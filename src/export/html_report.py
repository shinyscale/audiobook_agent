"""
Generate a formatted HTML report from analysis results.
Comprehensive narrator's guide with relationships, chapter details, and organized pronunciations.
"""

from pathlib import Path
from datetime import datetime
from collections import defaultdict
from jinja2 import Template

from ..models import AnalysisResult, StructureType, PronunciationFlag


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Audiobook Prep Report</title>
    <style>
        :root {
            --bg: #1a1a2e;
            --surface: #16213e;
            --surface-alt: #1f2b47;
            --primary: #0f3460;
            --accent: #e94560;
            --accent-soft: #c73e54;
            --text: #eee;
            --muted: #888;
            --success: #2d5a27;
            --warning: #5a5a27;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
        }

        .container { max-width: 1400px; margin: 0 auto; }

        /* Tab Navigation */
        nav {
            position: sticky;
            top: 0;
            background: var(--surface);
            padding: 0;
            border-radius: 8px;
            margin-bottom: 2rem;
            z-index: 100;
            display: flex;
            gap: 0;
            flex-wrap: wrap;
            justify-content: center;
            overflow: hidden;
        }
        nav a {
            color: var(--text);
            text-decoration: none;
            padding: 1rem 1.5rem;
            transition: all 0.2s;
            border-bottom: 3px solid transparent;
            cursor: pointer;
            position: relative;
        }
        nav a:hover {
            background: var(--primary);
        }
        nav a.active {
            background: var(--surface-alt);
            border-bottom-color: var(--accent);
            color: var(--accent);
            font-weight: 600;
        }

        /* Hide all tab content by default, show only active tab */
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }

        /* View toggle buttons */
        .view-toggle {
            padding: 0.5rem 1rem;
            border: 1px solid var(--primary);
            background: transparent;
            color: var(--text);
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .view-toggle:hover {
            background: var(--primary);
        }
        .view-toggle.active {
            background: var(--accent);
            border-color: var(--accent);
            font-weight: 600;
        }

        /* Pronunciation views */
        .pron-view {
            display: none;
        }
        .pron-view.active {
            display: block;
        }

        /* Print view: show all tabs and all pronunciation views */
        @media print {
            nav {
                display: none;
            }
            .tab-content {
                display: block !important;
                page-break-before: always;
            }
            .tab-content:first-of-type {
                page-break-before: auto;
            }
            .view-toggle {
                display: none !important;
            }
            .pron-view {
                display: block !important;
                page-break-before: always;
            }
        }

        /* Mobile responsive tabs */
        @media (max-width: 768px) {
            nav {
                flex-direction: column;
            }
            nav a {
                text-align: center;
            }
        }

        header {
            text-align: center;
            padding: 2rem;
            background: var(--surface);
            border-radius: 8px;
            margin-bottom: 2rem;
        }

        header h1 { color: var(--accent); margin-bottom: 0.5rem; font-size: 2.5rem; }
        header .meta { color: var(--muted); }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: var(--surface);
            padding: 1.5rem;
            border-radius: 8px;
            text-align: center;
        }

        .stat-card .value {
            font-size: 2rem;
            font-weight: bold;
            color: var(--accent);
        }

        .stat-card .label { color: var(--muted); }

        section {
            background: var(--surface);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }

        section h2 {
            color: var(--accent);
            border-bottom: 2px solid var(--primary);
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
            font-size: 1.5rem;
        }

        section h3 {
            color: var(--accent-soft);
            margin: 1.5rem 0 1rem 0;
            font-size: 1.2rem;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th, td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--primary);
        }

        th { color: var(--accent); font-weight: 600; }

        tr:hover { background: var(--primary); }

        .tag {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.85rem;
            background: var(--primary);
            margin: 0.1rem;
        }

        .tag.homograph { background: #5a3d7a; }
        .tag.proper_noun { background: #3d5a7a; }
        .tag.foreign { background: #7a5a3d; }
        .tag.unknown { background: #5a5a5a; }
        .tag.llm_refined { background: var(--success); }
        .tag.high { background: var(--success); }
        .tag.medium { background: var(--warning); }
        .tag.low { background: #5a2727; }

        /* Confidence badges */
        .confidence-badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 50%;
            font-size: 0.9rem;
            font-weight: bold;
            cursor: help;
            margin-left: 0.5rem;
        }
        .confidence-badge.high {
            background: var(--success);
            color: #fff;
        }
        .confidence-badge.medium {
            background: var(--warning);
            color: #333;
        }
        .confidence-badge.low {
            background: #5a2727;
            color: #fff;
        }

        .context {
            font-style: italic;
            color: var(--muted);
            font-size: 0.9rem;
        }

        .aliases { color: var(--muted); font-size: 0.9rem; }

        .description {
            font-style: italic;
            color: var(--muted);
            font-size: 0.9rem;
            margin-top: 0.25rem;
        }

        .warning {
            background: #5a4a27;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            margin-bottom: 0.5rem;
        }

        /* Relationship cards */
        .relationship-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1rem;
        }

        .relationship-card {
            background: var(--surface-alt);
            border-radius: 8px;
            padding: 1rem;
            border-left: 4px solid var(--accent);
        }

        .relationship-card h4 {
            color: var(--accent);
            margin-bottom: 0.5rem;
        }

        .relationship-card ul {
            list-style: none;
            padding: 0;
        }

        .relationship-card li {
            padding: 0.25rem 0;
            color: var(--text);
        }

        .relationship-card .rel-type {
            color: var(--muted);
            font-size: 0.85rem;
        }

        /* Character groups */
        .character-group {
            margin-bottom: 2rem;
        }

        .character-group h3 {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .character-group h3 .count {
            background: var(--primary);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.85rem;
        }

        /* Pronunciation groups */
        .pron-group {
            margin-bottom: 2rem;
        }

        .pron-group h3 {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .pron-note {
            font-size: 0.85rem;
            color: var(--muted);
            font-style: italic;
        }

        /* Chapter details */
        .chapter-details {
            margin-top: 0.5rem;
            padding: 0.5rem;
            background: var(--surface-alt);
            border-radius: 4px;
            font-size: 0.9rem;
        }

        .chapter-characters {
            display: flex;
            flex-wrap: wrap;
            gap: 0.25rem;
        }

        /* Chapter summaries */
        .chapter-summary {
            background: var(--surface-alt);
            padding: 1rem;
            border-radius: 4px;
            margin-top: 0.5rem;
            line-height: 1.7;
            font-size: 0.95rem;
        }

        .chapter-card {
            background: var(--surface-alt);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            border-left: 4px solid var(--accent);
        }

        .chapter-card h4 {
            color: var(--accent);
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .chapter-card .meta {
            color: var(--muted);
            font-size: 0.85rem;
        }

        /* Character profiles */
        .character-profile {
            background: var(--surface-alt);
            border-radius: 8px;
            padding: 1.25rem;
            margin-bottom: 1.5rem;
            border-left: 4px solid var(--accent);
        }

        .character-profile h4 {
            color: var(--accent);
            margin-bottom: 0.75rem;
            font-size: 1.2rem;
        }

        .character-profile .profile-meta {
            display: flex;
            gap: 1.5rem;
            flex-wrap: wrap;
            margin-bottom: 1rem;
            font-size: 0.9rem;
            color: var(--muted);
        }

        .character-profile .profile-body {
            line-height: 1.8;
            white-space: pre-wrap;
        }

        .character-profile .aliases-list {
            margin-top: 0.75rem;
            font-size: 0.9rem;
            color: var(--muted);
        }

        /* Print styles */
        @media print {
            body {
                background: white;
                color: black;
                padding: 0.5rem;
            }
            nav { display: none; }
            .stat-card, section {
                border: 1px solid #ddd;
                break-inside: avoid;
            }
            section { page-break-inside: avoid; }
            .tag { border: 1px solid #999; background: #eee !important; color: black; }
            header { page-break-after: avoid; }
            h2 { page-break-after: avoid; }
            tr { page-break-inside: avoid; }
        }

        @media (prefers-color-scheme: light) {
            :root {
                --bg: #f5f5f5;
                --surface: #fff;
                --surface-alt: #f9f9f9;
                --primary: #e0e0e0;
                --accent: #d32f2f;
                --accent-soft: #e57373;
                --text: #333;
                --muted: #666;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <nav>
            <a href="#overview" class="tab-link" data-tab="overview">Overview</a>
            <a href="#chapters" class="tab-link" data-tab="chapters">Chapters</a>
            <a href="#characters" class="tab-link" data-tab="characters">Characters</a>
            <a href="#pronunciations" class="tab-link" data-tab="pronunciations">Pronunciations</a>
        </nav>

        <div id="overview" class="tab-content active">
            <header>
                <h1>{{ title }}</h1>
                <p class="meta">
                    {% if author %}by {{ author }} &middot; {% endif %}
                    Narrator's Guide &middot; Generated {{ analyzed_at }}
                </p>
                {% if llm_model or analysis_duration %}
                <p class="meta" style="margin-top: 0.5rem; font-size: 0.9rem;">
                    {% if llm_model and llm_model != 'none' %}Analyzed with {{ llm_model }}{% endif %}
                    {% if llm_model and llm_model != 'none' and analysis_duration %} in {% elif analysis_duration %}Analyzed in {% endif %}
                    {% if analysis_duration %}{{ analysis_duration }}{% endif %}
                </p>
                {% endif %}
            </header>

            <div class="stats">
                <div class="stat-card">
                    <div class="value">{{ word_count }}</div>
                    <div class="label">Words</div>
                </div>
                <div class="stat-card">
                    <div class="value">{{ duration }}</div>
                    <div class="label">Est. Duration</div>
                </div>
                <div class="stat-card">
                    <div class="value">{{ chapter_count }}</div>
                    <div class="label">Chapters</div>
                </div>
                {% if prologue_count > 0 %}
                <div class="stat-card">
                    <div class="value">{{ prologue_count }}</div>
                    <div class="label">Prologue Materials</div>
                </div>
                {% endif %}
                <div class="stat-card">
                    <div class="value">{{ main_character_count }}</div>
                    <div class="label">Main Characters</div>
                </div>
                <div class="stat-card">
                    <div class="value">{{ pronunciation_count }}</div>
                    <div class="label">Pronunciation Notes</div>
                </div>
            </div>

            {% if overview %}
            <section>
                <h2>📚 Book Structure</h2>
                {% if overview.structure and overview.structure.description %}
                <p style="margin-top: 1rem; line-height: 1.8;">{{ overview.structure.description }}</p>
                {% if overview.structure.narrative_style and overview.structure.narrative_style != 'unknown' %}
                <p style="margin-top: 0.5rem; color: var(--muted); font-style: italic;">
                    Narrative style: {{ overview.structure.narrative_style }}
                </p>
                {% endif %}
                {% else %}
                <p style="color: var(--muted);">No structure information available.</p>
                {% endif %}
            </section>

            {% if overview.plot_summary and overview.plot_summary.plot_summary %}
            <section>
                <h2>📖 Plot Summary</h2>
                <div style="margin-top: 1rem; line-height: 1.8; white-space: pre-wrap;">{{ overview.plot_summary.plot_summary }}</div>
                {% if overview.plot_summary.themes %}
                <p style="margin-top: 1rem; color: var(--muted);">
                    <strong>Themes:</strong> {{ overview.plot_summary.themes | join(', ') }}
                </p>
                {% endif %}
            </section>
            {% endif %}

            {% if overview.model_usage %}
            <section>
                <h2>🤖 Analysis Models</h2>
                <table style="width: 100%; margin-top: 1rem; border-collapse: collapse;">
                    <thead>
                        <tr style="border-bottom: 2px solid var(--primary);">
                            <th style="text-align: left; padding: 0.75rem; color: var(--muted);">Phase</th>
                            <th style="text-align: left; padding: 0.75rem; color: var(--muted);">Model</th>
                            <th style="text-align: left; padding: 0.75rem; color: var(--muted);">Provider</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for phase, info in overview.model_usage.items() %}
                        <tr style="border-bottom: 1px solid var(--primary);">
                            <td style="padding: 0.75rem;">{{ phase }}</td>
                            <td style="padding: 0.75rem; font-family: monospace;">{{ info.model }}</td>
                            <td style="padding: 0.75rem;">{{ info.provider }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </section>
            {% endif %}

            {% if overview.timing %}
            <section>
                <h2>⏱️ Performance Timing</h2>
                <table style="width: 100%; margin-top: 1rem; border-collapse: collapse;">
                    <thead>
                        <tr style="border-bottom: 2px solid var(--primary);">
                            <th style="text-align: left; padding: 0.75rem; color: var(--muted);">Phase</th>
                            <th style="text-align: right; padding: 0.75rem; color: var(--muted);">Duration</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for phase, info in overview.timing.items() %}
                        {% if phase != 'total' %}
                        <tr style="border-bottom: 1px solid var(--primary);">
                            <td style="padding: 0.75rem;">{{ phase }}</td>
                            <td style="padding: 0.75rem; text-align: right; font-family: monospace;">{{ info.duration_formatted }}</td>
                        </tr>
                        {% endif %}
                        {% endfor %}
                        {% if overview.timing.total %}
                        <tr style="border-top: 2px solid var(--primary); font-weight: bold;">
                            <td style="padding: 0.75rem;">Total</td>
                            <td style="padding: 0.75rem; text-align: right; font-family: monospace;">{{ overview.timing.total.duration_formatted }}</td>
                        </tr>
                        {% endif %}
                    </tbody>
                </table>
            </section>
            {% endif %}
            {% endif %}

            <section id="relationships">
                <h2>🔗 Key Relationships</h2>
                {% if relationships %}
                <div class="relationship-grid">
                    {% for char_name, rels in relationships.items() %}
                    <div class="relationship-card">
                        <h4>{{ char_name }}</h4>
                        <ul>
                            {% for rel_name, rel_type in rels.items() %}
                            <li>
                                <strong>{{ rel_name }}</strong>
                                <span class="rel-type">{{ rel_type }}</span>
                            </li>
                            {% endfor %}
                        </ul>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <p style="color: var(--muted);">No explicit relationships detected.</p>
                {% endif %}
            </section>

            {% if warnings %}
            <section>
                <h2>⚠️ Warnings</h2>
                {% for warning in warnings %}
                <div class="warning">{{ warning }}</div>
                {% endfor %}
            </section>
            {% endif %}
        </div>

        <div id="chapters" class="tab-content">
        <section>
            <h2>📑 Chapter Guide</h2>

            {% if prologue_chapters %}
            <h3 style="margin-top: 1rem; margin-bottom: 1rem; color: var(--accent-soft);">Prologue Materials</h3>
            {% for ch in prologue_chapters %}
            <div class="chapter-card">
                <h4>
                    <span>{{ ch.label }}{% if ch.title %}: {{ ch.title }}{% endif %}</span>
                    <span class="meta">{{ ch.word_count }} words &middot; {{ ch.duration }}</span>
                </h4>
                {% if ch.summary %}
                <div class="chapter-summary">{{ ch.summary }}</div>
                {% endif %}
                {% if ch.characters %}
                <div class="chapter-characters" style="margin-top: 0.75rem;">
                    <strong style="margin-right: 0.5rem; color: var(--muted);">Characters:</strong>
                    {% for char_name in ch.characters[:8] %}
                    <span class="tag">{{ char_name }}</span>
                    {% endfor %}
                    {% if ch.characters|length > 8 %}
                    <span class="tag">+{{ ch.characters|length - 8 }} more</span>
                    {% endif %}
                </div>
                {% endif %}
            </div>
            {% endfor %}
            {% endif %}

            <h3 style="margin-top: 1.5rem; margin-bottom: 1rem; color: var(--accent-soft);">Chapters</h3>
            {% for ch in main_chapters_list %}
            <div class="chapter-card">
                <h4>
                    <span>{{ ch.label }}{% if ch.title %}: {{ ch.title }}{% endif %}</span>
                    <span class="meta">{{ ch.word_count }} words &middot; {{ ch.duration }}</span>
                </h4>
                {% if ch.summary %}
                <div class="chapter-summary">{{ ch.summary }}</div>
                {% endif %}
                {% if ch.characters %}
                <div class="chapter-characters" style="margin-top: 0.75rem;">
                    <strong style="margin-right: 0.5rem; color: var(--muted);">Characters:</strong>
                    {% for char_name in ch.characters[:8] %}
                    <span class="tag">{{ char_name }}</span>
                    {% endfor %}
                    {% if ch.characters|length > 8 %}
                    <span class="tag">+{{ ch.characters|length - 8 }} more</span>
                    {% endif %}
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </section>
        </div>

        <div id="characters" class="tab-content">
        <section>
            <h2>👥 Character Guide</h2>

            <!-- Confidence Filter -->
            <div style="margin-bottom: 1.5rem;">
                <label style="color: var(--muted); margin-right: 0.5rem;">
                    <input type="checkbox" id="show-low-confidence-only" onchange="filterByConfidence(this.checked)">
                    Show only low-confidence items
                </label>
            </div>

            {% if main_characters %}
            <div class="character-group">
                <h3>Main Characters <span class="count">{{ main_characters|length }}</span></h3>

                {% for char in main_characters %}
                <div class="character-profile character-item" data-confidence="{{ char.confidence.value }}">
                    <h4>
                        {{ char.canonical_name }}
                        {% if char.is_narrator %}
                        <span class="tag" style="background: var(--accent); color: var(--text); font-size: 0.75rem; margin-left: 0.5rem;" title="Narrator">📖 {{ char.narrative_role or "Narrator" }}</span>
                        {% endif %}
                        <span class="confidence-badge {{ char.confidence.value }}" title="Confidence: {{ char.confidence.value }}">
                            {% if char.confidence.value == 'high' %}✓
                            {% elif char.confidence.value == 'medium' %}!
                            {% else %}⚠
                            {% endif %}
                        </span>
                    </h4>
                    <div class="profile-meta">
                        <span>{{ char.mention_count }} mentions</span>
                        <span>First appears: Ch. {{ char.first_appearance_chapter or "?" }}</span>
                        <span class="tag {{ char.confidence.value }}">{{ char.confidence.value }} confidence</span>
                        {% if char.relationships %}
                        <span>Relationships:
                            {% for other, rel in char.relationships.items() %}
                            {{ other }} ({{ rel }}){% if not loop.last %}, {% endif %}
                            {% endfor %}
                        </span>
                        {% endif %}
                    </div>
                    {% if char.descriptions %}
                    <div class="profile-body">{{ char.descriptions[0].text }}</div>
                    {% if char.evidence %}
                    <details style="margin-top: 0.75rem;">
                        <summary style="cursor: pointer; color: var(--muted);">Evidence ({{ char.evidence|length }})</summary>
                        <div class="chapter-details" style="margin-top: 0.5rem;">
                            <ul style="list-style: none; padding-left: 0;">
                                {% for ev in char.evidence[:15] %}
                                <li style="margin-bottom: 0.75rem;">
                                    <div>
                                        <span class="tag">{{ ev.get("type","fact") }}</span>
                                        {% if ev.get("chunk") %}<span class="tag">{{ ev.get("chunk") }}</span>{% endif %}
                                    </div>
                                    {% if ev.get("statement") %}
                                    <div style="margin-top: 0.25rem;"><strong>{{ ev.get("statement") }}</strong></div>
                                    {% endif %}
                                    {% if ev.get("other") and ev.get("relation") %}
                                    <div style="margin-top: 0.25rem;"><strong>{{ ev.get("other") }}</strong> <span class="rel-type">({{ ev.get("relation") }})</span></div>
                                    {% endif %}
                                    {% if ev.get("quotes") %}
                                    <div class="context" style="margin-top: 0.25rem;">
                                        {% for q in ev.get("quotes")[:2] %}
                                        <div>“{{ q.get("quote","")[:200] }}{% if q.get("quote","")|length > 200 %}...{% endif %}”</div>
                                        {% endfor %}
                                    </div>
                                    {% endif %}
                                </li>
                                {% endfor %}
                                {% if char.evidence|length > 15 %}
                                <li class="pron-note">... and {{ char.evidence|length - 15 }} more evidence items</li>
                                {% endif %}
                            </ul>
                        </div>
                    </details>
                    {% endif %}
                    {% else %}
                    <div class="profile-body" style="color: var(--muted); font-style: italic;">No detailed profile available.</div>
                    {% endif %}
                    {% if char.aliases %}
                    <div class="aliases-list">Also known as: {{ char.aliases|join(", ") }}</div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
            {% endif %}

            {% if minor_characters %}
            <div class="character-group">
                <h3>Supporting Characters <span class="count">{{ minor_characters|length }}</span></h3>
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Mentions</th>
                            <th>First Appears</th>
                            <th>Aliases</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for char in minor_characters %}
                        <tr>
                            <td>
                                <strong>{{ char.canonical_name }}</strong>
                                {% if char.is_narrator %}
                                <span class="tag" style="background: var(--accent); color: var(--text); font-size: 0.7rem; margin-left: 0.25rem;">📖 {{ char.narrative_role or "Narrator" }}</span>
                                {% endif %}
                                {% if char.descriptions and char.descriptions[0].text|length > 0 %}
                                <div class="description">{{ char.descriptions[0].text[:200] }}{% if char.descriptions[0].text|length > 200 %}...{% endif %}</div>
                                {% endif %}
                            </td>
                            <td>{{ char.mention_count }}</td>
                            <td>Ch. {{ char.first_appearance_chapter or "?" }}</td>
                            <td class="aliases">{{ char.aliases|join(", ") or "—" }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}
        </section>
        </div>

        <div id="pronunciations" class="tab-content">
        <section>
            <h2>🗣️ Pronunciation Guide</h2>

            <!-- View Toggle and Search -->
            <div style="margin-bottom: 1.5rem; display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;">
                <div style="display: flex; gap: 0.5rem; align-items: center;">
                    <span style="color: var(--muted); margin-right: 0.5rem;">View:</span>
                    <button id="view-by-type" class="view-toggle active" onclick="switchPronView('by-type')">By Type</button>
                    <button id="view-by-chapter" class="view-toggle" onclick="switchPronView('by-chapter')">By Chapter</button>
                </div>
                <div style="display: flex; gap: 0.5rem; align-items: center; flex: 1; min-width: 250px;">
                    <span style="color: var(--muted);">Search:</span>
                    <input type="text" id="pron-search" placeholder="Filter pronunciations..."
                           style="flex: 1; padding: 0.5rem; border: 1px solid var(--primary); background: var(--surface-alt); color: var(--text); border-radius: 4px;"
                           oninput="searchPronunciations(this.value)">
                    <button onclick="clearPronSearch()"
                            style="padding: 0.5rem 1rem; border: 1px solid var(--primary); background: var(--surface-alt); color: var(--text); border-radius: 4px; cursor: pointer;">
                        Clear
                    </button>
                </div>
                <div id="pron-count" style="color: var(--muted); font-size: 0.9rem;"></div>
            </div>

            <!-- By Type View (default) -->
            <div id="pron-by-type" class="pron-view active">
            {% if homographs %}
            <div class="pron-group">
                <h3>Homographs <span class="tag homograph">{{ homographs|length }}</span></h3>
                <p class="pron-note">Words with multiple pronunciations depending on context</p>
                <table>
                    <thead>
                        <tr>
                            <th>Word</th>
                            <th>Confidence</th>
                            <th>Occurrences</th>
                            <th>Options/Notes</th>
                            <th>Example Context</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for pron in homographs %}
                        <tr class="pron-item" data-confidence="{{ pron.confidence.value }}">
                            <td><strong>{{ pron.word }}</strong></td>
                            <td>
                                <span class="confidence-badge {{ pron.confidence.value }}" title="Confidence: {{ pron.confidence.value }}">
                                    {% if pron.confidence.value == 'high' %}✓
                                    {% elif pron.confidence.value == 'medium' %}!
                                    {% else %}⚠
                                    {% endif %}
                                </span>
                            </td>
                            <td>{{ pron.occurrences }}</td>
                            <td>{{ pron.notes or "—" }}</td>
                            <td class="context">
                                {% if pron.context_examples %}
                                "...{{ pron.context_examples[0][:80] }}..."
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}

            {% if proper_nouns %}
            <div class="pron-group">
                <h3>Proper Nouns <span class="tag proper_noun">{{ proper_nouns|length }}</span></h3>
                <p class="pron-note">Character names, places, and other proper nouns</p>
                <table>
                    <thead>
                        <tr>
                            <th>Word</th>
                            <th>Occurrences</th>
                            <th>Context</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for pron in proper_nouns[:50] %}
                        <tr>
                            <td><strong>{{ pron.word }}</strong></td>
                            <td>{{ pron.occurrences }}</td>
                            <td class="context">
                                {% if pron.context_examples %}
                                "...{{ pron.context_examples[0][:60] }}..."
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% if proper_nouns|length > 50 %}
                <p class="pron-note">... and {{ proper_nouns|length - 50 }} more</p>
                {% endif %}
            </div>
            {% endif %}

            {% if foreign_words %}
            <div class="pron-group">
                <h3>Foreign Words <span class="tag foreign">{{ foreign_words|length }}</span></h3>
                <p class="pron-note">Words from other languages that may need special pronunciation</p>
                <table>
                    <thead>
                        <tr>
                            <th>Word</th>
                            <th>Language</th>
                            <th>Occurrences</th>
                            <th>Context</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for pron in foreign_words %}
                        <tr>
                            <td><strong>{{ pron.word }}</strong></td>
                            <td>{{ pron.notes or "—" }}</td>
                            <td>{{ pron.occurrences }}</td>
                            <td class="context">
                                {% if pron.context_examples %}
                                "...{{ pron.context_examples[0][:60] }}..."
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}

            {% if other_pronunciations %}
            <div class="pron-group">
                <h3>Other <span class="tag unknown">{{ other_pronunciations|length }}</span></h3>
                <p class="pron-note">Technical, archaic, or unusual words</p>
                <table>
                    <thead>
                        <tr>
                            <th>Word</th>
                            <th>Type</th>
                            <th>Occurrences</th>
                            <th>Context</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for pron in other_pronunciations %}
                        <tr>
                            <td><strong>{{ pron.word }}</strong></td>
                            <td><span class="tag">{{ pron.flag_reason.value }}</span></td>
                            <td>{{ pron.occurrences }}</td>
                            <td class="context">
                                {% if pron.context_examples %}
                                "...{{ pron.context_examples[0][:60] }}..."
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}
            </div>
            <!-- End By Type View -->

            <!-- By Chapter View -->
            <div id="pron-by-chapter" class="pron-view">
            {% if chapter_pronunciation_list %}
            {% for chapter in chapter_pronunciation_list %}
            <div class="pron-group">
                <h3>{{ chapter.title }} <span class="tag">{{ chapter.word_count }} words</span></h3>
                <table>
                    <thead>
                        <tr>
                            <th>Word</th>
                            <th>Type</th>
                            <th>Occurrences</th>
                            <th>Context</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for pron in chapter.pronunciations %}
                        <tr>
                            <td><strong>{{ pron.word }}</strong></td>
                            <td><span class="tag {{ pron.flag_reason.value }}">{{ pron.flag_reason.value }}</span></td>
                            <td>{{ pron.occurrences }}</td>
                            <td class="context">
                                {% if pron.context_examples %}
                                "...{{ pron.context_examples[0][:60] }}..."
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endfor %}
            {% else %}
            <p style="color: var(--muted);">No pronunciations found by chapter.</p>
            {% endif %}
            </div>
            <!-- End By Chapter View -->

        </section>
        </div>

        <footer style="text-align: center; color: var(--muted); padding: 2rem;">
            Generated by Audiobook Prep
        </footer>
    </div>

    <script>
        // Pronunciation search
        function searchPronunciations(query) {
            const searchTerm = query.toLowerCase().trim();
            const pronItems = document.querySelectorAll('.pron-item');
            let visibleCount = 0;
            let totalCount = pronItems.length;

            pronItems.forEach(item => {
                const row = item;
                const cells = row.querySelectorAll('td');
                let textContent = '';

                // Get text from all cells
                cells.forEach(cell => {
                    textContent += cell.textContent.toLowerCase() + ' ';
                });

                // Show/hide based on search match
                if (searchTerm === '' || textContent.includes(searchTerm)) {
                    row.style.display = '';
                    visibleCount++;
                } else {
                    row.style.display = 'none';
                }
            });

            // Update count display
            const countDiv = document.getElementById('pron-count');
            if (searchTerm) {
                countDiv.textContent = `Showing ${visibleCount} of ${totalCount} items`;
            } else {
                countDiv.textContent = '';
            }
        }

        function clearPronSearch() {
            document.getElementById('pron-search').value = '';
            searchPronunciations('');
        }

        // Confidence filtering
        function filterByConfidence(showLowOnly) {
            const items = document.querySelectorAll('.character-item, .pron-item');
            items.forEach(item => {
                const confidence = item.getAttribute('data-confidence');
                if (showLowOnly) {
                    // Show only low confidence items
                    if (confidence === 'low') {
                        item.style.display = '';
                    } else {
                        item.style.display = 'none';
                    }
                } else {
                    // Show all items
                    item.style.display = '';
                }
            });
        }

        // Pronunciation view switching
        function switchPronView(view) {
            // Remove active class from all view toggles and views
            document.querySelectorAll('.view-toggle').forEach(btn => {
                btn.classList.remove('active');
            });
            document.querySelectorAll('.pron-view').forEach(div => {
                div.classList.remove('active');
            });

            // Add active class to selected view
            if (view === 'by-type') {
                document.getElementById('view-by-type').classList.add('active');
                document.getElementById('pron-by-type').classList.add('active');
            } else if (view === 'by-chapter') {
                document.getElementById('view-by-chapter').classList.add('active');
                document.getElementById('pron-by-chapter').classList.add('active');
            }
        }

        // Tab switching functionality
        function switchTab(tabId) {
            // Remove active class from all tabs and content
            document.querySelectorAll('.tab-link').forEach(link => {
                link.classList.remove('active');
            });
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });

            // Add active class to selected tab and content
            const selectedLink = document.querySelector(`.tab-link[data-tab="${tabId}"]`);
            const selectedContent = document.getElementById(tabId);

            if (selectedLink) selectedLink.classList.add('active');
            if (selectedContent) selectedContent.classList.add('active');

            // Update URL hash without scrolling
            if (history.pushState) {
                history.pushState(null, null, `#${tabId}`);
            } else {
                window.location.hash = tabId;
            }
        }

        // Handle tab clicks
        document.querySelectorAll('.tab-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const tabId = link.getAttribute('data-tab');
                switchTab(tabId);
            });
        });

        // Handle deep linking (URL hash on page load)
        window.addEventListener('DOMContentLoaded', () => {
            const hash = window.location.hash.substring(1); // Remove the '#'
            if (hash && document.getElementById(hash)) {
                switchTab(hash);
            } else {
                // Default to overview tab
                switchTab('overview');
            }
        });

        // Handle browser back/forward buttons
        window.addEventListener('hashchange', () => {
            const hash = window.location.hash.substring(1);
            if (hash && document.getElementById(hash)) {
                switchTab(hash);
            }
        });
    </script>
