"""
Oracle Loop Monitor TUI.
Real-time monitoring of the oracle loop progress using Textual.
"""

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Header, Footer, Static, Input
from textual.binding import Binding
from textual.reactive import reactive
from rich.text import Text


# Stage order removed - it's misleading since execution order varies between parallel/sequential modes
# Instead we just show stage names without numbers


@dataclass
class Score:
    """Individual category score."""
    name: str
    value: float
    max_value: float = 10.0
    passing: bool = True


@dataclass
class Issue:
    """An issue from evaluation."""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str


@dataclass
class Commit:
    """A git commit."""
    hash: str
    message: str
    timestamp: str = ""  # Relative time like "2 hours ago"


@dataclass
class ClaudeActivity:
    """Activity from Claude during evaluation/fix phases."""
    tool_name: str
    description: str
    timestamp: str = ""


@dataclass
class OracleState:
    """Combined state from all data sources."""
    # From EVALUATION_STATE.md
    text_name: str = ""
    attempt: int = 0
    max_attempts: int = 5
    phase: str = "unknown"
    threshold: float = 8.0

    # Scores
    structure_score: Optional[float] = None
    characters_score: Optional[float] = None
    profiles_score: Optional[float] = None
    summaries_score: Optional[float] = None
    pronunciation_score: Optional[float] = None
    presentation_score: Optional[float] = None
    overall_score: Optional[float] = None

    # Issues
    issues: list[Issue] = field(default_factory=list)

    # From manifest.json
    total_texts: int = 0
    completed_texts: int = 0

    # From logs / progress file
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    current_stage: str = ""  # Current analysis stage (e.g., "Chapter Detection")

    # Ollama/local LLM activity (from PROGRESS.json during analysis)
    ollama_llm_calls: int = 0
    ollama_items_processed: int = 0
    ollama_items_total: Optional[int] = None
    ollama_avg_latency_ms: float = 0.0
    ollama_last_latency_ms: float = 0.0

    # Recent commits
    commits: list[Commit] = field(default_factory=list)

    # Claude activity (from iteration logs)
    claude_activities: list[ClaudeActivity] = field(default_factory=list)
    claude_last_message: str = ""
    thinking_text: list[str] = field(default_factory=list)  # Claude's reasoning/explanations

    # Metadata
    last_updated: datetime = field(default_factory=datetime.now)

    # Loop status
    loop_running: bool = False

    # Heartbeat data (real-time analysis activity)
    heartbeat_age_seconds: Optional[float] = None  # Seconds since last heartbeat
    heartbeat_activity: str = ""  # Last activity type (llm_call, stage_started, etc.)
    heartbeat_stage: str = ""  # Current stage from heartbeat
    heartbeat_stage_elapsed: float = 0.0  # Seconds in current stage
    heartbeat_total_elapsed: float = 0.0  # Total analysis time
    heartbeat_llm_calls: int = 0  # LLM calls in current stage

    # Process status
    analysis_running: bool = False  # Is audiobook-prep analyze process running
    analysis_pid: Optional[int] = None  # PID of analysis process

    # Recent stderr output
    recent_stderr: list[str] = field(default_factory=list)

    # Competitive consensus info
    competitive_mode: str = "none"  # none, single, multi
    competitive_stages: list[str] = field(default_factory=list)
    competitive_models: list[str] = field(default_factory=list)

    # Live voting data
    recent_votes: list[dict] = field(default_factory=list)


