# Oracle Monitor TUI Improvements

## Summary of Changes (2026-01-25)

The oracle monitor has been significantly improved to address sluggish behavior, unclear phase transitions, and limited thinking panel functionality.

---

## 1. Fixed Stage Display Issues

### Removed Misleading Stage Numbers
- **Problem**: Stage numbers (1-6) didn't match actual execution order, which varies between parallel/sequential modes
- **Solution**: Removed `STAGE_ORDER` dict and `get_stage_order()` function entirely
- **Result**: Stages now display without numbers, showing just the stage name (e.g., "Chapter Detection" instead of "1. Chapter Detection")

### Improved Staleness Detection
- **Problem**: 10-minute timeout for PROGRESS.json was too long, causing stale stage info to persist
- **Solution**: Reduced timeout from 600s to 120s (2 minutes)
- **Result**: Stage info clears much faster when analysis completes

### Heartbeat-Based Stage Clearing
- **Problem**: When analysis completes and Claude starts evaluating, old stage info would remain displayed
- **Solution**: Now uses heartbeat age as primary source of truth:
  - If heartbeat < 60s: Trust it completely, show current stage
  - If heartbeat > 60s: Clear stage info (analysis done or Claude working)
- **Result**: Stage display accurately reflects whether local LLM is actively running

---

## 2. Clear Phase Transitions

### Enhanced Phase Display
- **Problem**: Not obvious when local LLM vs Claude is working
- **Solution**: Added contextual labels to phase display in status bar:
  - `evaluate (Claude working)` - bold magenta
  - `fix (Claude fixing)` - bold yellow
  - `running_analysis (Local LLM)` - bold cyan
  - `complete` - bold green
- **Result**: Immediately obvious which system is active

### Panel Headers Show Active Phase
- **Local LLM Activity Panel**:
  - Shows "Analysis complete - idle" when Claude is working
  - Shows "Claude is now evaluating" message in magenta
  - Panel renamed from "OLLAMA ACTIVITY" to "LOCAL LLM ACTIVITY"

- **Claude Activity Panel**:
  - Header shows `[ACTIVE - EVALUATE]` when Claude is working
  - Uses magenta highlighting for active phases

### Stage Line Shows Claude Phase
- **Problem**: No indication in STAGE line when Claude is evaluating
- **Solution**: When no active local LLM stage but in Claude phase, shows:
  - `STAGE: Analysis Complete - Claude Evaluating` (bold magenta)
- **Result**: Clear visual indicator that analysis is done and evaluation has begun

---

## 3. Improved Heartbeat Display

### Better Status Indicators
- **Renamed**: "HEARTBEAT" → "LLM HEARTBEAT" (clarifies it tracks local LLM, not Claude)
- **Improved age thresholds**:
  - < 5s: "active" (green)
  - 5-30s: no label (yellow)
  - 30-60s: "idle" (yellow faded)
  - 60-300s: "analysis complete" if in Claude phase, otherwise "inactive" (dim)
  - > 300s: "inactive" (dim)
- **Context-aware**: Shows "analysis complete" in green when heartbeat is stale but Claude is working
- **Result**: Heartbeat status provides meaningful context instead of just showing staleness

---

## 4. Expandable Thinking Panel

### Toggle View Mode
- **Press 't'**: Toggle between compact and expanded modes
- **Compact mode** (default):
  - Shows last 3 thinking blocks
  - Truncates each block to 800 chars
  - Max height: 15 lines
  - Header: `[Press 't' to expand, 'x' to export]`

- **Expanded mode**:
  - Shows ALL thinking blocks (up to 50 captured)
  - No truncation
  - Max height: 40 lines
  - Wider word wrap (100 chars vs 80)
  - Header: `[EXPANDED - Press 't' to collapse]`

