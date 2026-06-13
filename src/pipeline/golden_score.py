"""
Golden-corpus scorer: deterministic F1 scoring of an AnalysisResult (or its
serialized JSON) against hand-verified ground truth.

No LLM calls — pure set comparisons — so a full corpus scores in seconds and
every code change gets a number. Used by tools/score_analysis.py and (later)
as the oracle loop's held-out evaluation.

Ground truth schema (validation/golden/<book>.json):
{
  "book": "The Great Gatsby",
  "source_file": "Test_Texts/gatsby.txt",          // optional
  "narrator": "Nick Carraway",                      // null for third-person
  "characters": [
    {"canonical_name": "Jay Gatsby",
     "aliases": ["Gatsby", "James Gatz"],           // acceptable aliases
     "role": "protagonist",                         // optional
     "required": true}                              // default true
  ],
  "forbidden": ["Mad'selle Salle"]                  // must NOT appear as characters
}
"""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_MAIN_TIER_ROLES = {"protagonist", "antagonist", "main", "narrator"}


def _title_stop_tokens():
    from .character_extraction_v2.main_cast import MainCastExtractor

    return MainCastExtractor._TITLE_TOKENS, MainCastExtractor._NAME_STOP_TOKENS


def normalize_name(name: str) -> str:
    """Lowercase, strip punctuation/titles/articles/possessives — matching only."""
    title_tokens, stop_tokens = _title_stop_tokens()
    words = []
    for raw in name.replace(".", " ").split():
        tok = raw.strip(",'\"()").lower()
        tok = re.sub(r"[’']s$", "", tok)  # possessives: "wilson's" → "wilson"
        if (
            tok
            and len(tok) > 1  # drop middle initials ("George B. Wilson")
            and tok not in title_tokens
            and tok not in stop_tokens
        ):
            words.append(tok)
    # Fall back to the raw lowered string when everything was a title/article
    # ("the narrator" → "narrator" handled above; "Mrs." alone → raw)
    return " ".join(words) if words else name.lower().strip()


def _name_set(canonical: str, aliases) -> set[str]:
    names = set()
    for raw in [canonical] + list(aliases or []):
        if not raw:
            continue
        # "PFC Billy Sherman (Tank)" carries two surface forms: the name and
        # the parenthetical nickname. Index both.
        paren = re.findall(r"\(([^)]+)\)", raw)
        base = re.sub(r"\s*\([^)]*\)", " ", raw).strip()
        for form in [base] + paren:
            n = normalize_name(form)
            if n:
                names.add(n)
    names.discard("")
    return names


def _match_keys(name_set: set[str]) -> set[str]:
    """Identity-matching keys for a character: the full normalized names PLUS
    the surname (last token) of any multi-word name. Fragment splits routinely
    leave surname-only mentions on a separate entity, so a full-name entity
    must still match a truth entry sharing the surname ("Spec-4 Timmy Ingram" ~
    "Ingram"). Used ONLY for character matching, never for alias precision
    (where a wrong given name like "Tabitha Voss" must stay a false positive)."""
    keys = set(name_set)
    for n in name_set:
        toks = n.split()
        if len(toks) >= 2 and len(toks[-1]) >= 3:
            keys.add(toks[-1])
    return keys