class StateParser:
    """Parse state from various data sources."""

    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path.cwd()

    def parse_evaluation_state(self) -> dict:
        """Parse EVALUATION_STATE.md for current text, attempt, phase, scores."""
        # Try multiple locations for state file
        possible_paths = [
            self.base_dir / "state" / "EVALUATION_STATE.md",
            self.base_dir / "EVALUATION_STATE.md",
            self.base_dir.parent / "state" / "EVALUATION_STATE.md",  # if running from monitor/
        ]
        state_file = None
        for path in possible_paths:
            if path.exists():
                state_file = path
                break
        if not state_file:
            return {}

        content = state_file.read_text()
        result = {}

        # Parse text name
        match = re.search(r'\*\*Name:\*\*\s*(\w+)', content)
        if match:
            result['text_name'] = match.group(1)

        # Parse attempt
        match = re.search(r'\*\*Attempt:\*\*\s*(\d+)', content)
        if match:
            result['attempt'] = int(match.group(1))

        # Parse phase
        match = re.search(r'\*\*Phase:\*\*\s*(\w+)', content)
        if match:
            result['phase'] = match.group(1)

        # Parse threshold
        match = re.search(r'threshold:\s*([\d.]+)', content)
        if match:
            result['threshold'] = float(match.group(1))

        # Parse scores - look for patterns like "Structure Detection: 10/10"
        score_patterns = [
            (r'Structure(?:\s+Detection)?:\s*([\d.]+)/10', 'structure_score'),
            (r'Character(?:\s+Extraction)?:\s*([\d.]+)/10', 'characters_score'),
            (r'(?:Character\s+)?Profiles?:\s*([\d.]+)/10', 'profiles_score'),
            (r'(?:Chapter\s+)?Summar(?:y|ies):\s*([\d.]+)/10', 'summaries_score'),
            (r'Pronunciation(?:\s+Guide)?:\s*([\d.]+)/10', 'pronunciation_score'),
            (r'(?:HTML\s+)?Presentation:\s*([\d.]+)/10', 'presentation_score'),
        ]

        for pattern, key in score_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                result[key] = float(match.group(1))

        # Parse overall score
        match = re.search(r'\*\*Overall:\s*([\d.]+)/10', content)
        if match:
            result['overall_score'] = float(match.group(1))

        # Parse model from configuration (e.g., "- Structure: qwen3:30b-instruct")
        model_match = re.search(r'-\s*(?:Structure|Characters|Summaries):\s*(\S+)', content)
        if model_match:
            result['model'] = model_match.group(1)

        # Parse issues
        issues = []
        # Look for issue patterns: "CRITICAL | description" or "### CRITICAL" followed by numbered items
        issue_pattern = re.compile(r'^\d+\.\s*\*\*(.+?)\*\*', re.MULTILINE)

        # Find sections for each severity
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            section_match = re.search(rf'###\s*{severity}.*?(?=###|\Z)', content, re.DOTALL | re.IGNORECASE)
            if section_match:
                section = section_match.group(0)
                for item_match in issue_pattern.finditer(section):
                    issues.append(Issue(severity=severity, description=item_match.group(1)))

        result['issues'] = issues

        return result

    def parse_manifest(self) -> dict:
        """Parse manifest.json for overall progress."""
        # Try multiple locations for manifest file
        possible_paths = [
            self.base_dir / "state" / "manifest.json",
            self.base_dir / "manifest.json",
            self.base_dir.parent / "state" / "manifest.json",  # if running from monitor/
        ]
        manifest_file = None
        for path in possible_paths:
            if path.exists():
                manifest_file = path
                break
        if not manifest_file:
            return {}

        try:
            with open(manifest_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

        texts = data.get('texts', [])
        total = len(texts)
        completed = sum(1 for t in texts if t.get('complete', False))
        threshold = data.get('quality_threshold', 8.0)

        # Competitive consensus config
        competitive_mode = data.get('competitive_mode', 'none')
        competitive_stages = data.get('competitive_stages', [])
        competitive_models = data.get('competitive_models', [])

        return {
            'total_texts': total,
            'completed_texts': completed,
            'threshold': threshold,
            'competitive_mode': competitive_mode,
            'competitive_stages': competitive_stages,
            'competitive_models': competitive_models,
        }

    def parse_git_log(self, count: int = 5) -> list[Commit]:
        """Get recent git commits with timestamps."""
        try:
            # Format: hash|relative_time|subject
            result = subprocess.run(
                ['git', 'log', f'--format=%h|%ar|%s', f'-{count}'],
                capture_output=True,
                text=True,
                cwd=self.base_dir,
                timeout=5
            )
            if result.returncode != 0:
                return []

            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 2)
                    if len(parts) >= 3:
                        commits.append(Commit(
                            hash=parts[0],
                            timestamp=parts[1],
                            message=parts[2]
                        ))
                    elif len(parts) == 2:
                        commits.append(Commit(hash=parts[0], message=parts[1]))
            return commits
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return []

    def parse_progress_file(self) -> dict:
        """Parse PROGRESS.json for current analysis stage and LLM metrics."""
        # Try multiple locations for PROGRESS.json
        # When running from oracle-loop/, the progress file is in oracle-loop/output/
        possible_paths = [
            self.base_dir / "output" / "PROGRESS.json",  # oracle-loop/output/
            self.base_dir.parent / "output" / "PROGRESS.json",  # ../output/
            Path("/home/zacharymandrews/Tools/audiobook_agent/output/PROGRESS.json"),
            Path("/home/zacharymandrews/Tools/audiobook_agent/oracle-loop/output/PROGRESS.json"),
        ]

        progress_file = None
        for path in possible_paths:
            if path.exists():
                progress_file = path
                break

        if not progress_file:
            return {}

        try:
            # Check if file was modified recently (within 2 minutes)
            # If stale, the analysis has completed and we shouldn't show old stage
            import time
            mtime = progress_file.stat().st_mtime
            age_seconds = time.time() - mtime
            if age_seconds > 120:  # 2 minutes - analysis likely complete
                return {}  # Stale progress file, don't show old stage data

            with open(progress_file) as f:
                data = json.load(f)
            return {
                'current_stage': data.get('stage', ''),
                'stage_model': data.get('model', ''),
                'input_tokens': data.get('input_tokens', 0),
                'output_tokens': data.get('output_tokens', 0),
                # New fields for Ollama activity panel
                'llm_calls': data.get('llm_calls', 0),
                'items_processed': data.get('items_processed', 0),
                'items_total': data.get('items_total'),
                'avg_latency_ms': data.get('avg_latency_ms', 0.0),
                'last_latency_ms': data.get('last_latency_ms', 0.0),
            }
        except (json.JSONDecodeError, IOError, OSError):
            return {}

    def parse_analysis_output(self, text_name: str) -> dict:
        """Parse analysis.json from output directory for token usage."""
        output_dir = self.base_dir / "output" / text_name

        # If output dir doesn't exist, check parent directory (oracle-loop structure)
        if not output_dir.exists():
            parent_output = self.base_dir.parent / "output" / text_name
            if parent_output.exists():
                output_dir = parent_output

        analysis_file = output_dir / "analysis.json"

        if not analysis_file.exists():
            return {}

        try:
            with open(analysis_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

        profiling = data.get('_profiling', {})
        totals = profiling.get('totals', {})
        stages = profiling.get('stages', [])

        # Sum input/output tokens from stages
        input_tokens = sum(s.get('tokens_prompt', 0) for s in stages)
        output_tokens = sum(s.get('tokens_completion', 0) for s in stages)

        # Get model from first stage that has one
        model = ""
        for stage in stages:
            if stage.get('model_used'):
                model = stage['model_used']
                break

        return {
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'llm_calls': totals.get('llm_calls', 0),
        }

    def parse_latest_log(self) -> dict:
        """Parse latest log file for model, token usage, and Claude activities."""
        logs_dir = self.base_dir / "logs"

        # If logs dir doesn't exist, check parent directory (oracle-loop structure)
        if not logs_dir.exists():
            parent_logs = self.base_dir.parent / "logs"
            if parent_logs.exists():
                logs_dir = parent_logs

        if not logs_dir.exists():
            return {}

        # Find latest iteration log
        log_files = sorted(logs_dir.glob("iteration_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not log_files:
            return {}

        latest_log = log_files[0]
        model = ""
        input_tokens = 0
        output_tokens = 0
        activities = []
        last_message = ""
        thinking_texts = []  # Collect Claude's text/reasoning blocks

        # Get log file modification time for timestamp estimation
        try:
            log_mtime = datetime.fromtimestamp(latest_log.stat().st_mtime)
        except OSError:
            log_mtime = datetime.now()

        try:
            lines = latest_log.read_text().strip().split('\n')
            total_lines = len(lines)

            for line_num, line in enumerate(lines):
                try:
                    data = json.loads(line.strip())
                    msg_type = data.get('type')

                    if msg_type == 'assistant':
                        msg = data.get('message', {})
                        if msg.get('model'):
                            model = msg['model']
                        usage = msg.get('usage', {})
                        input_tokens += usage.get('input_tokens', 0)
                        input_tokens += usage.get('cache_read_input_tokens', 0)
                        input_tokens += usage.get('cache_creation_input_tokens', 0)
                        output_tokens += usage.get('output_tokens', 0)

                        # Extract tool calls from content
                        content = msg.get('content', [])
                        for block in content:
                            if block.get('type') == 'tool_use':
                                tool_name = block.get('name', 'unknown')
                                tool_input = block.get('input', {})

                                # Create human-readable description
                                desc = self._describe_tool_use(tool_name, tool_input)
                                activities.append(ClaudeActivity(
                                    tool_name=tool_name,
                                    description=desc,
                                    timestamp=""  # Will be set below for recent activities
                                ))

                            elif block.get('type') == 'text':
                                # Capture text blocks for thinking panel
                                text = block.get('text', '')
                                if text and len(text.strip()) > 10:  # Skip trivial texts
                                    thinking_texts.append(text)
                                    # Also keep last message for backwards compatibility
                                    last_message = text[:500] + "..." if len(text) > 500 else text

                except json.JSONDecodeError:
                    continue
        except IOError:
            pass

        # Assign timestamps to the final batch of activities we return
        # Use the log file's modification time and estimate earlier timestamps
        recent_activities = activities[-12:]
        mtime_str = log_mtime.strftime("%H:%M:%S")

        # Estimate timestamps based on position in the activity list
        # Assume roughly 10-30 seconds per activity on average
        for i, activity in enumerate(recent_activities):
            # Most recent activities (last 3) get the current file mtime
            if i >= len(recent_activities) - 3:
                activity.timestamp = mtime_str
            else:
                # Estimate earlier timestamps by subtracting time from mtime
                # Newer items are closer to the end, so older items get larger offsets
                offset_index = len(recent_activities) - 3 - i
                offset_seconds = offset_index * 20  # ~20 seconds per activity estimate
                estimated_time = log_mtime - timedelta(seconds=offset_seconds)
                activity.timestamp = estimated_time.strftime("%H:%M:%S")

        return {
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'activities': recent_activities,
            'last_message': last_message,
            'thinking_texts': thinking_texts[-50:],  # Keep last 50 text blocks for export
        }

    def _describe_tool_use(self, tool_name: str, tool_input: dict) -> str:
        """Create human-readable description of a tool use."""
        if tool_name == 'Read':
            path = tool_input.get('file_path', '')
            return f"Reading {Path(path).name}" if path else "Reading file"

        elif tool_name == 'Edit':
            path = tool_input.get('file_path', '')
            return f"Editing {Path(path).name}" if path else "Editing file"

        elif tool_name == 'Write':
            path = tool_input.get('file_path', '')
            return f"Writing {Path(path).name}" if path else "Writing file"

        elif tool_name == 'Bash':
            cmd = tool_input.get('command', '')
            desc = tool_input.get('description', '')
            if desc:
                return desc[:50]
            elif cmd:
                # Truncate long commands
                return cmd[:50] + "..." if len(cmd) > 50 else cmd
            return "Running command"

        elif tool_name == 'Grep':
            pattern = tool_input.get('pattern', '')
            return f"Searching for '{pattern[:30]}'" if pattern else "Searching"

        elif tool_name == 'Glob':
            pattern = tool_input.get('pattern', '')
            return f"Finding files: {pattern[:30]}" if pattern else "Finding files"

        elif tool_name == 'Task':
            desc = tool_input.get('description', '')
            return f"Agent: {desc[:40]}" if desc else "Running agent"

        elif tool_name == 'TodoWrite':
            return "Updating task list"

        else:
            return f"{tool_name}"

    def parse_heartbeat(self) -> dict:
        """Parse HEARTBEAT.json for real-time analysis activity."""
        import time

        # Try multiple locations for heartbeat file
        # When running from oracle-loop/, the heartbeat is in oracle-loop/output/
        possible_paths = [
            self.base_dir / "output" / "HEARTBEAT.json",  # oracle-loop/output/
            self.base_dir.parent / "output" / "HEARTBEAT.json",  # ../output/
            Path("/home/zacharymandrews/Tools/audiobook_agent/output/HEARTBEAT.json"),
            Path("/home/zacharymandrews/Tools/audiobook_agent/oracle-loop/output/HEARTBEAT.json"),
        ]

        heartbeat_file = None
        for path in possible_paths:
            if path.exists():
                heartbeat_file = path
                break

        if not heartbeat_file:
            return {}

        try:
            with open(heartbeat_file) as f:
                data = json.load(f)

            # Calculate age of heartbeat
            unix_time = data.get('unix_time', 0)
            age_seconds = time.time() - unix_time if unix_time else None

            return {
                'heartbeat_age_seconds': age_seconds,
                'heartbeat_activity': data.get('activity', ''),
                'heartbeat_stage': data.get('stage', ''),
                'heartbeat_stage_elapsed': data.get('stage_elapsed_seconds', 0.0),
                'heartbeat_total_elapsed': data.get('total_elapsed_seconds', 0.0),
                'heartbeat_llm_calls': data.get('llm_calls_this_stage', 0),
                'heartbeat_model': data.get('model', ''),
            }
        except (json.JSONDecodeError, IOError, OSError):
            return {}

    def parse_live_votes(self) -> list[dict]:
        """Parse VOTES.json for live consensus voting data during analysis."""
        import time

        # Try multiple locations for votes file
        possible_paths = [
            self.base_dir / "output" / "VOTES.json",
            self.base_dir.parent / "output" / "VOTES.json",
            Path("/home/zacharymandrews/Tools/audiobook_agent/output/VOTES.json"),
        ]

        votes_file = None
        for path in possible_paths:
            if path.exists():
                votes_file = path
                break

        if not votes_file:
            return []

        try:
            # Check if file was modified recently (within 5 minutes)
            mtime = votes_file.stat().st_mtime
            age_seconds = time.time() - mtime
            if age_seconds > 300:  # 5 minutes - stale
                return []

            with open(votes_file) as f:
                data = json.load(f)

            # Return last 10 votes
            votes = data.get('votes', [])
            return votes[-10:]
        except (json.JSONDecodeError, IOError, OSError):
            return []

    def check_loop_running(self) -> bool:
        """Check if oracle-loop.sh is currently running."""
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'oracle-loop.sh'],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def check_analysis_running(self) -> tuple[bool, Optional[int]]:
        """Check if audiobook-prep analysis is currently running.

        Returns:
            Tuple of (is_running, pid or None)
        """
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'audiobook-prep analyze'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                pid = int(result.stdout.strip().split()[0])
                return True, pid
            return False, None
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            return False, None

    def get_recent_stderr(self, lines: int = 8) -> list[str]:
        """Get recent stderr lines from task output files.

        Looks for the most recently modified .output file in Claude's task dir.
        """
        task_dir = Path("/tmp/claude/-home-zacharymandrews-Tools-audiobook-agent-oracle-loop/tasks")
        if not task_dir.exists():
            return []

        try:
            # Find most recently modified output file
            output_files = list(task_dir.glob("*.output"))
            if not output_files:
                return []

            latest = max(output_files, key=lambda p: p.stat().st_mtime)

            # Check if file is recent (within 10 minutes)
            import time
            age = time.time() - latest.stat().st_mtime
            if age > 600:
                return []

            # Read last N lines
            content = latest.read_text()
            all_lines = content.strip().split('\n')

            # Filter to stderr lines and clean up
            stderr_lines = []
            for line in all_lines[-lines*2:]:  # Read more, filter down
                # Skip empty lines and non-stderr
                if not line.strip():
                    continue
                # Remove [stderr] prefix if present
                if line.startswith('[stderr] '):
                    line = line[9:]
                stderr_lines.append(line)

            return stderr_lines[-lines:]
        except (IOError, OSError):
            return []

    def get_state(self) -> OracleState:
        """Get combined state from all sources."""
        state = OracleState()

        # Parse evaluation state
        eval_state = self.parse_evaluation_state()
        state.text_name = eval_state.get('text_name', '')
        state.attempt = eval_state.get('attempt', 0)
        state.phase = eval_state.get('phase', 'unknown')
        state.threshold = eval_state.get('threshold', 8.0)
        state.structure_score = eval_state.get('structure_score')
        state.characters_score = eval_state.get('characters_score')
        state.profiles_score = eval_state.get('profiles_score')
        state.summaries_score = eval_state.get('summaries_score')
        state.pronunciation_score = eval_state.get('pronunciation_score')
        state.presentation_score = eval_state.get('presentation_score')
        state.overall_score = eval_state.get('overall_score')
        state.issues = eval_state.get('issues', [])

        # Parse manifest
        manifest = self.parse_manifest()
        state.total_texts = manifest.get('total_texts', 0)
        state.completed_texts = manifest.get('completed_texts', 0)
        if 'threshold' in manifest:
            state.threshold = manifest['threshold']

        # Competitive consensus config
        state.competitive_mode = manifest.get('competitive_mode', 'none')
        state.competitive_stages = manifest.get('competitive_stages', [])
        state.competitive_models = manifest.get('competitive_models', [])

        # Parse live votes
        state.recent_votes = self.parse_live_votes()

        # Parse progress file for current stage (real-time during analysis)
        progress_data = self.parse_progress_file()
        state.current_stage = progress_data.get('current_stage', '')

        # Populate Ollama activity metrics from progress data
        state.ollama_llm_calls = progress_data.get('llm_calls', 0)
        state.ollama_items_processed = progress_data.get('items_processed', 0)
        state.ollama_items_total = progress_data.get('items_total')
        state.ollama_avg_latency_ms = progress_data.get('avg_latency_ms', 0.0)
        state.ollama_last_latency_ms = progress_data.get('last_latency_ms', 0.0)

        # Try to get model/tokens from analysis output (local LLM usage)
        analysis_data = self.parse_analysis_output(state.text_name) if state.text_name else {}

        # Always parse log data for Claude activities
        log_data = self.parse_latest_log()
        state.claude_activities = log_data.get('activities', [])
        state.claude_last_message = log_data.get('last_message', '')
        state.thinking_text = log_data.get('thinking_texts', [])

        # Choose model based on phase
        # During evaluate/fix phases, show Claude model; during analysis, show local LLM
        claude_phases = ('awaiting_evaluation', 'evaluate', 'awaiting_fix', 'fix')

        if state.phase in claude_phases and log_data.get('model'):
            # Show Claude model during evaluate/fix phases
            state.model = log_data.get('model', '')
            state.input_tokens = log_data.get('input_tokens', 0)
            state.output_tokens = log_data.get('output_tokens', 0)
        elif state.current_stage and progress_data.get('stage_model'):
            # Show local LLM model during active analysis stage
            # Use real-time tokens from PROGRESS.json (updated during analysis)
            state.model = progress_data.get('stage_model', '')
            state.input_tokens = progress_data.get('input_tokens', 0)
            state.output_tokens = progress_data.get('output_tokens', 0)
        elif analysis_data:
            # Fall back to analysis output data (completed analysis)
            state.model = analysis_data.get('model', '')
            state.input_tokens = analysis_data.get('input_tokens', 0)
            state.output_tokens = analysis_data.get('output_tokens', 0)
        else:
            # Final fallback to log data
            state.model = log_data.get('model', '')
            state.input_tokens = log_data.get('input_tokens', 0)
            state.output_tokens = log_data.get('output_tokens', 0)

        # Parse git log
        state.commits = self.parse_git_log(12)

        # Check if loop is running
        state.loop_running = self.check_loop_running()

        # Check if analysis process is running
        state.analysis_running, state.analysis_pid = self.check_analysis_running()

        # Get recent stderr output
        state.recent_stderr = self.get_recent_stderr(8)

        # Parse heartbeat for real-time activity (more reliable than PROGRESS.json)
        heartbeat = self.parse_heartbeat()
        if heartbeat:
            state.heartbeat_age_seconds = heartbeat.get('heartbeat_age_seconds')
            state.heartbeat_activity = heartbeat.get('heartbeat_activity', '')
            state.heartbeat_stage = heartbeat.get('heartbeat_stage', '')
            state.heartbeat_stage_elapsed = heartbeat.get('heartbeat_stage_elapsed', 0.0)
            state.heartbeat_total_elapsed = heartbeat.get('heartbeat_total_elapsed', 0.0)
            state.heartbeat_llm_calls = heartbeat.get('heartbeat_llm_calls', 0)

            # Use heartbeat as primary source of truth for current stage
            # If heartbeat is fresh (< 60s), trust it completely
            # If stale (> 60s), clear the stage (analysis likely complete or Claude is working)
            if state.heartbeat_age_seconds is not None:
                if state.heartbeat_age_seconds < 60:
                    # Fresh heartbeat - use its data
                    if heartbeat.get('heartbeat_stage'):
                        state.current_stage = heartbeat['heartbeat_stage']
                    if heartbeat.get('heartbeat_model'):
                        state.model = heartbeat['heartbeat_model']
                else:
                    # Stale heartbeat - clear stage info (analysis done or Claude evaluating)
                    state.current_stage = ""

        state.last_updated = datetime.now()

        return state


def format_tokens(count: int) -> str:
    """Format token count as human-readable string."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    else:
        return str(count)


class StatusBar(Static):
    """Status bar showing current text, attempt, phase, model, tokens."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()

        # Loop status indicator (prominent, at start of first line)
        if self.state.loop_running:
            text.append("● RUNNING", style="bold green")
        else:
            text.append("● STOPPED", style="bold red")
        text.append("  │  ", style="dim")

        # Line 1: TEXT, ATTEMPT, PHASE
        text.append("TEXT: ", style="bold cyan")
        text.append(self.state.text_name or "(none)", style="white")
        text.append("  │  ", style="dim")
        text.append("ATTEMPT: ", style="bold cyan")
        text.append(f"{self.state.attempt}", style="white")
        text.append("  │  ", style="dim")
        text.append("PHASE: ", style="bold cyan")

        # Make phase very obvious with colors and context
        phase_style = "white"
        phase_label = self.state.phase
        if self.state.phase in ("awaiting_evaluation", "evaluate"):
            phase_style = "bold magenta"
            phase_label = f"{self.state.phase} (Claude working)"
        elif self.state.phase in ("awaiting_fix", "fix"):
            phase_style = "bold yellow"
            phase_label = f"{self.state.phase} (Claude fixing)"
        elif self.state.phase == "complete":
            phase_style = "bold green"
        elif self.state.phase == "running_analysis":
            phase_style = "bold cyan"
            phase_label = f"{self.state.phase} (Local LLM)"
        elif self.state.phase == "awaiting_analysis":
            phase_style = "cyan"
            phase_label = f"{self.state.phase} (starting)"
        text.append(phase_label, style=phase_style)

        text.append("\n")

        # Line 2: MODEL, TOKENS, STAGE
        text.append("MODEL: ", style="bold cyan")
        model_name = self.state.model.split('/')[-1] if self.state.model else "(none)"
        # Truncate model name if too long
        if len(model_name) > 25:
            model_name = model_name[:22] + "..."
        text.append(model_name, style="white")
        text.append("  │  ", style="dim")
        text.append("TOKENS: ", style="bold cyan")
        text.append(f"{format_tokens(self.state.input_tokens)} in / {format_tokens(self.state.output_tokens)} out", style="white")

        # Show current stage if running analysis
        if self.state.current_stage:
            text.append("\n")
            text.append("STAGE: ", style="bold cyan")
            text.append(f"{self.state.current_stage}", style="bold yellow")

            # Show stage elapsed time from heartbeat
            if self.state.heartbeat_stage_elapsed > 0:
                elapsed = self.state.heartbeat_stage_elapsed
                if elapsed >= 60:
                    mins = int(elapsed // 60)
                    secs = int(elapsed % 60)
                    text.append(f" ({mins}m {secs}s)", style="dim cyan")
                else:
                    text.append(f" ({int(elapsed)}s)", style="dim cyan")

            # Show LLM calls in current stage
            if self.state.heartbeat_llm_calls > 0:
                text.append(f"  [{self.state.heartbeat_llm_calls} LLM calls]", style="dim")
        elif self.state.phase in ('evaluate', 'awaiting_evaluation', 'fix', 'awaiting_fix'):
            # No active stage but in Claude phase - make it clear
            text.append("\n")
            text.append("STAGE: ", style="bold cyan")
            text.append("Analysis Complete - Claude Evaluating", style="bold magenta")

        # Show heartbeat status (activity indicator for local LLM)
        text.append("\n")
        if self.state.heartbeat_age_seconds is not None:
            age = self.state.heartbeat_age_seconds
            text.append("LLM HEARTBEAT: ", style="bold cyan")
            if age < 5:
                text.append("●", style="bold green")
                text.append(f" {age:.0f}s ago (active)", style="green")
            elif age < 30:
                text.append("●", style="bold yellow")
                text.append(f" {age:.0f}s ago", style="yellow")
            elif age < 60:
                text.append("○", style="yellow")
                text.append(f" {age:.0f}s ago (idle)", style="yellow")
            elif age < 300:
                mins = int(age // 60)
                text.append("○", style="dim")
                # Don't show as error - might be between stages or Claude is working
                if self.state.phase in ('awaiting_evaluation', 'evaluate', 'awaiting_fix', 'fix'):
                    text.append(f" {mins}m ago (analysis complete)", style="dim green")
                else:
                    text.append(f" {mins}m ago (inactive)", style="dim")
            else:
                mins = int(age // 60)
                text.append("○", style="dim")
                text.append(f" {mins}m ago (inactive)", style="dim")

            # Show total analysis time if available
            if self.state.heartbeat_total_elapsed > 0:
                total = self.state.heartbeat_total_elapsed
                text.append("  │  ", style="dim")
                text.append("TOTAL TIME: ", style="bold cyan")
                if total >= 3600:
                    hours = int(total // 3600)
                    mins = int((total % 3600) // 60)
                    text.append(f"{hours}h {mins}m", style="white")
                elif total >= 60:
                    mins = int(total // 60)
                    secs = int(total % 60)
                    text.append(f"{mins}m {secs}s", style="white")
                else:
                    text.append(f"{int(total)}s", style="white")
        else:
            text.append("HEARTBEAT: ", style="bold cyan")
            text.append("○", style="dim")
            text.append(" no data", style="dim")

        # Show analysis process status
        text.append("  │  ", style="dim")
        text.append("ANALYSIS: ", style="bold cyan")
        if self.state.analysis_running:
            text.append("●", style="bold green")
            text.append(f" running", style="green")
            if self.state.analysis_pid:
                text.append(f" (PID {self.state.analysis_pid})", style="dim")
        else:
            text.append("○", style="dim")
            text.append(" not running", style="dim")

        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class ScorePanel(Static):
    """Panel showing all scores with progress bars."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()
        threshold = self.state.threshold

        # Prominent total score at top
        text.append("═" * 56, style="dim cyan")
        text.append("\n")
        text.append("  TOTAL SCORE:  ", style="bold white")
        if self.state.overall_score is not None:
            overall = self.state.overall_score
            # Color based on threshold comparison
            if overall >= threshold:
                score_style = "bold green"
            elif overall >= threshold - 1.0:
                score_style = "bold yellow"
            else:
                score_style = "bold red"
            text.append(f"{overall:.2f}", style=score_style)
            text.append(" / 10", style="white")
            text.append(f"   [Threshold: {threshold:.1f}]", style="dim cyan")
        else:
            text.append("--", style="dim")
            text.append(" / 10", style="dim")
            text.append(f"   [Threshold: {threshold:.1f}]", style="dim cyan")
        text.append("\n")
        text.append("═" * 56, style="dim cyan")
        text.append("\n\n")

        scores = [
            ("Structure", self.state.structure_score),
            ("Characters", self.state.characters_score),
            ("Profiles", self.state.profiles_score),
            ("Summaries", self.state.summaries_score),
            ("Pronunciation", self.state.pronunciation_score),
            ("Presentation", self.state.presentation_score),
        ]

        for name, value in scores:
            # Pad name to fixed width
            padded_name = f"{name}:".ljust(16)
            text.append(padded_name, style="white")

            if value is None:
                text.append("  --/10  ", style="dim")
                text.append("░" * 30, style="dim")
            else:
                # Score value
                score_str = f"{value:4.1f}/10  "
                passing = value >= threshold
                text.append(score_str, style="green" if passing else "red")

                # Progress bar
                filled = int((value / 10.0) * 30)
                empty = 30 - filled
                bar_style = "green" if passing else "yellow" if value >= 6 else "red"
                text.append("█" * filled, style=bar_style)
                text.append("░" * empty, style="dim")

                # Pass/fail indicator
                if passing:
                    text.append(" ✓", style="green")
                else:
                    text.append(" ✗", style="red")

            text.append("\n")

        # Separator
        text.append("─" * 56, style="dim")
        text.append("\n")

        # Overall score
        text.append("OVERALL:".ljust(16), style="bold white")
        if self.state.overall_score is None:
            text.append("  --/10  ", style="dim")
            text.append(" " * 20, style="dim")
        else:
            overall = self.state.overall_score
            passing = overall >= threshold
            text.append(f"{overall:4.1f}/10  ", style="bold green" if passing else "bold red")
            text.append(" " * 13, style="dim")

        text.append(f"Threshold: {threshold:.1f}", style="cyan")

        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class OverallProgress(Static):
    """Overall progress bar showing texts completed."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()

        completed = self.state.completed_texts
        total = self.state.total_texts

        text.append("PROGRESS: ", style="bold cyan")
        text.append(f"{completed}/{total} texts complete  ", style="white")

        if total > 0:
            pct = completed / total
            filled = int(pct * 30)
            empty = 30 - filled
            text.append("█" * filled, style="green")
            text.append("░" * empty, style="dim")
            text.append(f" {pct * 100:.0f}%", style="white")
        else:
            text.append("░" * 30, style="dim")
            text.append(" 0%", style="white")

        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class IssuesPanel(Static):
    """Panel showing issues from evaluation."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()

        issues = self.state.issues
        text.append(f"ISSUES ({len(issues)})\n", style="bold white")

        if not issues:
            text.append("  No issues found", style="dim")
            return text

        severity_styles = {
            'CRITICAL': 'bold red',
            'HIGH': 'red',
            'MEDIUM': 'yellow',
            'LOW': 'dim white',
        }

        # Show up to 10 issues
        for issue in issues[:10]:
            style = severity_styles.get(issue.severity, 'white')
            text.append(f"{issue.severity:8} ", style=style)
            text.append("│ ", style="dim")
            # Truncate long descriptions
            desc = issue.description
            if len(desc) > 55:
                desc = desc[:52] + "..."
            text.append(desc, style="white")
            text.append("\n")

        if len(issues) > 10:
            text.append(f"  ... and {len(issues) - 10} more", style="dim")

        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class CommitsPanel(Static):
    """Panel showing recent git commits."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()

        text.append("RECENT COMMITS\n", style="bold white")

        if not self.state.commits:
            text.append("  No commits found", style="dim")
            return text

        for commit in self.state.commits:
            text.append(commit.hash, style="yellow")
            text.append(" │ ", style="dim")
            # Show timestamp if available
            if commit.timestamp:
                # Pad timestamp to fixed width for alignment
                ts = commit.timestamp[:15].ljust(15)
                text.append(ts, style="dim cyan")
                text.append(" │ ", style="dim")
            # Truncate long messages
            msg = commit.message
            max_msg_len = 60 if commit.timestamp else 80
            if len(msg) > max_msg_len:
                msg = msg[:max_msg_len - 3] + "..."
            text.append(msg, style="white")
            text.append("\n")

        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class StderrPanel(Static):
    """Panel showing recent stderr output from analysis."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()

        text.append("RECENT OUTPUT\n", style="bold white")

        if not self.state.recent_stderr:
            text.append("  No recent output", style="dim")
            if self.state.analysis_running:
                text.append("\n  (analysis running, waiting for output...)", style="dim cyan")
            return text

        for line in self.state.recent_stderr:
            # Color code based on content
            line_lower = line.lower()
            if 'error' in line_lower or 'fail' in line_lower:
                style = "red"
            elif 'warning' in line_lower:
                style = "yellow"
            elif 'low confidence' in line_lower:
                style = "yellow"
            else:
                style = "dim white"

            # Truncate long lines
            if len(line) > 90:
                line = line[:87] + "..."
            text.append(f"  {line}\n", style=style)

        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class OllamaActivityPanel(Static):
    """Panel showing local LLM (Ollama) activity during analysis."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()

        text.append("LOCAL LLM ACTIVITY\n", style="bold white")

        # Only show when we have an active analysis stage
        if not self.state.current_stage:
            # No active stage - determine why
            if self.state.phase in ('awaiting_evaluation', 'evaluate', 'awaiting_fix', 'fix'):
                # Claude is working
                text.append("  Analysis complete - idle\n", style="dim green")
                text.append("  Claude is now evaluating (see Claude Activity below)", style="bold magenta")
            elif self.state.phase == 'complete':
                text.append("  Analysis complete - all done!", style="bold green")
            else:
                text.append("  No active analysis", style="dim")
            return text

        # Stage progress with item counts
        text.append(f"  Stage: ", style="cyan")
        text.append(f"{self.state.current_stage}", style="bold yellow")

        # Item progress (e.g., "5/9 chapters")
        if self.state.ollama_items_total:
            pct = (self.state.ollama_items_processed / self.state.ollama_items_total) * 100
            text.append(f"  [{self.state.ollama_items_processed}/{self.state.ollama_items_total}]", style="white")
            text.append(f" {pct:.0f}%", style="cyan")
        elif self.state.ollama_items_processed > 0:
            text.append(f"  [{self.state.ollama_items_processed} processed]", style="white")

        text.append("\n")

        # Progress bar (if we have total)
        if self.state.ollama_items_total and self.state.ollama_items_total > 0:
            pct = self.state.ollama_items_processed / self.state.ollama_items_total
            filled = int(pct * 40)
            empty = 40 - filled
            text.append("  ")
            text.append("█" * filled, style="green")
            text.append("░" * empty, style="dim")
            text.append("\n")

        # LLM metrics
        text.append("\n")
        text.append("  LLM Calls: ", style="cyan")
        text.append(f"{self.state.ollama_llm_calls}", style="white")
        text.append("  │  ", style="dim")

        # Token throughput
        text.append("Tokens: ", style="cyan")
        text.append(f"{format_tokens(self.state.input_tokens)} in", style="white")
        text.append(" / ", style="dim")
        text.append(f"{format_tokens(self.state.output_tokens)} out", style="white")
        text.append("\n")

        # Latency metrics
        text.append("  Last Latency: ", style="cyan")
        if self.state.ollama_last_latency_ms > 0:
            # Format latency nicely
            latency = self.state.ollama_last_latency_ms
            if latency >= 1000:
                text.append(f"{latency/1000:.1f}s", style="white")
            else:
                text.append(f"{latency:.0f}ms", style="white")
        else:
            text.append("--", style="dim")

        text.append("  │  ", style="dim")

        text.append("Avg Latency: ", style="cyan")
        if self.state.ollama_avg_latency_ms > 0:
            avg_latency = self.state.ollama_avg_latency_ms
            if avg_latency >= 1000:
                text.append(f"{avg_latency/1000:.1f}s", style="white")
            else:
                text.append(f"{avg_latency:.0f}ms", style="white")
        else:
            text.append("--", style="dim")

        # Model name
        if self.state.model:
            text.append("\n")
            text.append("  Model: ", style="cyan")
            model_name = self.state.model.split('/')[-1] if self.state.model else "(none)"
            if len(model_name) > 40:
                model_name = model_name[:37] + "..."
            text.append(model_name, style="white")

        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class CompetitiveConsensusPanel(Static):
    """Panel showing competitive consensus mode and live voting."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()

        text.append("COMPETITIVE CONSENSUS\n", style="bold white")

        # Mode indicator
        mode = self.state.competitive_mode
        if mode == "multi":
            text.append("  Mode: ", style="cyan")
            text.append("MULTI-MODEL", style="bold green")
            text.append(" (diverse models voting)\n", style="dim")
        elif mode == "single":
            text.append("  Mode: ", style="cyan")
            text.append("SINGLE-MODEL", style="bold yellow")
            text.append(" (same model, 3 temps)\n", style="dim")
        else:
            text.append("  Mode: ", style="cyan")
            text.append("DISABLED", style="dim")
            text.append("\n")
            return text

        # Stages enabled
        stages = self.state.competitive_stages
        if stages:
            text.append("  Stages: ", style="cyan")
            stage_strs = []
            for stage in stages:
                if stage == "characters":
                    stage_strs.append("👥 characters")
                elif stage == "structure":
                    stage_strs.append("📖 structure")
                elif stage == "summaries":
                    stage_strs.append("📝 summaries")
                else:
                    stage_strs.append(stage)
            text.append(", ".join(stage_strs), style="white")
            text.append("\n")

        # Models (for multi mode)
        models = self.state.competitive_models
        if models and mode == "multi":
            text.append("  Models: ", style="cyan")
            for i, model_spec in enumerate(models):
                if i > 0:
                    text.append(", ", style="dim")
                # Parse model:temp format
                parts = model_spec.split(":")
                model_name = ":".join(parts[:-1]) if len(parts) > 1 else parts[0]
                temp = parts[-1] if len(parts) > 1 else "0.7"
                # Shorten model name
                if len(model_name) > 15:
                    model_name = model_name[:12] + "..."
                text.append(f"{model_name}", style="white")
                text.append(f"@{temp}", style="dim cyan")
            text.append("\n")

        # Recent votes
        votes = self.state.recent_votes
        if votes:
            text.append("\n")
            text.append("  Recent Votes:\n", style="bold cyan")
            for vote in votes[-5:]:  # Show last 5
                vote_type = vote.get('vote_type', '?')
                subject = vote.get('subject', '?')
                outcome = vote.get('outcome', '?')
                yes_count = vote.get('yes_count', 0)
                vote_count = vote.get('vote_count', 0)

                # Type icon
                if vote_type == "alias":
                    icon = "🔗"
                elif vote_type == "boundary":
                    icon = "📍"
                elif vote_type == "summary_merge":
                    icon = "📝"
                else:
                    icon = "🗳️"

                # Outcome style
                if outcome == "accepted":
                    outcome_style = "green"
                    outcome_icon = "✓"
                elif outcome == "rejected":
                    outcome_style = "red"
                    outcome_icon = "✗"
                else:
                    outcome_style = "yellow"
                    outcome_icon = "~"

                text.append(f"    {icon} ", style="dim")
                # Truncate subject
                subj = subject[:30] + "..." if len(subject) > 30 else subject
                text.append(f"{subj}", style="white")
                text.append(f" [{yes_count}/{vote_count}] ", style="dim")
                text.append(f"{outcome_icon}", style=outcome_style)
                text.append("\n")
        elif self.state.analysis_running:
            text.append("\n")
            text.append("  Votes: ", style="cyan")
            text.append("waiting for voting...", style="dim")
            text.append("\n")

        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class ClaudeActivityPanel(Static):
    """Panel showing Claude's recent activity (tool calls, messages)."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()

        # Show header with phase indicator
        if self.state.phase in ('awaiting_evaluation', 'evaluate', 'awaiting_fix', 'fix'):
            text.append("CLAUDE ACTIVITY [ACTIVE - ", style="bold white")
            text.append(self.state.phase.upper(), style="bold magenta")
            text.append("]\n", style="bold white")
        else:
            text.append("CLAUDE ACTIVITY\n", style="bold white")

        activities = self.state.claude_activities
        if not activities:
            text.append("  No recent activity", style="dim")
            if self.state.phase in ('awaiting_analysis', 'running_analysis'):
                text.append("\n  (Local LLMs running - see Local LLM Activity above)", style="dim cyan")
            return text

        # Show tool icons for each tool type
        tool_icons = {
            'Read': '📖',
            'Edit': '✏️',
            'Write': '📝',
            'Bash': '💻',
            'Grep': '🔍',
            'Glob': '📂',
            'Task': '🤖',
            'TodoWrite': '✅',
        }

        for activity in activities[-12:]:  # Show last 12 activities
            icon = tool_icons.get(activity.tool_name, '🔧')
            text.append(f"  {icon} ", style="dim")
            # Show timestamp if available
            if activity.timestamp:
                text.append(f"{activity.timestamp} ", style="dim cyan")
            text.append(f"{activity.tool_name:12}", style="cyan")
            text.append("│ ", style="dim")
            # Truncate long descriptions (shorter if timestamp shown)
            desc = activity.description
            max_desc_len = 55 if activity.timestamp else 70
            if len(desc) > max_desc_len:
                desc = desc[:max_desc_len - 3] + "..."
            text.append(desc, style="white")
            text.append("\n")

        # Show last message snippet if available
        if self.state.claude_last_message:
            text.append("\n")
            text.append("  Last output: ", style="dim")
            msg = self.state.claude_last_message.replace('\n', ' ')
            if len(msg) > 500:
                msg = msg[:497] + "..."
            text.append(msg, style="italic white")

        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class ClaudeThinkingPanel(Static):
    """Panel showing Claude's reasoning and explanations."""

    def __init__(self, state: OracleState, expanded: bool = False):
        super().__init__()
        self.state = state
        self.expanded = expanded

    def render(self) -> Text:
        text = Text()

        # Header shows mode
        if self.expanded:
            text.append("CLAUDE THINKING [EXPANDED - Press 't' to collapse]\n", style="bold white")
        else:
            text.append("CLAUDE THINKING [Press 't' to expand, 'x' to export]\n", style="bold white")

        thinking_texts = self.state.thinking_text
        if not thinking_texts:
            text.append("  No reasoning captured yet", style="dim")
            if self.state.phase in ('awaiting_analysis', 'running_analysis'):
                text.append("\n  (Local LLMs running - Claude reasoning appears during evaluate/fix)", style="dim cyan")
            return text

        # In expanded mode, show ALL blocks without truncation
        # In compact mode, show last 3 blocks with truncation
        if self.expanded:
            blocks_to_show = thinking_texts  # Show all
            max_chars_per_block = None  # No truncation
            blocks_label = f"Showing all {len(thinking_texts)} blocks"
        else:
            blocks_to_show = thinking_texts[-3:]  # Show last 3
            max_chars_per_block = 800  # Truncate in compact mode
            blocks_label = f"Showing last 3 of {len(thinking_texts)} blocks"

        text.append(f"  [{blocks_label}]\n", style="dim cyan")

        # Show thinking blocks with numbering
        for i, thinking in enumerate(blocks_to_show, 1):
            # Add separator between blocks
            if i > 1:
                text.append("  ─────────────────────────────────────────\n", style="dim")

            # Show block number (relative to total if not showing all)
            if self.expanded or len(thinking_texts) <= 3:
                text.append(f"  [{i}] ", style="dim cyan")
            else:
                # Show actual position in full list
                actual_index = len(thinking_texts) - len(blocks_to_show) + i
                text.append(f"  [{actual_index}/{len(thinking_texts)}] ", style="dim cyan")

            # Word wrap and display the thinking text
            # Clean up the text - remove excessive whitespace
            cleaned = ' '.join(thinking.split())

            # Truncate in compact mode
            truncated = False
            if max_chars_per_block and len(cleaned) > max_chars_per_block:
                cleaned = cleaned[:max_chars_per_block]
                truncated = True

            # Display with word wrapping by breaking into lines
            words = cleaned.split()
            current_line = ""
            line_limit = 100 if self.expanded else 80

            for word in words:
                if len(current_line) + len(word) + 1 <= line_limit:
                    current_line += (" " if current_line else "") + word
                else:
                    if current_line:
                        text.append(current_line + "\n", style="white")
                        text.append("      ", style="")  # Indent continuation
                    current_line = word

            if current_line:
                text.append(current_line, style="white")
                if truncated:
                    text.append("... [truncated]", style="dim yellow")
                text.append("\n")

        return text

    def update_state(self, state: OracleState, expanded: bool = None):
        self.state = state
        if expanded is not None:
            self.expanded = expanded
        self.refresh()


class FooterInfo(Static):
    """Footer showing last updated time and polling interval."""

    def __init__(self, state: OracleState, polling_interval: float = 2.0):
        super().__init__()
        self.state = state
        self.polling_interval = polling_interval

    def render(self) -> Text:
        text = Text()
        timestamp = self.state.last_updated.strftime("%Y-%m-%d %H:%M:%S")
        text.append(f"Last updated: {timestamp}", style="dim")
        text.append("  │  ", style="dim")
        text.append(f"Polling: {self.polling_interval:.0f}s", style="dim")
        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class OracleMonitorApp(App):
    """Main Oracle Loop Monitor application."""

    CSS = """
    Screen {
        background: $surface;
    }

    StatusBar {
        height: auto;
        max-height: 8;
        border: solid $primary;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    ScorePanel {
        height: 12;
        border: solid $primary;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    OverallProgress {
        height: 3;
        border: solid $primary;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    OllamaActivityPanel {
        height: auto;
        max-height: 9;
        border: solid $success;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    StderrPanel {
        height: auto;
        max-height: 10;
        border: solid $warning;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    IssuesPanel {
        height: auto;
        max-height: 6;
        border: solid $primary;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    CommitsPanel {
        height: auto;
        max-height: 6;
        border: solid $primary;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    CompetitiveConsensusPanel {
        height: auto;
        max-height: 12;
        border: solid $success;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    ClaudeActivityPanel {
        height: auto;
        max-height: 10;
        border: solid $accent;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    ClaudeThinkingPanel {
        height: auto;
        max-height: 15;
        border: solid $warning;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    ClaudeThinkingPanel.expanded {
        max-height: 40;
    }

    FooterInfo {
        height: 1;
        padding: 0 1;
    }

    #user-notes-input {
        margin: 0 0 1 0;
        border: solid $warning;
    }

    VerticalScroll {
        height: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("p", "toggle_pause", "Pause", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("n", "focus_notes", "Notes", show=True),
        Binding("t", "toggle_thinking", "Thinking", show=True),
        Binding("x", "export_thinking", "Export", show=True),
    ]

    paused = reactive(False)
    thinking_expanded = reactive(False)

    def __init__(self, base_dir: Path = None, polling_interval: float = 2.0):
        super().__init__()
        self.base_dir = base_dir or Path.cwd()
        self.polling_interval = polling_interval
        self.parser = StateParser(self.base_dir)
        self.state = self.parser.get_state()
        self.title = "Oracle Loop Monitor"
        self.notes_file = self.base_dir / "state" / "USER_NOTES.md"

    def compose(self) -> ComposeResult:
        yield Header()

        with VerticalScroll():
            yield StatusBar(self.state)
            yield ScorePanel(self.state)
            yield OverallProgress(self.state)
            yield CompetitiveConsensusPanel(self.state)
            yield OllamaActivityPanel(self.state)
            yield StderrPanel(self.state)
            yield ClaudeActivityPanel(self.state)
            yield ClaudeThinkingPanel(self.state, expanded=self.thinking_expanded)
            yield IssuesPanel(self.state)
            yield CommitsPanel(self.state)
            yield Input(placeholder="Send note to Claude (press Enter)...", id="user-notes-input")
            yield FooterInfo(self.state, self.polling_interval)

        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user notes submission."""
        if event.input.id == "user-notes-input":
            content = event.value.strip()
            if content:
                self._save_notes(content)
                event.input.value = ""
                self.notify(f"Note sent to Claude", title="Saved")

    def _save_notes(self, content: str) -> None:
        """Save notes to USER_NOTES.md."""
        try:
            notes_content = f"""# User Notes for Oracle Loop

---

## Current Notes

{content}
"""
            self.notes_file.write_text(notes_content)
        except Exception:
            pass

    def on_mount(self):
        """Start polling when mounted."""
        self.set_interval(self.polling_interval, self._poll_state)

    def _poll_state(self):
        """Poll for state updates."""
        if self.paused:
            return

        self.state = self.parser.get_state()
        self._update_widgets()

    def _update_widgets(self):
        """Update all widgets with new state."""
        try:
            self.query_one(StatusBar).update_state(self.state)
            self.query_one(ScorePanel).update_state(self.state)
            self.query_one(OverallProgress).update_state(self.state)
            self.query_one(CompetitiveConsensusPanel).update_state(self.state)
            self.query_one(OllamaActivityPanel).update_state(self.state)
            self.query_one(StderrPanel).update_state(self.state)
            self.query_one(ClaudeActivityPanel).update_state(self.state)
            self.query_one(ClaudeThinkingPanel).update_state(self.state, expanded=self.thinking_expanded)
            self.query_one(IssuesPanel).update_state(self.state)
            self.query_one(CommitsPanel).update_state(self.state)
            self.query_one(FooterInfo).update_state(self.state)
        except Exception:
            # Widget may not be ready yet
            pass

    def action_toggle_pause(self):
        """Toggle pause state."""
        self.paused = not self.paused
        if self.paused:
            self.notify("Polling paused", severity="warning")
        else:
            self.notify("Polling resumed")
            self._poll_state()

    def action_refresh(self):
        """Manual refresh."""
        self._poll_state()
        self.notify("Refreshed")

    def action_focus_notes(self):
        """Focus the notes input."""
        try:
            notes_input = self.query_one("#user-notes-input", Input)
            notes_input.focus()
        except Exception:
            pass

    def action_toggle_thinking(self):
        """Toggle thinking panel expanded/collapsed."""
        self.thinking_expanded = not self.thinking_expanded

        # Update CSS class
        try:
            thinking_panel = self.query_one(ClaudeThinkingPanel)
            if self.thinking_expanded:
                thinking_panel.add_class("expanded")
                self.notify("Thinking panel expanded", title="View Mode")
            else:
                thinking_panel.remove_class("expanded")
                self.notify("Thinking panel collapsed", title="View Mode")

            # Update the panel with new expanded state
            thinking_panel.update_state(self.state, expanded=self.thinking_expanded)
        except Exception:
            pass

    def action_export_thinking(self):
        """Export full thinking text to file."""
        if not self.state.thinking_text:
            self.notify("No thinking text to export", severity="warning")
            return

        export_file = self.base_dir / "state" / "CLAUDE_THINKING_EXPORT.txt"

        try:
            # Create export with timestamp and all thinking blocks
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            content_parts = [
                f"# Claude Thinking Export",
                f"# Exported: {timestamp}",
                f"# Text: {self.state.text_name}",
                f"# Attempt: {self.state.attempt}",
                f"# Total blocks: {len(self.state.thinking_text)}",
                "",
                "=" * 80,
                "",
            ]

            for i, thinking in enumerate(self.state.thinking_text, 1):
                content_parts.append(f"## Block {i}/{len(self.state.thinking_text)}")
                content_parts.append("")
                content_parts.append(thinking)
                content_parts.append("")
                content_parts.append("-" * 80)
                content_parts.append("")

            export_file.write_text("\n".join(content_parts), encoding="utf-8")
            self.notify(f"Exported to {export_file.name}", title="Export Complete")
        except Exception as e:
            self.notify(f"Export failed: {e}", severity="error")


def run_oracle_monitor(base_dir: Path = None, polling_interval: float = 2.0):
    """Launch the Oracle Loop Monitor TUI."""
    app = OracleMonitorApp(base_dir=base_dir, polling_interval=polling_interval)
    app.run()


def main():
    """CLI entry point for oracle-monitor command."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Monitor oracle loop progress in real-time"
    )
    parser.add_argument(
        "--dir", "-d",
        type=Path,
        default=Path.cwd(),
        help="Base directory containing EVALUATION_STATE.md, manifest.json, logs/"
    )
    parser.add_argument(
        "--interval", "-i",
        type=float,
        default=1.0,
        help="Polling interval in seconds (default: 1.0)"
    )

    args = parser.parse_args()
    # Resolve to absolute path before Textual changes working directory
    base_dir = args.dir.resolve()
    run_oracle_monitor(base_dir=base_dir, polling_interval=args.interval)


if __name__ == "__main__":
    main()