### Export Functionality
- **Press 'x'**: Export complete thinking history to file
- **Export location**: `oracle-loop/state/CLAUDE_THINKING_EXPORT.txt`
- **Export format**:
  ```
  # Claude Thinking Export
  # Exported: 2026-01-25 14:30:00
  # Text: frankenstein
  # Attempt: 3
  # Total blocks: 25

  ## Block 1/25
  [Full thinking text with no truncation]

  ## Block 2/25
  [Full thinking text...]
  ```
- **Notifications**: Toast messages confirm export success/failure

### Increased Thinking Capture
- **Problem**: Only kept last 10 thinking blocks
- **Solution**: Now keeps last 50 blocks
- **Result**: More complete thinking history available for export and review

---

## 5. Better Block Numbering

### Contextual Block Indices
- **Compact mode**: Shows position in full list (e.g., `[23/25]` not just `[1]`)
- **Expanded mode**: Shows sequential numbering (e.g., `[1]`, `[2]`, etc.)
- **Header**: Always shows total available blocks (e.g., `[Showing last 3 of 25 blocks]`)
- **Result**: Always clear how many blocks exist and which ones you're viewing

---

## 6. Updated Keybindings

New keybindings shown in footer:
- **q**: Quit
- **p**: Toggle pause
- **r**: Manual refresh
- **n**: Focus notes input
- **t**: Toggle thinking panel (NEW)
- **x**: Export thinking (NEW)

---

## Technical Changes

### Modified Functions
1. `parse_progress_file()`: Reduced staleness timeout from 600s to 120s
2. `parse_heartbeat()`: Added heartbeat trust logic
3. `parse_latest_log()`: Increased thinking block retention from 10 to 50
4. `get_state()`: Added heartbeat-based stage clearing logic

### New/Modified Classes
1. `ClaudeThinkingPanel`:
   - Added `expanded` parameter
   - Added dynamic block selection (3 vs all)
   - Added truncation control
   - Added contextual numbering

2. `OracleMonitorApp`:
   - Added `thinking_expanded` reactive property
   - Added `action_toggle_thinking()` method
   - Added `action_export_thinking()` method
   - Updated `_update_widgets()` to pass expanded state

### CSS Changes
- Added `.expanded` class for `ClaudeThinkingPanel` with `max-height: 40`

### Removed Code
- `STAGE_ORDER` dict (lines 22-32)
- `get_stage_order()` function (lines 35-40)

---

## Usage Tips

1. **Monitor a running oracle loop**:
   ```bash
   cd oracle-loop
   python -m monitor.oracle_monitor
   ```

2. **View full thinking chain**:
   - Press 't' to expand the thinking panel
   - Scroll through all captured reasoning
   - Press 't' again to return to compact view

3. **Export for analysis**:
   - Press 'x' to export thinking to file
   - File location: `oracle-loop/state/CLAUDE_THINKING_EXPORT.txt`
   - Can be opened in any text editor or analyzed further

4. **Understand current phase**:
   - Check PHASE line in status bar - includes context labels
   - Check panel headers for "ACTIVE" indicators
   - Check STAGE line - shows "Claude Evaluating" when appropriate
   - Check LLM HEARTBEAT - context-aware status

---

## Testing Checklist

- [ ] Monitor starts without errors
- [ ] Stage numbers removed from display
- [ ] Stale stage info clears within 2 minutes of analysis completion
- [ ] Phase transitions clearly show "Claude working" vs "Local LLM"
- [ ] Press 't' toggles thinking panel size
- [ ] Expanded mode shows more blocks and full text
- [ ] Press 'x' exports thinking to file
- [ ] Export file contains all blocks with proper formatting
- [ ] Heartbeat display shows context-aware messages
- [ ] Panel headers update to show active phase

---

## Future Improvements (Not Implemented)

- Individual thinking block selection/expansion
- Search/filter within thinking blocks
- Copy individual blocks to clipboard
- Diff view between attempts
- Syntax highlighting for code in thinking blocks
