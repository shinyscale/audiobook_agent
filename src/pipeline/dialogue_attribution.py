"""
CRF-based dialogue speaker attribution.

Uses a Conditional Random Field (sklearn-crfsuite) to attribute speakers to
dialogue turns within a chapter. The CRF models conversation sequences —
capturing alternation patterns, speech verb proximity, and character name
distance that rule-based approaches miss.

Integration pattern matches scalpels: availability check → try/except → LLM fallback.

Requires: sklearn-crfsuite (optional dependency, like torch for scalpels)
"""

import logging
import pickle
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = _PROJECT_ROOT / "models"
CRF_MODEL_PATH = MODELS_DIR / "attribution_crf" / "attribution_crf.pkl"

# Speech verbs used as features (common dialogue tags in literary fiction)
SPEECH_VERBS = {
    "said", "says", "asked", "replied", "answered", "whispered", "shouted",
    "cried", "exclaimed", "murmured", "muttered", "called", "demanded",
    "insisted", "suggested", "continued", "added", "remarked", "observed",
    "declared", "announced", "explained", "repeated", "began", "interrupted",
    "protested", "agreed", "admitted", "confessed", "pleaded", "groaned",
    "sighed", "laughed", "sobbed", "screamed", "yelled", "snapped",
    "growled", "hissed", "stammered", "stuttered", "urged", "warned",
    "promised", "threatened", "begged", "commanded", "ordered", "told",
    "inquired", "wondered", "mused", "thought", "reflected", "pondered",
}

# Quote extraction pattern — matches "..." and "..." style quotes
QUOTE_PATTERN = re.compile(
    r'(?:'
    r'\u201c([^\u201d]{3,})\u201d'  # "smart quotes"
    r'|'
    r'"([^"]{3,})"'                  # "straight quotes"
    r')',
    re.DOTALL,
)


def _crfsuite_available() -> bool:
    """Check if sklearn-crfsuite is installed."""
    try:
        import sklearn_crfsuite  # noqa: F401
        return True
    except ImportError:
        return False


def crf_available() -> bool:
    """Check if the CRF dialogue attribution model is available."""
    if not _crfsuite_available():
        return False
    return CRF_MODEL_PATH.exists()


# ── Feature Extraction ───────────────────────────────────────────────────────

def extract_dialogue_turns(chapter_text: str) -> list[dict]:
    """Extract an ordered sequence of dialogue turns from chapter text.

    Each turn contains the quoted text, its position, and surrounding context
    for feature extraction.

    Returns:
        List of dicts with keys: quote, position, pre_context, post_context
    """
    turns = []
    for match in QUOTE_PATTERN.finditer(chapter_text):
        quote = match.group(1) or match.group(2)
        if not quote or len(quote.strip()) < 3:
            continue

        start = match.start()
        end = match.end()

        # Extract surrounding context (200 chars before/after)
        pre_start = max(0, start - 200)
        post_end = min(len(chapter_text), end + 200)

        turns.append({
            "quote": quote.strip(),
            "position": start,
            "pre_context": chapter_text[pre_start:start],
            "post_context": chapter_text[end:post_end],
        })

    return turns


def _find_speech_verb(context: str) -> Optional[str]:
    """Find a speech verb in the given context string."""
    words = re.findall(r'\b\w+\b', context.lower())
    for word in words:
        if word in SPEECH_VERBS:
            return word
    return None


def _find_character_in_context(context: str, characters: list[str]) -> Optional[str]:
    """Find the closest character name mentioned in context.

    Checks for full names and individual name parts (e.g., "Tom" matches
    "Tom Buchanan"). Returns the full canonical name.
    """
    context_lower = context.lower()
    for char_name in characters:
        # Check full name
        if char_name.lower() in context_lower:
            return char_name
        # Check individual parts (first name, last name)
        for part in char_name.split():
            if len(part) > 2 and part.lower() in context_lower:
                return char_name
    return None


