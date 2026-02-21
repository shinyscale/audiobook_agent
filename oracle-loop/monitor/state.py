"""
Oracle Monitor state models and parsing.

Data models (Score, Issue, Commit, ClaudeActivity, OracleState),
StateParser for reading all data sources, and format_tokens utility.
"""

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


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

    # Ollama service heartbeat (from journalctl)
    ollama_last_request_age: Optional[float] = None  # Seconds since last API completion
    ollama_last_request_duration: Optional[float] = None  # Duration of last request in seconds

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

    # Experiment framework
    experiment_mode: bool = False  # True when experiment-runner.sh is active
    experiment_running: bool = False  # Is experiment-runner.sh process running
    active_experiment_id: str = ""
    active_experiment_desc: str = ""
    active_experiment_status: str = ""  # pending, in_progress, passed, failed_*
    experiment_phase: str = ""  # "screening", "validation", "regression"
    experiment_book_index: int = 0  # Current book index in phase
    experiment_books_in_phase: int = 0  # Total books in current phase
    experiment_current_book: str = ""  # Current book being tested
    screening_threshold: float = 7.0
    validation_threshold: float = 8.0
    category_regression_tolerance: float = 0.5

    # Baseline comparison (from checkpoints.json category_scores)
    baseline_category_scores: dict = field(default_factory=dict)  # {category: score}
    category_deltas: dict = field(default_factory=dict)  # {category: delta_from_baseline}

    # Experiment results summary
    experiment_results: dict = field(default_factory=dict)  # {book: {status, overall, ...}}

    # Identity graph data (from identity_graph.json)
    identity_graph: Optional[dict] = None

    # Diagnostic matrix data (from diagnostic_matrix.json)
    diagnostic_matrix: Optional[dict] = None  # Full matrix data
    diagnostic_timestamp: str = ""  # When diagnostic was last run
    diagnostic_running: bool = False  # Is batch-diagnostic.sh running


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
            Path("/home/zacharymandrews/Tools/audiobook_agent/oracle-loop/output/VOTES.json"),
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

            # Return all votes
            votes = data.get('votes', [])
            return votes
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

    def check_experiment_running(self) -> bool:
        """Check if experiment-runner.sh is currently running."""
        try:
            # Use pgrep with full match to avoid false positives from grep/pgrep commands
            # that contain "experiment-runner.sh" as a search pattern
            result = subprocess.run(
                ['pgrep', '-f', r'(^|/)experiment-runner\.sh(\s|$)'],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def parse_experiments(self) -> dict:
        """Parse experiments.json for experiment framework state."""
        possible_paths = [
            self.base_dir / "state" / "experiments.json",
            self.base_dir / "experiments.json",
            self.base_dir.parent / "state" / "experiments.json",
        ]
        experiments_file = None
        for path in possible_paths:
            if path.exists():
                experiments_file = path
                break

        if not experiments_file:
            return {}

        try:
            with open(experiments_file) as f:
                data = json.load(f)

            # Find active experiment (in_progress or the first pending)
            active_exp = None
            baseline_exp = None
            for exp in data.get('experiments', []):
                status = exp.get('status', '')
                if status == 'in_progress':
                    active_exp = exp
                elif status == 'baseline':
                    baseline_exp = exp
                elif status == 'pending' and active_exp is None:
                    # First pending experiment (might be next to run)
                    active_exp = exp

            # Get book sets
            book_sets = data.get('book_sets', {})

            # Determine current phase based on results in active experiment
            experiment_phase = ""
            book_index = 0
            books_in_phase = 0
            current_book = ""

            if active_exp:
                results = active_exp.get('results', {})
                screening_books = book_sets.get('screening', [])
                validation_books = book_sets.get('validation', [])
                regression_books = book_sets.get('regression', [])

                # Check which phase we're in based on results
                screening_complete = all(b in results for b in screening_books)
                validation_complete = all(b in results for b in validation_books)

                if not screening_complete:
                    experiment_phase = "screening"
                    books_in_phase = len(screening_books)
                    book_index = sum(1 for b in screening_books if b in results)
                    # Find current book (first without result)
                    for b in screening_books:
                        if b not in results:
                            current_book = b
                            break
                elif not validation_complete:
                    experiment_phase = "validation"
                    books_in_phase = len(validation_books)
                    book_index = sum(1 for b in validation_books if b in results)
                    for b in validation_books:
                        if b not in results:
                            current_book = b
                            break
                else:
                    experiment_phase = "regression"
                    books_in_phase = len(regression_books)
                    book_index = sum(1 for b in regression_books if b in results)
                    for b in regression_books:
                        if b not in results:
                            current_book = b
                            break

            return {
                'experiment_mode': active_exp is not None,
                'active_experiment': active_exp,
                'active_experiment_id': active_exp.get('id', '') if active_exp else '',
                'active_experiment_desc': active_exp.get('description', '') if active_exp else '',
                'active_experiment_status': active_exp.get('status', '') if active_exp else '',
                'experiment_results': active_exp.get('results', {}) if active_exp else {},
                'baseline_experiment': baseline_exp,
                'book_sets': book_sets,
                'experiment_phase': experiment_phase,
                'experiment_book_index': book_index,
                'experiment_books_in_phase': books_in_phase,
                'experiment_current_book': current_book,
                'screening_threshold': data.get('screening_threshold', 7.0),
                'validation_threshold': data.get('validation_threshold', 8.0),
                'category_regression_tolerance': data.get('category_regression_tolerance', 0.5),
            }
        except (json.JSONDecodeError, IOError):
            return {}

    def parse_baseline_category_scores(self, text_name: str) -> dict:
        """Get baseline category scores for a text from checkpoints.json."""
        possible_paths = [
            self.base_dir / "state" / "checkpoints.json",
            self.base_dir / "checkpoints.json",
            self.base_dir.parent / "state" / "checkpoints.json",
        ]
        checkpoints_file = None
        for path in possible_paths:
            if path.exists():
                checkpoints_file = path
                break

        if not checkpoints_file:
            return {}

        try:
            with open(checkpoints_file) as f:
                data = json.load(f)

            baseline = data.get('known_good_baseline', {}).get(text_name, {})
            return baseline.get('category_scores', {})
        except (json.JSONDecodeError, IOError):
            return {}

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

    def parse_ollama_service_logs(self) -> dict:
        """Parse Ollama service logs for last API completion time.

        Returns dict with:
            - ollama_last_request_age: seconds since last completion
            - ollama_last_request_duration: duration of last request in seconds
        """
        try:
            from datetime import datetime
            import time
            import re

            result = subprocess.run(
                ['journalctl', '-u', 'ollama', '-n', '1', '--no-pager'],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode != 0 or not result.stdout.strip():
                return {}

            # Parse the log line: "Jan 26 21:20:30 ... [GIN] 2026/01/26 - 21:20:30 | 200 | 8.900933032s | ... | POST     "/api/chat""
            log_line = result.stdout.strip()

            # Extract timestamp from GIN log portion: "2026/01/26 - 21:20:30"
            gin_match = re.search(r'\[GIN\]\s+(\d+/\d+/\d+)\s+-\s+([\d:]+)', log_line)
            if not gin_match:
                return {}

            date_str = gin_match.group(1)  # 2026/01/26
            time_str = gin_match.group(2)  # 21:20:30

            # Parse to datetime
            log_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
            age_seconds = (datetime.now() - log_datetime).total_seconds()

            # Extract duration from: "| 200 | 8.900933032s |"
            duration_s = None
            duration_match = re.search(r'\|\s*200\s*\|\s*([\d.]+(?:m|s|ms))', log_line)
            if duration_match:
                duration_str = duration_match.group(1)
                # Handle different time units
                if duration_str.endswith('ms'):
                    duration_s = float(duration_str[:-2]) / 1000
                elif duration_str.endswith('s'):
                    duration_s = float(duration_str[:-1])
                elif 'm' in duration_str:
                    # Format like "4m31s"
                    parts = duration_str.replace('m', ' ').replace('s', '').split()
                    if len(parts) == 2:
                        duration_s = int(parts[0]) * 60 + float(parts[1])
                    else:
                        duration_s = float(parts[0]) * 60

            return {
                'ollama_last_request_age': age_seconds,
                'ollama_last_request_duration': duration_s,
            }

        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError, Exception):
            return {}

    def parse_diagnostic_matrix(self) -> Optional[dict]:
        """Parse state/diagnostic_matrix.json if it exists."""
        possible_paths = [
            self.base_dir / "state" / "diagnostic_matrix.json",
            self.base_dir.parent / "state" / "diagnostic_matrix.json",
        ]
        for path in possible_paths:
            if path.exists():
                try:
                    with open(path) as f:
                        return json.load(f)
                except (json.JSONDecodeError, IOError):
                    return None
        return None

    def check_diagnostic_running(self) -> bool:
        """Check if batch-diagnostic.sh is currently running."""
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'batch-diagnostic.sh'],
                capture_output=True, text=True, timeout=2
            )
            return result.returncode == 0 and result.stdout.strip() != ''
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

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

        # Check if experiment-runner is running
        state.experiment_running = self.check_experiment_running()

        # Parse experiment framework state
        exp_data = self.parse_experiments()
        if exp_data:
            state.experiment_mode = exp_data.get('experiment_mode', False) or state.experiment_running
            state.active_experiment_id = exp_data.get('active_experiment_id', '')
            state.active_experiment_desc = exp_data.get('active_experiment_desc', '')
            state.active_experiment_status = exp_data.get('active_experiment_status', '')
            state.experiment_phase = exp_data.get('experiment_phase', '')
            state.experiment_book_index = exp_data.get('experiment_book_index', 0)
            state.experiment_books_in_phase = exp_data.get('experiment_books_in_phase', 0)
            state.experiment_current_book = exp_data.get('experiment_current_book', '')
            state.screening_threshold = exp_data.get('screening_threshold', 7.0)
            state.validation_threshold = exp_data.get('validation_threshold', 8.0)
            state.category_regression_tolerance = exp_data.get('category_regression_tolerance', 0.5)
            state.experiment_results = exp_data.get('experiment_results', {})

        # Get baseline category scores for current text (for delta comparison)
        if state.text_name:
            state.baseline_category_scores = self.parse_baseline_category_scores(state.text_name)

            # Calculate deltas from baseline
            if state.baseline_category_scores:
                score_map = {
                    'structure': state.structure_score,
                    'characters': state.characters_score,
                    'profiles': state.profiles_score,
                    'summaries': state.summaries_score,
                    'pronunciation': state.pronunciation_score,
                    'presentation': state.presentation_score,
                }
                for cat, current in score_map.items():
                    baseline = state.baseline_category_scores.get(cat)
                    if current is not None and baseline is not None:
                        state.category_deltas[cat] = current - baseline

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

        # Parse Ollama service logs for additional heartbeat info
        ollama_logs = self.parse_ollama_service_logs()
        if ollama_logs:
            state.ollama_last_request_age = ollama_logs.get('ollama_last_request_age')
            state.ollama_last_request_duration = ollama_logs.get('ollama_last_request_duration')


        # Load identity graph data if available
        if state.text_name:
            graph_paths = [
                self.base_dir / "output" / state.text_name / "identity_graph.json",
                Path.home() / "Tools" / "audiobook_agent" / "oracle-loop" / "output" / state.text_name / "identity_graph.json",
            ]
            for gp in graph_paths:
                if gp.exists():
                    try:
                        with open(gp) as f:
                            state.identity_graph = json.load(f)
                    except (json.JSONDecodeError, IOError):
                        pass
                    break

        # Parse diagnostic matrix
        diag = self.parse_diagnostic_matrix()
        if diag:
            state.diagnostic_matrix = diag
            state.diagnostic_timestamp = diag.get('timestamp', '')
        state.diagnostic_running = self.check_diagnostic_running()

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
