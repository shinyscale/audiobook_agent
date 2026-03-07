# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 21
- **Phase:** awaiting_fix
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ✗ (FAILING — father/son merged, Johnny fragment)
  - Completeness: 5/10
  - Identity Resolution: 4/10
  - Alias Grouping: 7/10
- Character Profiles: 5.5/10 ✗ (FAILING — merged character contamination, null summaries)
- Chapter Summaries: 5/10 ✗ (FAILING — hallucinated Uncle Bill on battlefield, wrong encounter attribution)
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 7.5/10 ✗ (FAILING — BOM in title, author name as title)
- **Overall: 6.5/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold)

## Improvements from Attempt 20

1. **Narrator correctly assigned to Uncle Bill** ✓ (was John in attempt 20)
2. **"the American, sir" absorbed as alias of John Donaldson** ✓ (was false separate character in attempt 20)
3. **Uncle Bill's profile now correct** — "elderly, grizzled, small man" ✓ (was on John's profile in attempt 20)

## Detailed Evaluation

### 2.1 Structure Detection: 9/10 ✓
- 1 section for continuous short story — correct
- Title is null — minor issue

### 2.2 Character Extraction: 5/10 ✗

**Completeness (5/10):**
- John Donaldson (33 mentions) — merges father AND son into one entry
- Uncle Bill (18 mentions, narrator=True) ✓
- Ted Frith (5 mentions) ✓
- Johnny (1 mention) — false fragment, should be merged with John/the son
- MISSING: Joe Barron, Margaret Donaldson (minor characters)

**Identity Resolution (4/10):**
- Father/son NOT split — the central identity puzzle remains unresolved. "John Donaldson" (father, the shabby American civilian) and "John" (son, the WWI ambulance driver) are merged into one 33-mention character.
- Johnny is a separate 1-mention fragment that should be the son
- Narrator correctly Uncle Bill ✓ (improvement)

**Alias Grouping (7/10):**
- John Donaldson aliases: ['American, sir', 'John'] — "American, sir" correctly grouped ✓
- Uncle Bill aliases: ['Bill'] ✓
- Johnny aliases: ['his son'] — reasonable but character shouldn't exist separately
- Ted Frith aliases: ['Ted'] ✓

### 2.3 Character Profiles: 5.5/10 ✗

- **Uncle Bill**: Physical description correct ✓ ("elderly, grizzled, small man"). Relationships: Ted Frith (colleague) ✓. Major improvement from attempt 20.
- **John Donaldson**: Description is the father's ("Tall, dark-skinned, shabby clothing... resembles his son's beauty") — internally coherent but the merged character means the son's attributes aren't captured. No relationships listed.
- **Johnny**: No physical description. Relationship "Ted Frith: close friend" — WRONG, Ted is Uncle Bill's colleague, not Johnny's friend.
- **Ted Frith**: Relationships reasonable (Johnny: close friend — wrong, Uncle Bill: colleague ✓, John Donaldson: concerned observer — OK).
- character_summary null for ALL characters.

### 2.4 Chapter Summaries: 5/10 ✗

The section summary has major hallucinations:
1. "the narrator encounters that same man—John Donaldson" — Since narrator=Uncle Bill, this says Uncle Bill encounters John Donaldson on the Italian front. WRONG. Uncle Bill is never on the battlefield. It's John (the son) who encounters his father there.
2. "Uncle Bill, mortally wounded on a battlefield, confesses his fear of dishonor" — COMPLETELY FABRICATED. Uncle Bill is never wounded or on any battlefield. He is the elderly frame narrator at home.
3. "his son John embraces him" — Implies Uncle Bill's son is John. John is Uncle Bill's NEPHEW, not son.
4. Opening section (letter, fishing trip, WWI service) is largely correct ✓
5. "American, sir" declaration correctly captured ✓

