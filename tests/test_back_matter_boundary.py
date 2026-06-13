"""Tests for chapter-independent back-matter boundary detection and clipping.

Guards against the regression where the last chapter ran to EOF, so back-matter
detection was skipped and acknowledgements/glossary names leaked into the cast.
"""

from src.analyzer import AudiobookAnalyzer
from src.ingestion.regions import RegionDetector, RegionType, detect_document_regions


def _body(text, chapters):
    regions = detect_document_regions(text, chapters)
    body = [r for r in regions if r.region_type == RegionType.BODY]
    return body[0] if body else None


class TestDetectBackMatterStart:
    def setup_method(self):
        self.det = RegionDetector()

    def test_finds_glossary_heading_in_latter_portion(self):
        story = "The patrol moved through the jungle. " * 2000
        text = story + "\n\nGlossary\nNVA: North Vietnamese Army.\n"
        pos = self.det.detect_back_matter_start(text)
        assert pos is not None and pos >= int(len(text) * 0.55)
        assert text[pos:].lstrip().lower().startswith("glossary")

    def test_returns_none_without_back_matter(self):
        text = "Mitchell walked the perimeter. " * 3000
        assert self.det.detect_back_matter_start(text) is None

    def test_ignores_early_heading(self):
        # A "Notes" heading in the first half must not be taken as back matter.
        text = "Notes\nsome early note.\n" + ("Story content here. " * 4000)
        assert self.det.detect_back_matter_start(text) is None

    def test_ignores_front_matter_toc_line(self):
        # TOC entry near the front; real content fills the rest, no back heading.
        text = "Acknowledgements .... 459\n" + ("Story content. " * 4000)
        assert self.det.detect_back_matter_start(text) is None

    def test_picks_earliest_of_multiple_headings(self):
        story = "Combat narrative. " * 3000
        text = story + "\n\nGlossary\nterms.\n" + ("x " * 200) + "\n\nAcknowledgements\nthanks.\n"
        pos = self.det.detect_back_matter_start(text)
        assert text[pos:].lstrip().lower().startswith("glossary")


class TestDetectRegionsUsesBoundary:
    def test_body_ends_at_back_matter_even_when_chapter_runs_to_eof(self):
        story = "The squad advanced. " * 3000
        text = story + "\n\nAcknowledgements\nThanks to Charlie Varon.\n"
        # A chapter that (wrongly) runs to EOF — the failure mode.
        chapters = [{"start_pos": 0, "end_pos": len(text), "title": "Last"}]
        body = _body(text, chapters)
        ack = text.find("Acknowledgements")
        assert body is not None and body.end_position <= ack
        assert text.find("Charlie Varon") >= body.end_position


class TestClipChaptersToBody:
    class _Ch:
        def __init__(self, i, sp, ep):
            self.index, self.start_position, self.end_position = i, sp, ep
            self.title = None

    class _CM:
        def __init__(self, chs):
            self.chapters = chs

    def test_clips_overextending_last_chapter(self):
        cm = self._CM([self._Ch(1, 0, 500), self._Ch(2, 500, 1000)])
        n = AudiobookAnalyzer._clip_chapters_to_body(cm, 800)
        assert n == 1
        assert cm.chapters[-1].end_position == 800
        assert len(cm.chapters) == 2

    def test_drops_pure_back_matter_chapter(self):
        cm = self._CM([self._Ch(1, 0, 900), self._Ch(2, 910, 1000)])
        n = AudiobookAnalyzer._clip_chapters_to_body(cm, 820)
        assert n == 2  # ch1 clipped to 820, ch2 (starts at 910) dropped
        assert len(cm.chapters) == 1
        assert cm.chapters[0].end_position == 820

    def test_no_change_when_within_body(self):
        cm = self._CM([self._Ch(1, 0, 500), self._Ch(2, 500, 900)])
        n = AudiobookAnalyzer._clip_chapters_to_body(cm, 1000)
        assert n == 0
        assert len(cm.chapters) == 2