def _detect_pronoun_gender(context: str) -> str:
    """Detect dominant pronoun gender in context. Returns 'male', 'female', or 'neutral'."""
    context_lower = " " + context.lower() + " "
    male_pronouns = sum(len(re.findall(rf'\b{p}\b', context_lower)) for p in ["he", "him", "his"])
    female_pronouns = sum(len(re.findall(rf'\b{p}\b', context_lower)) for p in ["she", "her", "hers"])
    if male_pronouns > female_pronouns:
        return "male"
    elif female_pronouns > male_pronouns:
        return "female"
    return "neutral"


def extract_features(
    turn: dict,
    turn_index: int,
    total_turns: int,
    characters: list[str],
    prev_speaker: Optional[str] = None,
    prev_prev_speaker: Optional[str] = None,
) -> dict[str, str]:
    """Extract CRF features for a single dialogue turn.

    Features are designed for literary fiction dialogue attribution:
    - Speech verb presence and type in surrounding narration
    - Character name proximity (who is mentioned near the quote)
    - Pronoun gender agreement
    - Position in chapter and conversation sequence
    - Alternation pattern (previous speakers)
    """
    pre = turn["pre_context"]
    post = turn["post_context"]
    quote = turn["quote"]

    features = {}

    # Feature 1: Speech verb in pre-context (e.g., "said Tom" before the quote)
    pre_verb = _find_speech_verb(pre[-80:])  # Last 80 chars before quote
    features["pre_speech_verb"] = pre_verb or "none"

    # Feature 2: Speech verb in post-context (e.g., after the quote "...said Tom")
    post_verb = _find_speech_verb(post[:80])  # First 80 chars after quote
    features["post_speech_verb"] = post_verb or "none"

    # Feature 3: Character name in pre-context (nearest)
    pre_char = _find_character_in_context(pre[-100:], characters)
    features["pre_character"] = pre_char or "none"

    # Feature 4: Character name in post-context (nearest)
    post_char = _find_character_in_context(post[:100], characters)
    features["post_character"] = post_char or "none"

    # Feature 5: Speech verb + character combination (strongest signal)
    # "said Tom" pattern — verb in post-context with character
    if post_verb and post_char:
        features["post_verb_char"] = f"{post_verb}_{post_char}"
    else:
        features["post_verb_char"] = "none"
    # "Tom said" pattern — character in pre-context with verb
    if pre_verb and pre_char:
        features["pre_verb_char"] = f"{pre_verb}_{pre_char}"
    else:
        features["pre_verb_char"] = "none"

    # Feature 6: Pronoun gender in surrounding context
    features["pre_pronoun_gender"] = _detect_pronoun_gender(pre[-100:])
    features["post_pronoun_gender"] = _detect_pronoun_gender(post[:100])

    # Feature 7: Quote length bucket
    qlen = len(quote)
    if qlen < 20:
        features["quote_length"] = "very_short"
    elif qlen < 50:
        features["quote_length"] = "short"
    elif qlen < 150:
        features["quote_length"] = "medium"
    elif qlen < 500:
        features["quote_length"] = "long"
    else:
        features["quote_length"] = "very_long"

    # Feature 8: Position in chapter (early/middle/late)
    if total_turns > 0:
        rel_pos = turn_index / max(1, total_turns - 1)
        if rel_pos < 0.25:
            features["chapter_position"] = "early"
        elif rel_pos < 0.75:
            features["chapter_position"] = "middle"
        else:
            features["chapter_position"] = "late"
    else:
        features["chapter_position"] = "only"

    # Feature 9: Previous speaker (alternation pattern)
    features["prev_speaker"] = prev_speaker or "none"
    features["prev_prev_speaker"] = prev_prev_speaker or "none"

    # Feature 10: Is this likely a continuation? (short gap, no speech verb)
    if not pre_verb and not post_verb and not pre_char and not post_char:
        features["likely_continuation"] = "true"
    else:
        features["likely_continuation"] = "false"

    # Feature 11: Quote starts with address? ("My dear...", "Listen...")
    first_words = quote[:30].lower()
    if any(first_words.startswith(addr) for addr in [
        "my dear", "listen", "look", "tell me", "well,", "oh,", "ah,",
        "no,", "yes,", "please", "come", "wait", "stop",
    ]):
        features["starts_with_address"] = "true"
    else:
        features["starts_with_address"] = "false"

    # Feature 12: Contains question mark?
    features["is_question"] = "true" if "?" in quote else "false"

    return features