def score_against_truth(analysis: dict, truth: dict) -> dict:
    """
    Score a serialized AnalysisResult dict against a ground-truth dict.

    Returns a flat metrics dict (all rates in [0,1], None where undefined).
    """
    predicted = [
        {
            "canonical": c.get("canonical_name", ""),
            "names": _name_set(c.get("canonical_name", ""), c.get("aliases")),
            "match_keys": _match_keys(
                _name_set(c.get("canonical_name", ""), c.get("aliases"))
            ),
            "role": (c.get("role") or "").lower(),
            "id": c.get("id"),
            "mentions": c.get("mention_count", 0) or 0,
        }
        for c in analysis.get("characters") or []
        if c.get("canonical_name")
    ]

    truth_chars = [
        {
            "canonical": t["canonical_name"],
            "names": _name_set(t["canonical_name"], t.get("aliases")),
            "match_keys": _match_keys(_name_set(t["canonical_name"], t.get("aliases"))),
            "alias_set": {normalize_name(a) for a in (t.get("aliases") or [])},
            "required": t.get("required", True),
        }
        for t in truth.get("characters") or []
    ]

    # --- Greedy one-to-one matching on match-key intersection --------------
    matches: list[tuple[dict, dict]] = []
    used_pred = set()
    for t in truth_chars:
        best = None
        for i, p in enumerate(predicted):
            if i in used_pred:
                continue
            if t["match_keys"] & p["match_keys"]:
                # Prefer canonical-name hits over alias-only hits
                exact = normalize_name(t["canonical"]) in p["names"]
                if best is None or (exact and not best[1]):
                    best = (i, exact)
        if best is not None:
            used_pred.add(best[0])
            matches.append((t, predicted[best[0]]))

    matched_truth = {id(t) for t, _ in matches}

    # --- Character recall (required truth characters found) ----------------
    required = [t for t in truth_chars if t["required"]]
    required_found = [t for t in required if id(t) in matched_truth]
    recall = len(required_found) / len(required) if required else None
    missing = [t["canonical"] for t in required if id(t) not in matched_truth]

    # --- Main-cast precision (predicted main-tier chars that are real) -----
    truth_names_all: set[str] = set()
    truth_tokens_all: set[str] = set()
    for t in truth_chars:
        truth_names_all |= t["names"]
        for n in t["names"]:
            truth_tokens_all |= {w for w in n.split() if len(w) >= 3}
    main_preds = [p for p in predicted if p["role"] in _MAIN_TIER_ROLES]
    if not main_preds:
        # Older outputs without role tiers: judge the top 2x-required characters
        # by mention count instead.
        k = max(2 * len(required), 1)
        main_preds = sorted(predicted, key=lambda p: -p["mentions"])[:k]
    spurious = [p["canonical"] for p in main_preds if not (p["names"] & truth_names_all)]
    precision = (
        (len(main_preds) - len(spurious)) / len(main_preds) if main_preds else None
    )

    f1 = None
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = 2 * precision * recall / (precision + recall)

    # --- Alias micro-P/R over matched characters ----------------------------
    tp = fp = fn = 0
    alias_errors: list[str] = []
    for t, p in matches:
        truth_aliases = t["alias_set"]
        pred_aliases = {
            n for n in p["names"] if n != normalize_name(p["canonical"])
        }
        # Acceptable surface forms: truth aliases, truth canonical, and any
        # single-token fragment of those (a surname or first name alone is a
        # legitimate alias — "Carraway" for "Nick Carraway").
        acceptable = set(truth_aliases) | {normalize_name(t["canonical"])}
        fragments = set()
        for n in acceptable:
            fragments |= {w for w in n.split() if len(w) >= 3}
        acceptable |= fragments
        for a in pred_aliases:
            if a in acceptable:
                tp += 1
            else:
                fp += 1
                alias_errors.append(f"{p['canonical']} +'{a}'")
        for a in truth_aliases:
            if a not in pred_aliases and a != normalize_name(p["canonical"]):
                fn += 1
    alias_precision = tp / (tp + fp) if (tp + fp) else None
    alias_recall = tp / (tp + fn) if (tp + fn) else None

    # --- Forbidden names (hallucination canaries) ---------------------------
    forbidden_norm = {normalize_name(f) for f in truth.get("forbidden") or []}
    forbidden_hits = sorted(
        {
            p["canonical"]
            for p in predicted
            if p["names"] & forbidden_norm
        }
    )

    # --- Narrator ------------------------------------------------------------
    narrator_correct = None
    truth_narr = truth.get("narrator")
    pred_narr_id = analysis.get("narrator_character_id")
    pred_narr_names: set[str] = set()
    if pred_narr_id:
        for p in predicted:
            if p["id"] == pred_narr_id:
                pred_narr_names = p["names"]
                break
    if truth_narr is None:
        narrator_correct = pred_narr_id is None
    else:
        narrator_correct = bool(
            pred_narr_names & _name_set(truth_narr, [])
        )

    return {
        "book": truth.get("book", "?"),
        "character_recall": recall,
        "main_cast_precision": precision,
        "character_f1": f1,
        "missing_required": missing,
        "spurious_main_cast": spurious,
        "alias_precision": alias_precision,
        "alias_recall": alias_recall,
        "alias_false_positives": alias_errors[:10],
        "forbidden_hits": forbidden_hits,
        "narrator_correct": narrator_correct,
        "predicted_total": len(predicted),
        "truth_required": len(required),
    }


def score_files(analysis_path: str | Path, truth_path: str | Path) -> dict:
    """Score an analysis JSON file against a ground-truth JSON file."""
    with open(analysis_path) as f:
        analysis = json.load(f)
    with open(truth_path) as f:
        truth = json.load(f)
    return score_against_truth(analysis, truth)


def format_score(s: dict) -> str:
    """Human-readable one-book report."""
    def pct(v):
        return "n/a" if v is None else f"{v * 100:.0f}%"

    lines = [
        f"== {s['book']} ==",
        f"  character F1:        {pct(s['character_f1'])}  "
        f"(recall {pct(s['character_recall'])}, precision {pct(s['main_cast_precision'])})",
        f"  alias P/R:           {pct(s['alias_precision'])} / {pct(s['alias_recall'])}",
        f"  narrator:            {'OK' if s['narrator_correct'] else 'WRONG' if s['narrator_correct'] is not None else 'n/a'}",
        f"  predicted chars:     {s['predicted_total']}",
    ]
    if s["missing_required"]:
        lines.append(f"  MISSING required:    {', '.join(s['missing_required'])}")
    if s["spurious_main_cast"]:
        lines.append(f"  SPURIOUS main cast:  {', '.join(s['spurious_main_cast'])}")
    if s["forbidden_hits"]:
        lines.append(f"  FORBIDDEN present:   {', '.join(s['forbidden_hits'])}")
    if s["alias_false_positives"]:
        lines.append(f"  alias FPs:           {'; '.join(s['alias_false_positives'])}")
    return "\n".join(lines)
