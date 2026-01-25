"""
F30: HTML Export with Paragraph Context for pronunciations.

Generates an interactive HTML file with pronunciations and their full
paragraph context, enabling offline review and sharing.
"""

from datetime import datetime
from typing import Optional

from ..models import PronunciationEntry
from ..pipeline.pronunciation_guide.word_index import WordIndex


def generate_pronunciation_html(
    pronunciations: list[PronunciationEntry],
    word_index: Optional[WordIndex] = None,
    title: str = "Pronunciation Guide",
) -> str:
    """
    Generate interactive HTML export of pronunciations with paragraph context.

    Args:
        pronunciations: List of pronunciation entries
        word_index: Optional WordIndex for paragraph context extraction
        title: Title for the HTML document

    Returns:
        Complete HTML document as string
    """
    # Group pronunciations by type
    by_type: dict[str, list[PronunciationEntry]] = {}
    for pron in pronunciations:
        ptype = pron.flag_reason or "other"
        if ptype not in by_type:
            by_type[ptype] = []
        by_type[ptype].append(pron)

    # Build HTML
    html_parts = [_generate_header(title)]

    # Summary stats
    html_parts.append(
        f"""
    <div class="stats">
        <div class="stat-card">
            <div class="value">{len(pronunciations)}</div>
            <div class="label">Total Words</div>
        </div>
        <div class="stat-card">
            <div class="value">{len(by_type)}</div>
            <div class="label">Categories</div>
        </div>
    </div>
    """
    )

    # Pronunciation list with context
    html_parts.append('<div class="pronunciation-list">')

    for ptype, entries in sorted(by_type.items(), key=lambda x: -len(x[1])):
        html_parts.append(
            f"""
        <div class="category">
            <h2>{ptype.replace('_', ' ').title()} ({len(entries)})</h2>
            <div class="entries">
        """
        )

        for entry in sorted(entries, key=lambda e: e.word.lower()):
            # Extract paragraph context if word_index available
            context_html = ""
            if word_index and entry.mentions:
                first_mention = entry.mentions[0]
                para_ctx = word_index.extract_paragraph_context(
                    first_mention.position,
                    len(entry.word),
                )
                if para_ctx:
                    para_text, word_offset, word_len = para_ctx
                    # Highlight the word in context
                    if 0 <= word_offset < len(para_text):
                        highlighted = (
                            para_text[:word_offset]
                            + '<mark class="highlight">'
                            + para_text[word_offset : word_offset + word_len]
                            + "</mark>"
                            + para_text[word_offset + word_len :]
                        )
                        context_html = f'<div class="paragraph-context">{highlighted}</div>'

            ipa = entry.ipa or ""
            notes = entry.notes or ""

            html_parts.append(
                f"""
                <div class="entry">
                    <div class="word-header">
                        <span class="word">{entry.word}</span>
                        {f'<span class="ipa">{ipa}</span>' if ipa else ''}
                    </div>
                    {f'<div class="notes">{notes}</div>' if notes else ''}
                    {context_html}
                    <div class="meta">
                        Chapter {entry.mentions[0].chapter if entry.mentions else '?'} •
                        {len(entry.mentions)} occurrence{'s' if len(entry.mentions) != 1 else ''}
                    </div>
                </div>
            """
            )

        html_parts.append("</div></div>")

    html_parts.append("</div>")
    html_parts.append(_generate_footer())

    return "\n".join(html_parts)


def _generate_header(title: str) -> str:
    """Generate HTML header with styles."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --bg: #1a1a2e;
            --surface: #16213e;
            --surface-alt: #1f2937;
            --primary: #374151;
            --accent: #e94560;
            --text: #edf2f7;
            --muted: #a0aec0;
            --success: #10b981;
            --warning: #f59e0b;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 2rem;
            line-height: 1.6;
        }}

        h1 {{
            color: var(--accent);
            margin-bottom: 1rem;
        }}

        h2 {{
            color: var(--text);
            border-bottom: 2px solid var(--accent);
            padding-bottom: 0.5rem;
            margin-top: 2rem;
        }}

        .stats {{
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: var(--surface);
            padding: 1rem 2rem;
            border-radius: 8px;
            text-align: center;
        }}

        .stat-card .value {{
            font-size: 2rem;
            font-weight: bold;
            color: var(--accent);
        }}

        .stat-card .label {{
            color: var(--muted);
            font-size: 0.9rem;
        }}

        .pronunciation-list {{
            max-width: 900px;
        }}

        .category {{
            margin-bottom: 2rem;
        }}

        .entries {{
            display: grid;
            gap: 1rem;
        }}

        .entry {{
            background: var(--surface);
            padding: 1rem;
            border-radius: 8px;
            border-left: 3px solid var(--accent);
        }}

        .word-header {{
            display: flex;
            align-items: baseline;
            gap: 1rem;
            margin-bottom: 0.5rem;
        }}

        .word {{
            font-size: 1.2rem;
            font-weight: bold;
            color: var(--accent);
        }}

        .ipa {{
            font-family: 'Noto Sans', 'DejaVu Sans', sans-serif;
            color: var(--muted);
        }}

        .notes {{
            color: var(--text);
            margin-bottom: 0.75rem;
        }}

        .paragraph-context {{
            background: var(--surface-alt);
            padding: 1rem;
            border-radius: 4px;
            margin: 0.75rem 0;
            font-style: italic;
            color: var(--muted);
        }}

        .highlight {{
            background: var(--accent);
            color: var(--text);
            padding: 0.1rem 0.3rem;
            border-radius: 2px;
            font-style: normal;
            font-weight: bold;
        }}

        .meta {{
            font-size: 0.85rem;
            color: var(--muted);
        }}

        @media (prefers-color-scheme: light) {{
            :root {{
                --bg: #f5f5f5;
                --surface: #fff;
                --surface-alt: #f9f9f9;
                --primary: #e0e0e0;
                --text: #333;
                --muted: #666;
            }}
        }}

        @media print {{
            body {{
                background: white;
                color: black;
            }}
            .entry {{
                break-inside: avoid;
                border-color: #333;
            }}
            .highlight {{
                background: #ffeb3b;
                color: black;
            }}
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p style="color: var(--muted);">Generated {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
"""


def _generate_footer() -> str:
    """Generate HTML footer."""
    return """
    <script>
        // Filter functionality
        function filterPronunciations(query) {
            const searchTerm = query.toLowerCase().trim();
            document.querySelectorAll('.entry').forEach(entry => {
                const word = entry.querySelector('.word').textContent.toLowerCase();
                const notes = entry.querySelector('.notes')?.textContent.toLowerCase() || '';
                const matches = searchTerm === '' || word.includes(searchTerm) || notes.includes(searchTerm);
                entry.style.display = matches ? 'block' : 'none';
            });
        }
    </script>
</body>
</html>"""
