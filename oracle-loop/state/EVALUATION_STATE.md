# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 6.7

---

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
- Character Profiles: 8/10 ✓
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 9/10 ✓
- **Overall: 7.4/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

---

## Evaluation Details

### 1. Structure Detection: 9/10 ✓

"The Cask of Amontillado" is a short story with no chapter divisions. The tool correctly identified it as a single structural unit (1 chapter). The structure entry shows:
- Type: chapter
- Word count: 2,354 (correct for this ~2,500 word story)
- Estimated duration: ~15 minutes (reasonable)

Minor issue: `title: null` - could ideally be "The Cask of Amontillado" for a titleless short story, but this is acceptable.

### 2. Character Extraction: 5/10 ✗ (FAILING)

**Expected characters for "The Cask of Amontillado":**
1. Montresor - narrator/protagonist (many mentions via "I")
2. Fortunato - victim/antagonist (frequently named)
3. Luchresi - mentioned rival (only referenced, never appears)

**Found:**
1. Fortunato (main_cast_1) - ✓ Correct, 14 mentions
2. the Amontillado (main_cast_2) - ⚠️ PROBLEMATIC - treated as character
3. Luchresi (supporting_0) - ✓ Correct, 4 mentions
4. Montresor (F6 reconciled) - ✓ Correct, but only 1 mention counted

**Critical Issues:**

1. **"the Amontillado" extracted as a character with WRONG aliases**
   - "the Amontillado" is the wine (a MacGuffin/plot device), NOT a character
   - It has absurd aliases: "the catacombs", "catacombs", "the trowel", "trowel"
   - These are completely unrelated objects merged together
   - The catacombs are a PLACE, the trowel is a MURDER WEAPON, the Amontillado is WINE
   - **Root cause:** The main_cast extractor is merging unrelated non-character entities
   - Per rubric: "symbolic objects/forces" CAN be valid, but the alias merging is completely wrong
   - **Location:** `src/pipeline/character_extraction_v2/main_cast.py` - alias grouping logic

2. **Montresor mention count is only 1**
   - Montresor is the first-person narrator - he doesn't say his own name often
   - The system correctly identified him as narrator (is_narrator: true)
   - However, the low mention count may have prevented proper main_cast detection
   - He was picked up by F6 reconciliation (hash ID), not main_cast extraction
   - This is borderline acceptable for first-person narrators

### 3. Character Profiles: 8/10 ✓

**Fortunato profile:** Excellent
- Appearance: "jester's motley with conical cap and bells" ✓ (accurate from text)
- Personality: "Confident in wine expertise, easily deceived by flattery" ✓
- Voice guidance: "boisterous then frantic" ✓ (captures character arc)
- Verbal tics: "He! he! he!", "Amontillado!" ✓
- Example quotes excellent: "For the love of God, Montresor!" ✓

**Montresor profile:** Good
- Personality: "cold calculation, deceptive charm" ✓
- Voice guidance: "authoritative" ✓
- Verbal tics: "feigned concern" ✓
- Missing: His family motto connection ("Nemo me impune lacessit")

**The Amontillado profile:** Problematic but not egregious
- Description contains garbled text: "abstract诱饵 that drives" (Chinese character corruption)
- Profile body acknowledges it's "never described physically"

Minor deduction for the text corruption, but main characters are well-profiled.

### 4. Chapter Summaries: 9/10 ✓

The single summary is excellent:
- Captures carnival setting ✓
- Describes Fortunato's costume ✓
- Notes the descent into catacombs ✓
- Mentions the Medoc wine ✓
- Describes the chaining and sealing ✓
- Includes the "fifty years undisturbed" ending ✓

Length is appropriate (~150 words). No hallucinations detected. All key plot points present.

### 5. Pronunciation Guide: 7/10 ✗ (FAILING)