The nested narration structure (Uncle Bill telling John's story about encountering his father) continues to confuse the LLM, which collapses the frame narrator into the battlefield narrative.

### 2.5 Pronunciation Guide: 9/10 ✓
- 15 entries, all with IPA ✓
- Excellent foreign terms: Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux
- Homographs: live, minute, read, close, moderate — appropriate
- Minor entries: "dum-dums" and "mayn't" are valid flags

### 2.6 HTML Presentation: 7.5/10 ✗
- Title shows "Mary Raymond Shipman Andrews" (author) instead of story title
- BOM character in title and h1
- Navigation functional ✓
- Character sections organized ✓

## Current Issues (Priority Order)

### CRITICAL
1. **Father/son merge: John Donaldson father + John son = one character** [Identity Resolution]
   - Problem: The father ("John Donaldson", shabby American civilian who abandoned family, dies on battlefield) and son ("John", beautiful youngster, ambulance driver, Uncle Bill's nephew) are merged into a single 33-mention character.
   - Evidence: 21 attempts and STEP 3.95/3.95b fires ~50% of the time due to LLM non-determinism in summary wording.
   - Root cause: The father/son split depends on specific LLM summary phrasings that Pattern A-D regex can match. When the LLM uses different wording, no pattern fires.
   - Location: `src/agents/characters.py` STEP 3.95/3.95b
   - Fix approach: The split logic needs to be MORE ROBUST — either add more pattern variants, or use a completely different signal (e.g., the physical description contrast "elderly shabby" vs "beautiful youngster" in the source text, or the alias "American, sir" as an indicator of a separate identity).

2. **Summary hallucination: Uncle Bill on battlefield, mortally wounded** [Summaries]
   - Problem: Summary says "Uncle Bill, mortally wounded on a battlefield" — completely fabricated. Uncle Bill is never on a battlefield.
   - Evidence: The story's nested narration (Uncle Bill recounting John's experience) is collapsed by the LLM.
   - Location: `src/pipeline/summarizer/` — the summarizer doesn't distinguish frame narrator from story protagonist
   - Fix approach: Summarizer prompt could include narrator identity to help the LLM maintain narrative layers. Also, the "narrator encounters" phrasing cascades from the merged character issue — if father/son were split, the summary might correctly attribute encounters.

### HIGH
3. **Johnny 1-mention fragment character** [Completeness]
   - Problem: "Johnny" (id=main_cast_0, 1 mention) is a separate character from "John Donaldson" (33 mentions). Johnny is the son's nickname and should be an alias of the son character.
   - Evidence: aliases=['his son'] confirms this IS the son
   - Location: V2 character extraction — Johnny should merge into the son character, but since father/son aren't split, there's no clean "son-only" character to merge into.
   - Note: This resolves naturally if the father/son split works — Johnny would merge into the son character.

4. **character_summary null for all characters** [Profiles]
   - Problem: No character summaries generated for any character
   - Evidence: `character_summary: null` for all 4 characters
   - Location: Profile generation in `src/pipeline/character_profiling/` or `src/analyzer.py`
   - Note: This was also null in attempt 20. May be a config or model issue with qwen3-next.

### MEDIUM
5. **HTML title shows author name instead of story title** [Presentation]
   - Problem: `<title>Mary Raymond Shipman Andrews</title>` — should be the story title
   - BOM character also present
   - Location: Title extraction in ingestion or HTML template
   - Fix: Strip BOM in ingestion; use story title not author name

6. **Johnny→Ted Frith "close friend" relationship is wrong** [Profiles]
   - Problem: Johnny shows relationship with Ted Frith as "close friend". Ted is Uncle Bill's colleague, not Johnny's friend.
   - Location: Profile generation — likely LLM hallucination during profiling

7. **Missing minor characters: Joe Barron, Margaret Donaldson** [Completeness]
   - Low mention count characters. F6/F6b reconciliation non-deterministic.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | 0 | Baseline. Narrator misidentification cascades into profiles + summaries |
| 2 | 6.6 | +0.05 | Narrator fix worked (Bill=narrator). Johnny still missing, summary wrong. |
| 3 | 6.0 | -0.55 | REGRESSION. "American, sir" false character stole narrator. |
| 4 | 6.4 | -0.15 | Co-present guard fixed "American, sir" but narrator regressed. |
| 5 | 6.7 | +0.15 | Plot summary improved. Narrator metadata still wrong. |
| 6 | 7.0 | +0.45 | Uncle Bill narrator. John Donaldson false secondary narrator. |
| 7 | 6.9 | +0.35 | Narrator guard worked. Boy disappeared (false merge). |
| 8 | 7.85 | +1.30 | Father/son split, plot summary fixed, profiles improved. |
| 9 | 8.0 | +1.45 | Cross-character alias contamination fixed. |
| 10 | 7.0 | +0.45 | REGRESSION. Father/son merge recurred (LLM non-determinism). |
| 11 | 7.2 | +0.65 | Narrator fix, relationship cleanup. STEP 3.95 didn't fire. |
| 12 | 7.7 | +1.15 | Father/son split via alias contradiction! |
| 13 | 5.8 | -0.75 | SEVERE REGRESSION. STEP 3.95 didn't fire, narrator wrong. |
| 14 | 7.6 | +1.05 | Father/son split, Johnny gone, summaries improved. |
| 15 | 6.85 | +0.30 | Shabby civilian merged, narrator fixed. Father/son re-merged. |
| 16 | 6.95 | +0.40 | LLM produced no parenthetical this time. Johnny phantom returned. |
| 17 | 6.2 | -0.35 | Summary severe regression. Wrong narrator in plot summary. |
| 18 | 6.8 | +0.25 | No Johnny phantom. Father/son still merged. |
| 19 | 7.7 | +1.15 | Father/son split (Pattern D)! "Dying Uncle Bill" gone. |
| 20 | 5.95 | -0.60 | SEVERE REGRESSION. Father/son split didn't fire. "American, sir" false char. Narrator wrong. |
| 21 | 6.5 | -0.05 | Narrator fixed ✓, "American sir" absorbed ✓. Father/son still merged. Summary hallucinations. |

## Fix History
- Attempt 11-20: See previous entries
- Attempt 21: Re-analysis with new config (commit 90b62a5). Narrator and alias absorption improved. Father/son split still not firing. Summary hallucinations persist.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Wrong narrator | `narrator.py` | Fixed |
| 3 | Johnny exact_firstname guard | `characters.py` | REGRESSION — REVERTED |
| 4 | Co-present guard Step 5.4.5 | `characters.py` | Partial |
| 5 | Narrator guard / merge direction | `characters.py`, `narrator.py` | Bug/wrong direction |
| 6 | narrator.py detect() crash | `narrator.py` | Fixed |
| 7 | John Donaldson false narrator | `narrator.py` | Fixed |
| 8 | Role assignment / summaries | `characters.py`, `summarizer.py` | Fixed |
| 9 | Cross-character alias / relationships | `main_cast.py`, `analyzer.py` | Partial |
| 11 | STEP 3.95 / relationships / narrator | `characters.py`, `post_corrections.py`, `analyzer.py` | Mixed |
| 12 | STEP 3.95 alias contradiction | `characters.py` | Fixed |
| 13 | force_parenthetical / narrator_instruction | `post_corrections.py`, `generator.py` | Never fired |
| 14 | STEP 3.97 nickname phantom | `characters.py` | Fixed |
| 15 | STEP 5.4.6c / Step 6.6 narrator | `characters.py`, `analyzer.py` | Fixed |
| 16-18 | STEP 3.95/3.95b patterns | `characters.py` | Intermittent |
| 19 | STEP 3.95b Pattern D / narrator survival | `characters.py`, `generator.py` | Fixed |
| 20 | Cross-alias decontamination / parenthetical rel labels | `characters.py`, `post_corrections.py` | UNTESTABLE |
| 21 | Re-analysis with new config (90b62a5) | No code changes | Narrator ✓, alias ✓, split ✗ |

**Pattern: STEP 3.95/3.95b fires ~50% of the time due to LLM non-determinism in summary wording. This is the core instability. 21 attempts and the split has fired in attempts 8, 9, 12, 14, 19 — and failed in 10, 11, 13, 15, 16, 17, 18, 20, 21.**

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Config: max_tokens=8192, context_length=32768, think_mode=false
- Duration: 16m 50s

## Next Action
The father/son split is the ROOT CAUSE of most failures (characters, profiles, summaries all cascade from it). After 21 attempts, the regex-pattern approach in STEP 3.95/3.95b is fundamentally unreliable (~50% fire rate).

**Recommended fix approach:** Instead of adding more LLM-dependent regex patterns, implement a DETERMINISTIC split signal. Options:
1. **Physical description contrast**: The source text describes the father as "shabby", "dark-skinned", elderly vs the son as "beautiful youngster", "towering". If the profiler finds contradictory age/appearance descriptors for a single character, trigger a split.
2. **Alias-based split**: When "American, sir" (a dialogue phrase) is an alias AND the character has aliases like "Johnny"/"the boy" (youth terms), that contradiction signals two identities.
3. **Mention-context analysis**: Check if the character's mentions span incompatible contexts (pre-war childhood + battlefield death), which would indicate merged identities.

The fix phase should focus ONLY on making the father/son split deterministic. All other issues (profiles, summaries, Johnny fragment) cascade from this.
