"""Tests for final-stage cast cleanup: dedup, regrounding, narrator sanity."""

from src.pipeline.cast_dedup import (
    merge_fragment_duplicates,
    reground_canonical_names,
    reject_implausible_narrator,
)

TEXT = (
    "Staff Sgt. Mike Mitchell led the patrol. Mitchell knew the area. "
    "Sergeant Huffman and Huffman's squad followed. " * 5
    + "Diana Ross and Mary Wilson of the Supremes played on the radio. "
    + "Wilson the sniper took aim. Wilson fired. " * 30
)


class _Ch:
    _n = 0

    def __init__(self, name, mc, aliases=None, role="supporting", **kw):
        type(self)._n += 1
        self.id = kw.get("id", f"c{type(self)._n}")
        self.canonical_name = name
        self.mention_count = mc
        self.aliases = list(aliases or [])
        self.role = role
        self.is_narrator = kw.get("is_narrator", False)
        self.evidence = kw.get("evidence", [])
        self.descriptions = kw.get("descriptions", [])


class TestMergeFragments:
    def test_identical_count_subset_merges(self):
        chars = [
            _Ch("Staff Sgt. Mike Mitchell", 1149, role="protagonist"),
            _Ch("Mitchell", 1149),
        ]
        out = merge_fragment_duplicates(chars, TEXT)
        assert len(out) == 1
        assert out[0].canonical_name == "Staff Sgt. Mike Mitchell"
        assert "Mitchell" in out[0].aliases

    def test_different_counts_do_not_merge(self):
        # Soldier "Murphy"(3) must NOT fold into name-drop "Audie Murphy"(36).
        chars = [_Ch("Audie Murphy", 36), _Ch("First Sergeant Murphy", 3)]
        out = merge_fragment_duplicates(chars, TEXT)
        assert len(out) == 2

    def test_given_name_conflict_blocks_merge(self):
        # Same count but conflicting given names = different people.
        chars = [_Ch("Mike Mitchell", 50), _Ch("David Mitchell", 50)]
        out = merge_fragment_duplicates(chars, TEXT)
        assert len(out) == 2

    def test_ambiguous_surname_left_alone(self):
        # "Wilson" contained by two different full names → ambiguous → no merge.
        chars = [
            _Ch("George Wilson", 40),
            _Ch("Myrtle Wilson", 40),
            _Ch("Wilson", 40),
        ]
        out = merge_fragment_duplicates(chars, TEXT)
        assert len(out) == 3

    def test_namesake_canonical_prefers_grounded_surname(self):
        # "Mary Wilson" bigram occurs once; "Wilson" surname dominates → the
        # merged entity should display as "Wilson", not the name-drop.
        chars = [_Ch("Mary Wilson", 90), _Ch("Wilson", 90)]
        out = merge_fragment_duplicates(chars, TEXT)
        assert len(out) == 1
        assert out[0].canonical_name == "Wilson"

    def test_empty_core_never_merges(self):
        # "Doc" is a bare title (empty core) — must not fold into any Doc X.
        chars = [_Ch("Doc Silkowski", 8), _Ch("Doc", 8)]
        out = merge_fragment_duplicates(chars, TEXT)
        assert len(out) == 2


class TestReground:
    def test_ungrounded_full_name_regrounds_to_surname(self):
        # A full name absent from the text regrounds to the grounded surname.
        c = _Ch("Zachariah Mitchell", 1149, aliases=["Mitchell"])
        reground_canonical_names([c], TEXT)
        assert c.canonical_name in ("Mitchell",)

    def test_grounded_full_name_kept(self):
        c = _Ch("Mike Mitchell", 1149)  # "mike mitchell" is in TEXT
        reground_canonical_names([c], TEXT)
        assert c.canonical_name == "Mike Mitchell"


class TestNarratorSanity:
    def test_minor_narrator_rejected(self):
        chars = [_Ch("Mitchell", 1149, role="protagonist"),
                 _Ch("Haynes", 20, role="protagonist", is_narrator=True, id="h")]
        nid = reject_implausible_narrator(chars, "h")
        assert nid is None
        assert chars[1].is_narrator is False

    def test_dominant_narrator_kept(self):
        chars = [_Ch("Nick", 110, is_narrator=True, id="n"),
                 _Ch("Gatsby", 200)]
        nid = reject_implausible_narrator(chars, "n")
        assert nid == "n"

    def test_undernamed_firstperson_narrator_kept(self):
        # Nick Carraway: ~14% of Gatsby's mentions but a real narrator (34 > floor).
        chars = [_Ch("Nick Carraway", 34, is_narrator=True, id="n"),
                 _Ch("Gatsby", 249)]
        nid = reject_implausible_narrator(chars, "n")
        assert nid == "n"
        assert chars[0].is_narrator is True
