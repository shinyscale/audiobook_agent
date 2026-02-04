#!/usr/bin/env python3
"""
Synthetic PDF Generator for Testing

Generates PDFs with known content and specific issues to test the ingestion pipeline.
This allows us to create controlled, reproducible test cases where we know exactly
what the "correct" output should be.

Usage:
    python generate_test_pdfs.py [output_dir]

Categories of test PDFs:
1. Clean text - properly formatted, no issues
2. Missing spaces - words concatenated together
3. OCR-style errors - Roman numeral corruption, character substitutions
4. Line break issues - words split across lines with/without hyphens
5. Mixed issues - combination of problems
"""

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


@dataclass
class TestPDFSpec:
    """Specification for a test PDF."""

    name: str
    description: str
    content: str
    expected_clean: str  # What the text should look like after cleaning
    issues: list[str] = field(default_factory=list)  # List of issue types present


def create_pdf(spec: TestPDFSpec, output_dir: Path) -> Path:
    """Create a PDF from a specification."""
    output_path = output_dir / f"{spec.name}.pdf"

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )

    styles = getSampleStyleSheet()
    # Create a style that preserves whitespace better
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        spaceBefore=6,
        spaceAfter=6,
    )

    story = []

    # Split content into paragraphs and add them
    paragraphs = spec.content.split("\n\n")
    for para in paragraphs:
        if para.strip():
            # Replace newlines with <br/> for reportlab
            para_html = para.replace("\n", "<br/>")
            story.append(Paragraph(para_html, body_style))
            story.append(Spacer(1, 12))

    doc.build(story)

    # Also save the spec as JSON for test reference
    spec_path = output_dir / f"{spec.name}.json"
    spec_dict = {
        "name": spec.name,
        "description": spec.description,
        "expected_clean": spec.expected_clean,
        "issues": spec.issues,
    }
    spec_path.write_text(json.dumps(spec_dict, indent=2))

    return output_path


# =============================================================================
# Test PDF Specifications
# =============================================================================