# ── CRF Model ────────────────────────────────────────────────────────────────

class CRFDialogueAttributor:
    """CRF-based dialogue speaker attribution.

    Given a chapter's text and a list of known characters, extracts dialogue
    turns and predicts which character speaks each line.

    Uses sklearn-crfsuite for sequence labeling — the CRF models the
    conversation flow (alternation, speech verbs, name proximity) rather
    than treating each quote independently.
    """

    _instance: Optional["CRFDialogueAttributor"] = None

    def __new__(cls) -> "CRFDialogueAttributor":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._model = None
        return cls._instance

    def _load_model(self):
        """Load the CRF model from disk."""
        if self._model is not None:
            return

        import sklearn_crfsuite

        if not CRF_MODEL_PATH.exists():
            raise FileNotFoundError(f"CRF model not found: {CRF_MODEL_PATH}")

        with open(CRF_MODEL_PATH, "rb") as f:
            self._model = pickle.load(f)

        logger.info(f"Loaded CRF dialogue attribution model from {CRF_MODEL_PATH}")

    def attribute(
        self,
        chapter_text: str,
        characters: list[str],
        confidence_threshold: float = 0.6,
    ) -> list[dict]:
        """Attribute speakers to dialogue turns in a chapter.

        Args:
            chapter_text: Full text of the chapter
            characters: List of known character names in this chapter
            confidence_threshold: Minimum confidence to include attribution

        Returns:
            List of dicts with keys: quote, speaker, confidence, position
        """
        self._load_model()

        if not characters:
            return []

        turns = extract_dialogue_turns(chapter_text)
        if not turns:
            return []

        # Build feature sequences
        features_seq = []
        prev_speaker = None
        prev_prev_speaker = None

        for i, turn in enumerate(turns):
            feats = extract_features(
                turn, i, len(turns), characters,
                prev_speaker=prev_speaker,
                prev_prev_speaker=prev_prev_speaker,
            )
            features_seq.append(feats)

            # For feature extraction, use the explicit character name if found
            # (this helps the CRF's alternation features even before prediction)
            post_char = _find_character_in_context(turn["post_context"][:100], characters)
            pre_char = _find_character_in_context(turn["pre_context"][-100:], characters)
            explicit = post_char or pre_char
            prev_prev_speaker = prev_speaker
            prev_speaker = explicit

        # CRF prediction (sequence labeling)
        pred_labels = self._model.predict([features_seq])[0]

        # Extract marginal probabilities for confidence
        try:
            marginals = self._model.predict_marginals([features_seq])[0]
        except Exception:
            marginals = [{}] * len(pred_labels)

        results = []
        for i, (turn, label, marg) in enumerate(zip(turns, pred_labels, marginals)):
            confidence = marg.get(label, 0.5) if marg else 0.5

            # Map CRF label back to character name
            speaker = label if label in characters or label == "UNKNOWN" else "UNKNOWN"

            if speaker != "UNKNOWN" and confidence >= confidence_threshold:
                results.append({
                    "quote": turn["quote"][:200],  # Truncate for storage
                    "speaker": speaker,
                    "confidence": round(confidence, 3),
                    "position": turn["position"],
                })

        return results

    def unload(self):
        """Unload the model to free memory."""
        self._model = None
        CRFDialogueAttributor._instance = None
        logger.info("Unloaded CRF dialogue attribution model")
