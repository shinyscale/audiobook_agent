# Output Quality Improvements PRD v1

## Summary

Improvements to audiobook analysis output quality based on Gatsby analysis review.
Addresses character hallucination, HTML UX, and pronunciation organization.

**Created**: 2026-01-09
**Status**: Draft

---

## Requirements

### BUG-001: Character Profile Hallucination Prevention
**Priority**: Critical
**Category**: Bug Fix
**Status**: `passes: true`

**Problem**: LLM generates character profiles with hallucinated information.
Example: "Mrs. Claud Roosevelt" conflated casual text reference with location name,
then invented fictional backstory.

**Root Cause**: `analyzer.py:1033-1075` - Profile generation has no validation.
Only ~500 chars context provided, LLM invents "role, traits, relationships".

**Acceptance Criteria**:
- [ ] Profile claims must be grounded in actual text passages
- [ ] Each profile statement links to source evidence
- [ ] Entity disambiguation prevents name/location conflation
- [ ] Confidence scoring for profile quality
- [ ] Low-confidence profiles flagged for human review

**Files to Modify**:
- `src/analyzer.py` - `_generate_character_profile()` method
- `src/pipeline/character_extraction/consensus.py` - Entity disambiguation
- `src/models.py` - Add evidence fields to Character model

**Verification**:
- Re-run Gatsby analysis
- "Mrs. Claud Roosevelt" should NOT appear, or should be flagged as low-confidence
- All character profiles should have linked evidence

---

### FEAT-001: Tabbed HTML Interface
**Priority**: High
**Category**: Feature
**Status**: `passes: true`

**Problem**: HTML report is one long scroller, hard to navigate for narrators.

**Solution**: Replace scroll-based navigation with tabbed interface.

**Acceptance Criteria**:
- [ ] Tab bar with: Overview | Chapters | Characters | Pronunciations
- [ ] Active tab highlighted, content switches without page reload
- [ ] URL hash updates for deep linking (#characters, #pronunciations)
- [ ] Mobile-responsive tab design
- [ ] Print view still shows all sections

**Files to Modify**:
- `src/export/html_report.py` - Add tabbed navigation HTML/CSS/JS

**Verification**:
- Open generated HTML report
- Click each tab, verify content switches
- Verify URL updates with hash
- Print preview shows all sections

---

### FEAT-002: Per-Chapter Pronunciation Guide
**Priority**: High
**Category**: Feature
**Status**: `passes: true`

**Problem**: Pronunciation guide is one 470-item list. Narrators need per-chapter lists.

**Solution**: Add "By Chapter" view alongside existing "By Type" view.

**Acceptance Criteria**:
- [ ] Toggle between "By Type" and "By Chapter" views
- [ ] Chapter view shows: "Chapter 1 (24 words)" expandable sections
- [ ] Each chapter section lists pronunciations appearing in that chapter
- [ ] Words appearing in multiple chapters shown in each relevant chapter
- [ ] Preserve existing "By Type" view as default

**Files to Modify**:
- `src/export/html_report.py` - Add chapter-based pronunciation rendering
- Uses existing `chapter_indices` field in PronunciationEntry model

**Verification**:
- Toggle to "By Chapter" view
- Verify each chapter shows correct word count
- Spot-check that words appear in correct chapters

---

### FEAT-003: Evidence-Linked Character Profiles
**Priority**: Medium
**Category**: Feature
**Status**: `passes: true`

**Problem**: Character profiles are prose blobs with no source attribution.

**Solution**: Link profile claims to source text passages.

**Acceptance Criteria**:
- [ ] Profile shows clickable evidence citations [1], [2], [3]
- [ ] Clicking citation expands to show source passage
- [ ] Evidence limited to actual text, not LLM interpretation
- [ ] Profile generation prompt requires evidence for each claim

**Files to Modify**:
- `src/analyzer.py` - Update profile generation prompt
- `src/models.py` - Add `profile_evidence` field
- `src/export/html_report.py` - Render evidence citations

**Verification**:
- Character profiles show numbered citations
- Clicking citation reveals source quote from text

---

### FEAT-004: Confidence Indicators in HTML
**Priority**: Low
**Category**: Feature
**Status**: `passes: true`

**Problem**: Low-confidence items not visually distinguished in HTML report.

**Solution**: Add visual confidence indicators.

**Acceptance Criteria**:
- [ ] High confidence: green indicator
- [ ] Medium confidence: yellow indicator
- [ ] Low confidence: red indicator with "Review" badge
- [ ] Hover shows confidence percentage
- [ ] Filter to show only low-confidence items

**Files to Modify**:
- `src/export/html_report.py` - Add confidence badges and styling

**Verification**:
- Characters/pronunciations show colored confidence badges
- Hover reveals percentage
- Filter shows only flagged items

---

### FEAT-005: Searchable Pronunciation List
**Priority**: Low
**Category**: Feature
**Status**: `passes: true`

**Problem**: Large pronunciation lists (400+ items) hard to search.

**Solution**: Add search/filter box for pronunciations.

**Acceptance Criteria**:
- [ ] Search box filters pronunciation list in real-time
- [ ] Filter by word, IPA, or flag reason
- [ ] Clear button resets filter
- [ ] Show "X of Y items" count

**Files to Modify**:
- `src/export/html_report.py` - Add search JavaScript

**Verification**:
- Type in search box, list filters immediately
- Counter updates with filtered count
- Clear button restores full list

---

## Implementation Order

1. **BUG-001** - Critical bug fix first
2. **FEAT-001** - Tabbed interface (foundation for other UX improvements)
3. **FEAT-002** - Per-chapter pronunciations (user-requested)
4. **FEAT-003** - Evidence linking (enhances trust in profiles)
5. **FEAT-004** - Confidence indicators (quick win)
6. **FEAT-005** - Search (nice to have)

---

## Testing Plan

| Test | Requirement | Method |
|------|-------------|--------|
| No hallucinated characters | BUG-001 | Re-run Gatsby, check for "Mrs. Claud Roosevelt" |
| Tabs work | FEAT-001 | Manual click-through test |
| Per-chapter accuracy | FEAT-002 | Spot-check 3 chapters against source |
| Evidence links work | FEAT-003 | Click citations, verify quotes |
| Confidence colors | FEAT-004 | Visual inspection |
| Search filters | FEAT-005 | Type queries, verify filtering |

---

## Ralph-Wiggum Integration

To implement with ralph-loop:

```bash
/ralph-loop --max-iterations 10 "Implement BUG-001 from spec/output-quality-v1.prd.md.
Read the PRD, implement the fix, run tests, and output <promise>COMPLETE</promise>
when the acceptance criteria are met."
```

Track progress by updating `passes: false` to `passes: true` for each requirement.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1 | 2026-01-09 | Initial PRD with 6 requirements |