**Correct flagging (good):**
- Amontillado (/ˌæmən.tɪˈlɑː.doʊ/) ✓
- Fortunato (/ˌfɔːr.tuˈnɑː.toʊ/) ✓
- Montresor (/ˌmɒn.trəˈsɔːr/) ✓
- Luchresi (/luːkˈrɛ.si/) ✓
- flambeaux (/flæmˈboʊ/) ✓ (French)
- nitre (/ˈnaɪ.trər/) ✓ (British spelling of niter)
- roquelaire (/ˈrɒk.ə.lɛːr/) ✓ (archaic cloak)
- requiescat (/rɛkwiˈɛskæt/) - good (Latin "rest in peace")

**False positives (unnecessary flags):**
- jingled, jingling - common English words
- cough's - common word with possessive
- filmy - common English word
- leer - common English word
- familiarly - common English word
- tight-fitting - common hyphenated word
- to-day - archaic spelling but pronunciation obvious
- insufferably - common English word
- recoiling - common English word
- unsteadily - common English word
- ejaculated - common word (means "exclaimed" in Victorian usage)
- endeavoured - British spelling but pronunciation obvious
- promiscuously - common English word (means "in confusion" here)
- hearken/hearkened - archaic but pronunciation clear
- labours - British spelling, obvious
- clamourer/clamoured - common words
- re-echoed, re-erected, reapproached - common words with re- prefix

**Score Impact:**
- 53 total pronunciations flagged
- Approximately 25-30 are false positives (common English words)
- Over 50% false positive rate is too high

### 6. HTML Presentation: 9/10 ✓

- Navigation tabs work (Chapters, Characters, Pronunciations)
- Character profiles well-organized with expandable evidence sections
- Pronunciation filtering available with search box
- Summary display is clear and readable
- Minor issue: text corruption in Amontillado profile ("诱饵" Chinese characters)

---

## Current Issues (Priority Order)

### CRITICAL

1. **False entity merging: "the Amontillado" has nonsense aliases**
   - Problem: "the Amontillado" (wine) merged with "catacombs" (place) and "trowel" (object)
   - Evidence: Aliases shown as: "the catacombs, catacombs, the trowel, trowel"
   - These are completely unrelated nouns in the text
   - **ID pattern:** main_cast_2 → Fix in main_cast.py
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` - alias merging logic
   - Root cause: LLM may be grouping all non-human noun phrases together
   - Fix approach: Add semantic coherence check - aliases must be linguistically related (same referent) not just "non-person nouns mentioned together"

### HIGH

2. **Excessive pronunciation false positives**
   - Problem: ~50% of flagged words are common English (jingled, filmy, leer, etc.)
   - Evidence: 53 flags, ~25-30 unnecessary
   - Location: `src/pipeline/pronunciation/` or pronunciation agent
   - Fix approach: Add word frequency filtering - skip words in top 10K common English words unless they have unusual context (homographs, foreign origin, etc.)

### MEDIUM

3. **Text corruption in output**
   - Problem: Chinese characters "诱饵" appear in Amontillado profile
   - Evidence: "remaining an abstract诱饵 that drives the characters' actions"
   - Location: Likely LLM response parsing or encoding issue
   - Fix approach: Add UTF-8 sanitization to strip non-Latin characters from English text output

4. **"the Amontillado" shouldn't be a main character at all**
   - While symbolic objects CAN be valid, the Amontillado wine is a MacGuffin, not a character with agency
   - It doesn't "drive the plot" in a character sense - Montresor uses it as bait
   - Lower priority than the alias issue since the rubric allows symbolic objects

---

## Fix History
(First attempt - no previous fixes)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| - | - | - | - |

---

## Configuration Audit

Checked `_config` and `_profiling` sections:

- Model configuration appears appropriate
- Character extraction used competitive consensus (good)
- 40 LLM calls total, 49,970 tokens (reasonable for short text)
- Warnings in output noted Amontillado character issue

---

## Next Action

Run PROMPT_fix.md to address:
1. CRITICAL: Fix alias merging logic to prevent unrelated nouns from being grouped
2. HIGH: Add common word filtering to pronunciation flagging