def get_test_specs() -> list[TestPDFSpec]:
    """Return all test PDF specifications."""
    return [
        # 1. Clean text - no issues
        TestPDFSpec(
            name="clean_text",
            description="Properly formatted text with no issues",
            content="""CHAPTER I

The morning sun rose over the quiet village of Millbrook. Sarah walked
down the cobblestone street, her footsteps echoing in the early silence.

She had lived here all her life, yet today everything felt different.
The familiar shops and houses seemed to hold secrets she had never noticed
before. Perhaps it was the letter in her pocket that changed everything.

CHAPTER II

Three days had passed since the letter arrived. Sarah sat in the garden,
reading it for the hundredth time. The words still made no sense to her.""",
            expected_clean="""CHAPTER I

The morning sun rose over the quiet village of Millbrook. Sarah walked
down the cobblestone street, her footsteps echoing in the early silence.

She had lived here all her life, yet today everything felt different.
The familiar shops and houses seemed to hold secrets she had never noticed
before. Perhaps it was the letter in her pocket that changed everything.

CHAPTER II

Three days had passed since the letter arrived. Sarah sat in the garden,
reading it for the hundredth time. The words still made no sense to her.""",
            issues=[],
        ),
        # 2. Missing spaces - concatenated words
        TestPDFSpec(
            name="missing_spaces",
            description="Text with missing word spaces (common in old/scanned PDFs)",
            content="""CHAPTER I

The morningsun rose overthe quiet villageof Millbrook. Sarahwalked
downthe cobblestonestreet, herfootsteps echoingin theearly silence.

Shehad livedhere allher life, yettoday everythingfelt different.
Thefamiliar shopsand housesseemed tohold secretsshe hadnever noticed
before. Perhapsit wasthe letterin herpocket thatchanged everything.""",
            expected_clean="""CHAPTER I

The morning sun rose over the quiet village of Millbrook. Sarah walked
down the cobblestone street, her footsteps echoing in the early silence.

She had lived here all her life, yet today everything felt different.
The familiar shops and houses seemed to hold secrets she had never noticed
before. Perhaps it was the letter in her pocket that changed everything.""",
            issues=["missing_spaces"],
        ),
        # 3. OCR Roman numeral corruption
        TestPDFSpec(
            name="ocr_roman_numerals",
            description="Roman numerals corrupted by OCR (II->IT, III->ITI)",
            content="""CHAPTER IT

The story begins here with chapter two.

CHAPTER ITI

This is chapter three of the tale.

CHAPTER 1V

And here we have chapter four.

LETTER Vll

A letter from the seventh correspondence.""",
            expected_clean="""CHAPTER II

The story begins here with chapter two.

CHAPTER III

This is chapter three of the tale.

CHAPTER IV

And here we have chapter four.

LETTER VII

A letter from the seventh correspondence.""",
            issues=["ocr_roman_numerals"],
        ),
        # 4. OCR character substitutions
        TestPDFSpec(
            name="ocr_character_subs",
            description="Common OCR character substitution errors",
            content="""Tlie quick brown fox jumped over tlie lazy dog. Wlien tlie sun set,
tliey all went liome. Witli great care, tlie fatber carried liis cliild
tlirough tlie door.

Tliis was sometliing tliey liad never seen before. Notliing could
prepare tliem for wliat was about to liappen.""",
            expected_clean="""The quick brown fox jumped over the lazy dog. When the sun set,
they all went home. With great care, the father carried his child
through the door.

This was something they had never seen before. Nothing could
prepare them for what was about to happen.""",
            issues=["ocr_character_substitutions"],
        ),
        # 5. Hyphenated line breaks
        TestPDFSpec(
            name="hyphenated_breaks",
            description="Words split across lines with hyphens",
            content="""The extraor-
dinary circum-
stances of their meet-
ing would never be for-
gotten by anyone who wit-
nessed it.

She remem-
bered the conversa-
tion they had shared, the under-
standing that passed between them with-
out words.""",
            expected_clean="""The extraordinary circumstances of their meeting would never be forgotten by anyone who witnessed it.

She remembered the conversation they had shared, the understanding that passed between them without words.""",
            issues=["hyphenated_line_breaks"],
        ),
        # 6. Non-hyphenated line breaks (split words)
        TestPDFSpec(
            name="split_words",
            description="Words split at line breaks without hyphens (proper nouns)",
            content="""Henry Cler
val was the son of a merchant of Geneva. The young Franken
stein family had known them for years.

They traveled to Ingol
stadt together, where Cler
val would study languages while Victor pursued his scientific interests.""",
            expected_clean="""Henry Clerval was the son of a merchant of Geneva. The young Frankenstein family had known them for years.

They traveled to Ingolstadt together, where Clerval would study languages while Victor pursued his scientific interests.""",
            issues=["split_words_no_hyphen"],
        ),
        # 7. Punctuation spacing issues
        TestPDFSpec(
            name="punctuation_spacing",
            description="Missing spaces after punctuation",
            content="""The end came quickly.No one expected it.What happened next
surprised everyone.

"Hello,"said the man."How are you?"she replied.They talked
for hours;never once did they mention the past.""",
            expected_clean="""The end came quickly. No one expected it. What happened next
surprised everyone.

"Hello," said the man. "How are you?" she replied. They talked
for hours; never once did they mention the past.""",
            issues=["punctuation_spacing"],
        ),
        # 8. Mixed issues (realistic old PDF)
        TestPDFSpec(
            name="mixed_issues_realistic",
            description="Combination of issues like a realistic old scanned PDF",
            content="""CHAPTER IT

Tlie morningsun rose overthe quiet villageof Mill
brook. Sarahwalked downthe cobble
stone street,lier footsteps echoingin theearly silence.

CHAPTER ITI

Shehad livedliere allher life,yet today every
tliingfelt different.Tlie familiarshops andhouses
seemed toliold secretsshe liadnever noticed be
fore.Perliaps itwas theletter inlier pocket tliat
changed everytliing.""",
            expected_clean="""CHAPTER II

The morning sun rose over the quiet village of Millbrook. Sarah walked down the cobblestone street, her footsteps echoing in the early silence.

CHAPTER III

She had lived here all her life, yet today everything felt different. The familiar shops and houses seemed to hold secrets she had never noticed before. Perhaps it was the letter in her pocket that changed everything.""",
            issues=[
                "ocr_roman_numerals",
                "ocr_character_substitutions",
                "missing_spaces",
                "split_words_no_hyphen",
                "punctuation_spacing",
            ],
        ),
        # 9. Ligature issues
        TestPDFSpec(
            name="broken_ligatures",
            description="Broken ligatures (fi, fl, ff split with spaces)",
            content="""The of ficial document was dif ficult to read. It was full of suf fering
and af fliction, describing the dif ference between right and wrong.

The suf ficient evidence was finally found af ter many ef forts.""",
            expected_clean="""The official document was difficult to read. It was full of suffering
and affliction, describing the difference between right and wrong.

The sufficient evidence was finally found after many efforts.""",
            issues=["broken_ligatures"],
        ),
        # 10. I/1/l confusion
        TestPDFSpec(
            name="i_l_1_confusion",
            description="Confusion between I, l (lowercase L), and 1",
            content="""CHAPTER l

In the beginning, 1 was alone. The number 1 haunted me, as did
every instance where l appeared instead of I.

"What shall 1 do?" l asked myself. 1t seemed impossible.""",
            expected_clean="""CHAPTER I

In the beginning, I was alone. The number 1 haunted me, as did
every instance where I appeared instead of I.

"What shall I do?" I asked myself. It seemed impossible.""",
            issues=["i_l_1_confusion"],
        ),
    ]


def main():
    parser = argparse.ArgumentParser(description="Generate test PDFs for ingestion testing")
    parser.add_argument(
        "output_dir",
        nargs="?",
        default="tests/fixtures/pdfs",
        help="Output directory for generated PDFs",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available test specs without generating",
    )
    args = parser.parse_args()

    specs = get_test_specs()

    if args.list:
        print("Available test PDF specifications:")
        print("-" * 60)
        for spec in specs:
            issues_str = ", ".join(spec.issues) if spec.issues else "none"
            print(f"  {spec.name}")
            print(f"    Description: {spec.description}")
            print(f"    Issues: {issues_str}")
            print()
        return

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {len(specs)} test PDFs in {output_dir}/")
    print("-" * 60)

    for spec in specs:
        pdf_path = create_pdf(spec, output_dir)
        print(f"  Created: {pdf_path.name}")

    print("-" * 60)
    print(f"Generated {len(specs)} PDFs with corresponding .json spec files")
    print("Use the .json files to verify expected output in tests")


if __name__ == "__main__":
    main()