</body>
</html>
'''


def format_number(value: int) -> str:
    """Format a number with thousands separators."""
    return f"{value:,}"


def _classify_chapter(title: str) -> str:
    """
    Classify a chapter as 'prologue', 'title_page', or 'main'.

    Args:
        title: The chapter title

    Returns:
        'prologue' - Letters, preface, introduction, etc.
        'title_page' - Title page entries (to be filtered)
        'main' - Regular story chapters
    """
    if not title:
        return 'main'

    title_upper = title.upper().strip()

    # Title page detection (filter out)
    # Matches patterns like "FRANKENSTEIN; OR," or standalone book titles
    if '; OR,' in title_upper or title_upper.endswith('; OR'):
        return 'title_page'

    # Prologue material detection
    prologue_patterns = [
        'LETTER',      # LETTER I, LETTER II, etc.
        'PREFACE',
        'INTRODUCTION',
        'FOREWORD',
        'DEDICATION',
        'EDITOR',
        'PROLOGUE',
        "AUTHOR'S NOTE",
    ]

    for pattern in prologue_patterns:
        if title_upper.startswith(pattern) or pattern in title_upper:
            return 'prologue'

    return 'main'


def _format_duration(seconds: float) -> str:
    """Format duration in human-readable form (e.g., '2m 34s')."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    if mins > 0:
        return f"{mins}m {secs}s"
    return f"{secs}s"


def export_html_report(
    result: AnalysisResult,
    output_path: str | Path,
    llm_model: str | None = None,
    analysis_duration_seconds: float | None = None,
) -> None:
    """
    Export analysis results as an HTML report.

    Args:
        result: AnalysisResult to export
        output_path: Path to write HTML file
        llm_model: Name of the LLM model used (optional)
        analysis_duration_seconds: Total analysis time in seconds (optional)
    """
    # Calculate duration string
    total_mins = result.metadata.estimated_total_duration_minutes
    hours = int(total_mins // 60)
    mins = int(total_mins % 60)
    duration = f"{hours}h {mins}m"

    # Get chapters and split into prologue vs main chapters
    chapter_elements = [e for e in result.structure if e.type == StructureType.CHAPTER]

    prologue_chapters = []
    main_chapters = []
    prologue_idx = 1
    main_idx = 1

    for elem in chapter_elements:
        classification = _classify_chapter(elem.title)

        # Skip title pages entirely
        if classification == 'title_page':
            continue

        ch_mins = elem.estimated_duration_minutes
        ch_hours = int(ch_mins // 60)
        ch_mins_remainder = int(ch_mins % 60)

        # Get characters that appear in this chapter
        chapter_chars = elem.characters_present if elem.characters_present else []

        chapter_data = {
            'title': elem.title,
            'word_count': format_number(elem.word_count),
            'duration': f"{ch_hours}h {ch_mins_remainder}m" if ch_hours else f"{ch_mins_remainder}m",
            'confidence': elem.confidence.value,
            'characters': chapter_chars,
            'summary': elem.summary,  # LLM-generated chapter summary
        }

        if classification == 'prologue':
            chapter_data['index'] = prologue_idx
            chapter_data['label'] = f"Prologue {prologue_idx}"
            prologue_chapters.append(chapter_data)
            prologue_idx += 1
        else:
            chapter_data['index'] = main_idx
            chapter_data['label'] = f"Chapter {main_idx}"
            main_chapters.append(chapter_data)
            main_idx += 1

    # Separate main vs minor characters (threshold: 10+ mentions = main)
    main_characters = [c for c in result.characters if c.mention_count >= 10]
    minor_characters = [c for c in result.characters if c.mention_count < 10][:30]

    # Extract relationships into a dict for display
    relationships = {}
    for char in result.characters:
        if char.relationships:
            relationships[char.canonical_name] = char.relationships

    # Group pronunciations by type
    homographs = [p for p in result.pronunciations if p.flag_reason == PronunciationFlag.HOMOGRAPH]
    proper_nouns = [p for p in result.pronunciations if p.flag_reason == PronunciationFlag.PROPER_NOUN]
    foreign_words = [p for p in result.pronunciations if p.flag_reason == PronunciationFlag.FOREIGN]
    other_pronunciations = [
        p for p in result.pronunciations
        if p.flag_reason not in (PronunciationFlag.HOMOGRAPH, PronunciationFlag.PROPER_NOUN, PronunciationFlag.FOREIGN)
    ]

    # Group pronunciations by chapter for the "By Chapter" view
    pronunciations_by_chapter = defaultdict(list)
    for pron in result.pronunciations:
        for chapter_idx in pron.chapter_indices:
            pronunciations_by_chapter[chapter_idx].append(pron)

    # Build chapter pronunciation list with counts
    chapter_pronunciation_list = []
    for chapter in result.structure:
        if chapter.type == StructureType.CHAPTER:
            chapter_prons = pronunciations_by_chapter.get(chapter.index, [])
            if chapter_prons:
                chapter_pronunciation_list.append({
                    'index': chapter.index,
                    'title': chapter.title or f"Chapter {chapter.index}",
                    'word_count': len(chapter_prons),
                    'pronunciations': sorted(chapter_prons, key=lambda p: p.word.lower())
                })

    # Prepare template
    template = Template(HTML_TEMPLATE)

    # Format analysis duration if provided
    analysis_duration_str = None
    if analysis_duration_seconds is not None:
        analysis_duration_str = _format_duration(analysis_duration_seconds)

    html = template.render(
        title=result.metadata.title or "Untitled",
        author=result.metadata.author,
        analyzed_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        word_count=format_number(result.metadata.total_word_count),
        duration=duration,
        chapter_count=len(main_chapters),
        prologue_count=len(prologue_chapters),
        main_character_count=len(main_characters),
        pronunciation_count=len(result.pronunciations),
        prologue_chapters=prologue_chapters,
        main_chapters_list=main_chapters,
        relationships=relationships,
        main_characters=main_characters,
        minor_characters=minor_characters,
        homographs=homographs,
        proper_nouns=proper_nouns,
        foreign_words=foreign_words,
        other_pronunciations=other_pronunciations,
        chapter_pronunciation_list=chapter_pronunciation_list,
        warnings=result.warnings,
        llm_model=llm_model,
        analysis_duration=analysis_duration_str,
        overview=result.overview,
    )

    output_path = Path(output_path)
    output_path.write_text(html, encoding='utf-8')
    print(f"HTML report saved to: {output_path}")
