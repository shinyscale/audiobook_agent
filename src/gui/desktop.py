"""
Desktop GUI for Audiobook Prep using tkinter.
Provides file pickers, progress tracking, and result viewing.
"""

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False
    # Create dummy classes for type hints
    tk = None
    filedialog = None
    messagebox = None
    ttk = None

from pathlib import Path
import threading
import json
from typing import Optional
import os

try:
    from ..analyzer import AudiobookAnalyzer
    from ..models import AnalysisResult
    from ..pipeline.metrics import ProgressSnapshot, MetricsCollector
    from ..pipeline.pricing import format_cost
    HAS_ANALYZER = True
except ImportError:
    HAS_ANALYZER = False
    format_cost = None

try:
    from ..llm.config import (
        LLMProvider,
        DEFAULT_URLS,
        detect_available_models,
        detect_context_length,
        test_connection,
        pull_ollama_model,
        delete_ollama_model,
    )
    from ..llm.prompts import PromptConfig, DEFAULT_PROMPTS
    HAS_LLM_CONFIG = True
except ImportError:
    HAS_LLM_CONFIG = False
    PromptConfig = None  # type: ignore
    DEFAULT_PROMPTS = None  # type: ignore

try:
    from .tui import run_tui
    HAS_TUI = True
except ImportError:
    HAS_TUI = False

try:
    from ..agents.config import (
        AgentConfig,
        OrchestratorConfig,
        PipelineTuningConfig,
        RECOMMENDED_AGENT_MODELS,
        create_optimized_config,
    )
    HAS_AGENT_CONFIG = True
except ImportError:
    HAS_AGENT_CONFIG = False
    OrchestratorConfig = None  # type: ignore
    PipelineTuningConfig = None  # type: ignore

try:
    from ..system import (
        detect_system_specs,
        detect_optimal_profile,
        format_specs_display,
        HARDWARE_PROFILES,
        apply_profile_to_config,
    )
    HAS_SYSTEM_DETECTION = True
except ImportError:
    HAS_SYSTEM_DETECTION = False


# Stage order mapping for display purposes
# This defines the expected execution order of pipeline stages
STAGE_ORDER = {
    "Chapter Detection": 1,
    "Character Extraction": 2,
    "Character Extraction V2": 2,  # Alternative to V1, same position
    "Chapter Summaries": 3,
    "Character Profiles": 4,
    "Pronunciation Guide": 5,
}


def get_stage_order(stage_name: str) -> str:
    """Get the order prefix for a stage name."""
    order = STAGE_ORDER.get(stage_name)
    if order:
        return f"{order}. "
    return ""


def make_combobox_auto_expand(combobox: "ttk.Combobox"):
    """Make combobox dropdown expand to fit longest value.

    This fixes the issue where long model names are truncated in dropdowns.
    """
    def adjust_dropdown_width():
        # Get all values
        values = combobox.cget('values')
        if not values:
            return

        # Find longest value
        max_length = max(len(str(v)) for v in values)

        # Set dropdown width (convert chars to pixels, roughly 7px per char)
        # The combobox widget width controls the dropdown listbox width
        try:
            # Set the listbox width to accommodate longest item
            combobox.configure(width=max(max_length, 30))
        except:
            pass  # Ignore errors

    # Set postcommand to adjust width before showing dropdown
    combobox.configure(postcommand=adjust_dropdown_width)


class ProgressWindow:
    """Enhanced window showing detailed analysis progress."""

    def __init__(self, parent, metrics_collector: Optional[MetricsCollector] = None):
        self.window = tk.Toplevel(parent)
        self.window.title("Analyzing...")
        self.window.geometry("650x400")  # Larger to fit new info
        self.window.transient(parent)
        self.window.grab_set()

        self.metrics = metrics_collector
        self.cancelled = False
        self.details_expanded = False

        # Center on parent
        self.window.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 325
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 200
        self.window.geometry(f"+{x}+{y}")

        # Main content frame
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Stage name (large, prominent)
        self.stage_label = tk.Label(
            main_frame,
            text="Initializing...",
            font=("Arial", 12, "bold")
        )
        self.stage_label.pack(pady=(0, 10))

        # Progress bar with percentage
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='indeterminate',
            length=550
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.percent_label = tk.Label(progress_frame, text="", width=5)
        self.percent_label.pack(side=tk.LEFT, padx=(5, 0))

        # Start indeterminate animation
        self.progress_bar.start(10)

        # Timing section
        timing_frame = tk.Frame(main_frame)
        timing_frame.pack(fill=tk.X, pady=10)
        self.stage_time_label = tk.Label(
            timing_frame,
            text="⏱️  Stage: 0:00",
            anchor=tk.W,
            font=("Arial", 9)
        )
        self.stage_time_label.pack(fill=tk.X)
        self.total_time_label = tk.Label(
            timing_frame,
            text="⏱️  Total: 0:00 elapsed",
            anchor=tk.W,
            font=("Arial", 9)
        )
        self.total_time_label.pack(fill=tk.X)

        # Metrics section (items, confidence, model, tokens)
        metrics_frame = tk.Frame(main_frame)
        metrics_frame.pack(fill=tk.X, pady=10)
        self.items_label = tk.Label(
            metrics_frame,
            text="📊 Items: Processing...",
            anchor=tk.W,
            font=("Arial", 9)
        )
        self.items_label.pack(fill=tk.X)
        self.model_label = tk.Label(
            metrics_frame,
            text="🤖 Model: ...",
            anchor=tk.W,
            font=("Arial", 9)
        )
        self.model_label.pack(fill=tk.X)
        self.tokens_label = tk.Label(
            metrics_frame,
            text="💰 In: 0 | Out: 0 | Cost: $0.00",
            anchor=tk.W,
            font=("Arial", 9)
        )
        self.tokens_label.pack(fill=tk.X)

        # Expandable details section
        self.details_frame = tk.Frame(main_frame)
        self.details_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.details_toggle = tk.Button(
            self.details_frame,
            text="▼ Stage Details",
            command=self._toggle_details
        )
        self.details_toggle.pack()

        # Details content (initially hidden)
        self.details_content = tk.Frame(self.details_frame)

        # Text widget for stage table
        self.details_text = tk.Text(
            self.details_content,
            height=6,
            font=("Courier", 9),
            wrap=tk.NONE
        )
        self.details_text.pack(fill=tk.BOTH, expand=True)
        self.details_text.config(state=tk.DISABLED)

        # Cancel button
        self.cancel_button = tk.Button(
            main_frame,
            text="Cancel",
            command=self.cancel,
            state=tk.DISABLED  # For now, don't allow cancel
        )
        self.cancel_button.pack(pady=10)

        # Start polling if metrics provided
        if self.metrics:
            self._poll_progress()

    def _poll_progress(self):
        """Poll metrics collector for updates (every 100ms)."""
        if self.window.winfo_exists():
            try:
                snapshot = self.metrics.get_progress_snapshot()
                self._update_display(snapshot)
            except Exception as e:
                # If polling fails, just skip this update
                pass
            self.window.after(100, self._poll_progress)

    def _update_display(self, snapshot: ProgressSnapshot):
        """Update all widgets based on snapshot."""
        # Stage name
        if snapshot.current_stage_name:
            order_prefix = get_stage_order(snapshot.current_stage_name)
            self.stage_label.config(text=f"Analyzing: {order_prefix}{snapshot.current_stage_name}")

        # Progress bar
        if snapshot.progress_percentage:
            self.progress_bar.stop()
            self.progress_bar['mode'] = 'determinate'
            self.progress_bar['value'] = snapshot.progress_percentage
            self.percent_label.config(text=f"{snapshot.progress_percentage:.0f}%")
        else:
            if self.progress_bar['mode'] != 'indeterminate':
                self.progress_bar['mode'] = 'indeterminate'
                self.progress_bar.start(10)
            self.percent_label.config(text="")

        # Timing
        stage_time = self._format_duration(snapshot.current_stage_elapsed_seconds)
        self.stage_time_label.config(text=f"⏱️  Stage: {stage_time}")

        if snapshot.estimated_remaining_seconds:
            total_est = self._format_duration(snapshot.estimated_remaining_seconds)
            self.total_time_label.config(
                text=f"⏱️  Total: {self._format_duration(snapshot.total_elapsed_seconds)} elapsed, "
                     f"~{total_est} remaining"
            )
        else:
            self.total_time_label.config(
                text=f"⏱️  Total: {self._format_duration(snapshot.total_elapsed_seconds)} elapsed"
            )

        # Items and confidence (stage-aware labels)
        stage_labels = {
            "Chapter Detection": "chapters",
            "Character Extraction": "characters",
            "Character Profiles": "profiles",
            "Chapter Summaries": "summaries",
            "Pronunciation Guide": "words",
        }

        if snapshot.current_stage_items_processed > 0:
            # Get stage-specific item type
            item_type = stage_labels.get(snapshot.current_stage_name, "items")
            items_text = f"📊 {snapshot.current_stage_items_processed} {item_type}"
            if snapshot.current_stage_items_total:
                items_text += f" / {snapshot.current_stage_items_total}"

            # Confidence breakdown
            h, m, l = (
                snapshot.current_stage_high_confidence,
                snapshot.current_stage_medium_confidence,
                snapshot.current_stage_low_confidence
            )
            if h + m + l > 0:
                items_text += f" ({h}H/{m}M/{l}L confidence)"

            self.items_label.config(text=items_text)
        else:
            # Show stage-specific "starting" message
            stage_starting = {
                "Chapter Detection": "📊 Detecting chapters...",
                "Character Extraction": "📊 Extracting characters...",
                "Character Profiles": "📊 Profiling characters...",
                "Chapter Summaries": "📊 Generating summaries...",
                "Pronunciation Guide": "📊 Building pronunciation guide...",
            }
            msg = stage_starting.get(snapshot.current_stage_name, "📊 Processing...")
            self.items_label.config(text=msg)

        # Model
        if snapshot.current_stage_model:
            provider = snapshot.current_stage_provider or "unknown"
            self.model_label.config(
                text=f"🤖 Model: {snapshot.current_stage_model} ({provider})"
            )
        else:
            self.model_label.config(text="🤖 Model: ...")

        # Tokens and cost
        if format_cost:
            cost_str = format_cost(snapshot.estimated_cost_usd)
        elif snapshot.estimated_cost_usd is not None:
            cost_str = f"${snapshot.estimated_cost_usd:.3f}"
        else:
            cost_str = "Unknown"

        self.tokens_label.config(
            text=f"💰 In: {snapshot.total_prompt_tokens:,} | Out: {snapshot.total_completion_tokens:,} | Cost: {cost_str}"
        )

        # Update details if expanded
        if self.details_expanded:
            self._update_details_table(snapshot)

    def _toggle_details(self):
        """Toggle visibility of details section."""
        if self.details_expanded:
            self.details_content.pack_forget()
            self.details_toggle.config(text="▼ Stage Details")
            self.details_expanded = False
        else:
            self.details_content.pack(fill=tk.BOTH, expand=True)
            self.details_toggle.config(text="▲ Stage Details")
            self.details_expanded = True

    def _update_details_table(self, snapshot: ProgressSnapshot):
        """Update the detailed stage table."""
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)

        # Build table
        lines = []
        lines.append("Stage                       Time    Items  Confidence")
        lines.append("─" * 59)

        # Completed stages
        for stage in snapshot.completed_stages:
            time_str = self._format_duration(stage.duration_seconds)
            order_prefix = get_stage_order(stage.stage_name)
            stage_display = f"{order_prefix}{stage.stage_name}"
            lines.append(
                f"✓ {stage_display:<25} {time_str:>7} {stage.items_processed:>5}  "
                f"{stage.confidence_summary}"
            )

        # Current stage
        if snapshot.current_stage_name:
            time_str = self._format_duration(snapshot.current_stage_elapsed_seconds)
            items = snapshot.current_stage_items_processed
            h, m, l = (
                snapshot.current_stage_high_confidence,
                snapshot.current_stage_medium_confidence,
                snapshot.current_stage_low_confidence
            )
            order_prefix = get_stage_order(snapshot.current_stage_name)
            stage_display = f"{order_prefix}{snapshot.current_stage_name}"
            lines.append(
                f"→ {stage_display:<25} {time_str:>7} {items:>5}  "
                f"{h}H/{m}M/{l}L"
            )

        self.details_text.insert(1.0, "\n".join(lines))
        self.details_text.config(state=tk.DISABLED)

    def show_completion_summary(self, snapshot: ProgressSnapshot):
        """Show final summary when analysis completes."""
        self.stage_label.config(text="✅ Analysis Complete!")
        self.progress_bar.stop()
        self.progress_bar['mode'] = 'determinate'
        self.progress_bar['value'] = 100
        self.percent_label.config(text="100%")

        # Update to show final summary
        self.details_toggle.config(text="▼ Final Summary")
        # Force expand
        if not self.details_expanded:
            self._toggle_details()

    def _format_duration(self, seconds: float) -> str:
        """Format seconds as M:SS."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"

    def cancel(self):
        """Cancel analysis."""
        self.cancelled = True
        self.window.destroy()

    def update(self, message: str):
        """Update progress message (legacy compatibility)."""
        self.stage_label.config(text=message)
        self.window.update_idletasks()

    def close(self):
        """Close progress window."""
        self.window.destroy()


class PromptEditorDialog:
    """Dialog for editing LLM prompts."""

    def __init__(self, parent, current_prompts: "PromptConfig"):
        if not HAS_TKINTER or not HAS_LLM_CONFIG:
            raise ImportError("tkinter and LLM config are required")

        self.window = tk.Toplevel(parent)
        self.window.title("Edit LLM Prompts")
        self.window.geometry("800x600")
        self.window.transient(parent)
        self.window.grab_set()

        # Center on parent
        self.window.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 400
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 300
        self.window.geometry(f"+{x}+{y}")

        self.current_prompts = current_prompts
        self.result_prompts: Optional["PromptConfig"] = None
        self.prompt_vars: dict[str, tk.StringVar] = {}

        self._create_widgets()

    def _create_widgets(self):
        """Create dialog widgets."""
        # Main container with scrollbar
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Description
        ttk.Label(
            main_frame,
            text="Customize the system prompts used by the LLM for each analysis task.",
            wraplength=750
        ).pack(anchor=tk.W, pady=(0, 10))

        # Create notebook (tabs) for each prompt
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # Get prompt descriptions
        descriptions = PromptConfig.get_prompt_descriptions()

        # Create a tab for each prompt
        for field_name, display_name in descriptions.items():
            current_value = getattr(self.current_prompts, field_name, "")
            default_value = getattr(DEFAULT_PROMPTS, field_name, "")

            # Create frame for this prompt
            frame = ttk.Frame(notebook, padding="10")
            notebook.add(frame, text=display_name[:20])  # Truncate long names

            # Reset button at top
            btn_frame = ttk.Frame(frame)
            btn_frame.pack(fill=tk.X, pady=(0, 5))

            ttk.Label(btn_frame, text=display_name, font=("Arial", 10, "bold")).pack(side=tk.LEFT)

            def make_reset_callback(fn, dv):
                def reset():
                    self.prompt_vars[fn].set(dv)
                return reset

            reset_btn = ttk.Button(
                btn_frame,
                text="Reset to Default",
                command=make_reset_callback(field_name, default_value)
            )
            reset_btn.pack(side=tk.RIGHT)

            # Text area with scrollbar
            text_frame = ttk.Frame(frame)
            text_frame.pack(fill=tk.BOTH, expand=True)

            scrollbar = ttk.Scrollbar(text_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            text_widget = tk.Text(
                text_frame,
                wrap=tk.WORD,
                yscrollcommand=scrollbar.set,
                font=("Consolas", 10),
                height=15
            )
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=text_widget.yview)

            # Insert current value
            text_widget.insert("1.0", current_value)

            # Store reference (using a StringVar wrapper for tracking)
            var = tk.StringVar(value=current_value)
            self.prompt_vars[field_name] = var

            # Bind text changes to variable
            def make_update_callback(var_ref, text_ref):
                def update(*args):
                    var_ref.set(text_ref.get("1.0", "end-1c"))
                return update

            text_widget.bind("<KeyRelease>", make_update_callback(var, text_widget))

            # Store text widget for later update
            var._text_widget = text_widget  # type: ignore

        # Button row
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(
            button_frame,
            text="Reset All to Defaults",
            command=self._reset_all
        ).pack(side=tk.LEFT)

        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._cancel
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            button_frame,
            text="Save",
            command=self._save
        ).pack(side=tk.RIGHT)

    def _reset_all(self):
        """Reset all prompts to defaults."""
        for field_name, var in self.prompt_vars.items():
            default_value = getattr(DEFAULT_PROMPTS, field_name, "")
            var.set(default_value)
            if hasattr(var, "_text_widget"):
                var._text_widget.delete("1.0", tk.END)  # type: ignore
                var._text_widget.insert("1.0", default_value)  # type: ignore

    def _save(self):
        """Save prompts and close dialog."""
        # Build new PromptConfig from edited values
        kwargs = {}
        for field_name, var in self.prompt_vars.items():
            # Get value from text widget
            if hasattr(var, "_text_widget"):
                value = var._text_widget.get("1.0", "end-1c")  # type: ignore
            else:
                value = var.get()
            kwargs[field_name] = value

        self.result_prompts = PromptConfig(**kwargs)
        self.window.destroy()

    def _cancel(self):
        """Cancel without saving."""
        self.result_prompts = None
        self.window.destroy()

    def show(self) -> Optional["PromptConfig"]:
        """Show dialog and return result."""
        self.window.wait_window()
        return self.result_prompts


class LLMSettingsPanel:
    """Expandable/collapsible LLM configuration panel."""

    # Provider display names
    PROVIDER_NAMES = {
        "ollama": "Ollama",
        "lm_studio": "LM Studio",
        "openai": "OpenAI",
        "anthropic": "Anthropic",
    }

    def __init__(self, parent):
        if not HAS_TKINTER:
            raise ImportError("tkinter is required")

        self.parent = parent

        # State variables
        self.expanded = tk.BooleanVar(value=False)
        self.editing_enabled = tk.BooleanVar(value=False)  # Prevent accidental changes
        self.provider = tk.StringVar(value="lm_studio")
        self.model = tk.StringVar()
        self.base_url = tk.StringVar()
        self.api_key = tk.StringVar()
        self.context_length = tk.IntVar(value=32768)
        self.detected_models: list[str] = []
        self.custom_prompts: Optional["PromptConfig"] = None  # User-customized prompts

        self._create_widgets()
        self._update_for_provider()
        self._update_editing_state()  # Apply initial disabled state

    def _create_widgets(self):
        """Create the panel widgets."""
        # Outer frame
        self.outer_frame = ttk.Frame(self.parent)

        # Header row (always visible)
        header_frame = ttk.Frame(self.outer_frame)
        header_frame.pack(fill=tk.X)

        self.toggle_button = ttk.Button(
            header_frame,
            text="▶ LLM Settings",
            command=self._toggle_expanded,
            width=18
        )
        self.toggle_button.pack(side=tk.LEFT)

        # Provider label shown when collapsed
        self.provider_label = ttk.Label(header_frame, text="Provider: LM Studio")
        self.provider_label.pack(side=tk.LEFT, padx=10)

        # Expandable content frame (hidden by default)
        self.content_frame = ttk.LabelFrame(
            self.outer_frame,
            text="LLM Configuration",
            padding="10"
        )

        self._create_content_widgets()

    def _create_content_widgets(self):
        """Create widgets inside the expandable panel."""
        # Enable editing checkbox
        enable_row = ttk.Frame(self.content_frame)
        enable_row.pack(fill=tk.X, pady=(0, 10))

        ttk.Checkbutton(
            enable_row,
            text="Enable editing (prevents accidental changes)",
            variable=self.editing_enabled,
            command=self._update_editing_state
        ).pack(side=tk.LEFT)

        ttk.Separator(self.content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 10))

        # Row 1: Provider selection
        provider_row = ttk.Frame(self.content_frame)
        provider_row.pack(fill=tk.X, pady=5)

        ttk.Label(provider_row, text="Provider:").pack(side=tk.LEFT)
        self.provider_combo = ttk.Combobox(
            provider_row,
            textvariable=self.provider,
            values=["ollama", "lm_studio", "openai", "anthropic"],
            state="readonly",
            width=15
        )
        self.provider_combo.pack(side=tk.LEFT, padx=5)
        self.provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)

        # Row 2: Base URL
        url_row = ttk.Frame(self.content_frame)
        url_row.pack(fill=tk.X, pady=5)

        ttk.Label(url_row, text="Base URL:").pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(url_row, textvariable=self.base_url, width=45)
        self.url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Row 3: Model selection
        model_row = ttk.Frame(self.content_frame)
        model_row.pack(fill=tk.X, pady=5)

        ttk.Label(model_row, text="Model:").pack(side=tk.LEFT)
        self.model_combo = ttk.Combobox(
            model_row,
            textvariable=self.model,
            width=35
        )
        self.model_combo.pack(side=tk.LEFT, padx=5)
        make_combobox_auto_expand(self.model_combo)  # Auto-expand for long model names

        self.detect_models_button = ttk.Button(
            model_row,
            text="Detect",
            command=self._detect_models,
            width=8
        )
        self.detect_models_button.pack(side=tk.LEFT, padx=2)

        # Row 3b: Ollama Management (shown only for Ollama provider)
        self.ollama_mgmt_frame = ttk.Frame(self.content_frame)

        ttk.Label(self.ollama_mgmt_frame, text="Pull Model:").pack(side=tk.LEFT)
        self.pull_model_entry = ttk.Entry(self.ollama_mgmt_frame, width=20)
        self.pull_model_entry.pack(side=tk.LEFT, padx=5)
        self.pull_model_entry.insert(0, "qwen2.5:7b")  # Default suggestion

        self.pull_button = ttk.Button(
            self.ollama_mgmt_frame,
            text="Pull",
            command=self._pull_model,
            width=6
        )
        self.pull_button.pack(side=tk.LEFT, padx=2)

        self.delete_button = ttk.Button(
            self.ollama_mgmt_frame,
            text="Delete Selected",
            command=self._delete_model
        )
        self.delete_button.pack(side=tk.LEFT, padx=10)

        # Row 3c: Pull progress (shown during pull operations)
        self.pull_progress_frame = ttk.Frame(self.content_frame)
        self.pull_progress_var = tk.StringVar(value="")
        self.pull_progress_label = ttk.Label(
            self.pull_progress_frame,
            textvariable=self.pull_progress_var,
            width=40
        )
        self.pull_progress_label.pack(side=tk.LEFT)
        self.pull_progress_bar = ttk.Progressbar(
            self.pull_progress_frame,
            length=200,
            mode='determinate'
        )
        self.pull_progress_bar.pack(side=tk.LEFT, padx=5)

        # Row 4: Context length
        context_row = ttk.Frame(self.content_frame)
        context_row.pack(fill=tk.X, pady=5)

        ttk.Label(context_row, text="Context Length:").pack(side=tk.LEFT)
        self.context_spinbox = ttk.Spinbox(
            context_row,
            from_=1024,
            to=262144,
            textvariable=self.context_length,
            width=10,
            increment=1024
        )
        self.context_spinbox.pack(side=tk.LEFT, padx=5)

        self.detect_context_button = ttk.Button(
            context_row,
            text="Auto",
            command=self._detect_context_length,
            width=6
        )
        self.detect_context_button.pack(side=tk.LEFT, padx=2)

        ttk.Label(context_row, text="tokens").pack(side=tk.LEFT)

        # Row 5: API Key (only shown for cloud providers)
        self.api_key_row = ttk.Frame(self.content_frame)

        ttk.Label(self.api_key_row, text="API Key:").pack(side=tk.LEFT)
        self.api_key_entry = ttk.Entry(
            self.api_key_row,
            textvariable=self.api_key,
            show="*",
            width=45
        )
        self.api_key_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Row 6: Test connection button
        button_row = ttk.Frame(self.content_frame)
        button_row.pack(fill=tk.X, pady=10)

        self.test_button = ttk.Button(
            button_row,
            text="Test Connection",
            command=self._test_connection
        )
        self.test_button.pack(side=tk.LEFT)

        self.status_label = ttk.Label(button_row, text="")
        self.status_label.pack(side=tk.LEFT, padx=10)

        # Row 7: Edit Prompts button
        prompts_row = ttk.Frame(self.content_frame)
        prompts_row.pack(fill=tk.X, pady=5)

        self.edit_prompts_button = ttk.Button(
            prompts_row,
            text="Edit Prompts...",
            command=self._edit_prompts
        )
        self.edit_prompts_button.pack(side=tk.LEFT)

        self.prompts_status_label = ttk.Label(prompts_row, text="Using default prompts")
        self.prompts_status_label.pack(side=tk.LEFT, padx=10)

    def _toggle_expanded(self):
        """Toggle panel expansion."""
        if self.expanded.get():
            self.content_frame.pack_forget()
            self.toggle_button.config(text="▶ LLM Settings")
            self.expanded.set(False)
        else:
            self.content_frame.pack(fill=tk.X, pady=5)
            self.toggle_button.config(text="▼ LLM Settings")
            self.expanded.set(True)

    def _update_editing_state(self):
        """Enable or disable all editable widgets based on editing_enabled."""
        enabled = self.editing_enabled.get()
        state = "readonly" if enabled else "disabled"
        entry_state = "normal" if enabled else "disabled"
        button_state = "normal" if enabled else "disabled"

        # Update comboboxes (use readonly when enabled, disabled when not)
        self.provider_combo.config(state=state)
        self.model_combo.config(state=state if enabled else "disabled")

        # Update entry fields
        self.url_entry.config(state=entry_state)
        self.api_key_entry.config(state=entry_state)
        self.context_spinbox.config(state=entry_state)
        self.pull_model_entry.config(state=entry_state)

        # Update buttons
        self.detect_models_button.config(state=button_state)
        self.detect_context_button.config(state=button_state)
        self.test_button.config(state=button_state)
        self.pull_button.config(state=button_state)
        self.delete_button.config(state=button_state)
        self.edit_prompts_button.config(state=button_state)

    def _on_provider_change(self, event=None):
        """Handle provider selection change."""
        self._update_for_provider()
        # Auto-detect models for local providers
        provider = self.provider.get()
        if provider in ("ollama", "lm_studio"):
            self._detect_models()

    def _update_for_provider(self):
        """Update UI based on selected provider."""
        provider = self.provider.get()

        # Update default URL
        if HAS_LLM_CONFIG:
            try:
                provider_enum = LLMProvider(provider)
                default_url = DEFAULT_URLS.get(provider_enum, "")
                self.base_url.set(default_url)
            except ValueError:
                pass
        else:
            # Fallback defaults
            default_urls = {
                "ollama": "http://localhost:11434",
                "lm_studio": "http://localhost:1234/v1",
                "openai": "https://api.openai.com/v1",
                "anthropic": "https://api.anthropic.com/v1",
            }
            self.base_url.set(default_urls.get(provider, ""))

        # Show/hide API key field
        if provider in ("openai", "anthropic"):
            self.api_key_row.pack(fill=tk.X, pady=5, before=self.content_frame.winfo_children()[-1])
        else:
            self.api_key_row.pack_forget()

        # Update provider label in collapsed view
        display_name = self.PROVIDER_NAMES.get(provider, provider)
        self.provider_label.config(text=f"Provider: {display_name}")

        # Enable/disable detect buttons for local providers
        is_local = provider in ("ollama", "lm_studio")
        state = tk.NORMAL if is_local else tk.DISABLED
        self.detect_models_button.config(state=state)
        self.detect_context_button.config(state=state)

        # Show/hide Ollama management section
        if provider == "ollama":
            self.ollama_mgmt_frame.pack(fill=tk.X, pady=5)
        else:
            self.ollama_mgmt_frame.pack_forget()
            self.pull_progress_frame.pack_forget()

        # Clear status
        self.status_label.config(text="")

    def _detect_models(self):
        """Fetch available models from local provider."""
        if not HAS_LLM_CONFIG:
            self.status_label.config(text="LLM config not available")
            return

        provider = self.provider.get()
        base_url = self.base_url.get()

        self.status_label.config(text="Detecting models...")
        self.parent.update_idletasks()

        try:
            provider_enum = LLMProvider(provider)
            models = detect_available_models(provider_enum, base_url)
            if models:
                self.detected_models = models
                self.model_combo["values"] = models
                if models and not self.model.get():
                    self.model.set(models[0])
                self.status_label.config(text=f"Found {len(models)} model(s)")
            else:
                self.status_label.config(text="No models found")
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)[:30]}")

    def _pull_model(self):
        """Pull a model from the Ollama library."""
        if not HAS_LLM_CONFIG:
            self.status_label.config(text="LLM config not available")
            return

        model_name = self.pull_model_entry.get().strip()
        if not model_name:
            self.status_label.config(text="Enter a model name to pull")
            return

        base_url = self.base_url.get()

        # Show progress frame
        self.pull_progress_frame.pack(fill=tk.X, pady=5)
        self.pull_button.config(state=tk.DISABLED)
        self.pull_progress_bar["value"] = 0
        self.pull_progress_var.set(f"Pulling {model_name}...")
        self.parent.update_idletasks()

        def progress_callback(status, completed, total):
            if total > 0:
                percent = (completed / total) * 100
                self.parent.after(0, lambda p=percent: self.pull_progress_bar.configure(value=p))
            # Truncate status message
            status_short = status[:35] + "..." if len(status) > 35 else status
            self.parent.after(0, lambda s=status_short: self.pull_progress_var.set(s))

        def pull_thread():
            try:
                success, message = pull_ollama_model(model_name, base_url, progress_callback)
                if success:
                    self.parent.after(0, lambda: self.pull_progress_var.set(f"✓ {model_name} ready"))
                    # Refresh model list
                    self.parent.after(500, self._detect_models)
                else:
                    self.parent.after(0, lambda m=message: self.pull_progress_var.set(f"✗ {m[:40]}"))
            except Exception as e:
                self.parent.after(0, lambda: self.pull_progress_var.set(f"✗ Error: {str(e)[:30]}"))
            finally:
                self.parent.after(0, lambda: self.pull_button.config(state=tk.NORMAL))

        thread = threading.Thread(target=pull_thread, daemon=True)
        thread.start()

    def _delete_model(self):
        """Delete the currently selected model from Ollama."""
        if not HAS_LLM_CONFIG:
            self.status_label.config(text="LLM config not available")
            return

        model_name = self.model.get()
        if not model_name:
            self.status_label.config(text="Select a model first")
            return

        # Confirm deletion
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete model '{model_name}'?\n\nThis will free disk space but you'll need to pull it again to use it."
        ):
            return

        base_url = self.base_url.get()
        success, message = delete_ollama_model(model_name, base_url)

        if success:
            self.status_label.config(text=f"✓ Deleted {model_name}")
            self._detect_models()  # Refresh list
        else:
            self.status_label.config(text=f"✗ {message[:30]}")

    def _detect_context_length(self):
        """Auto-detect context length from model metadata."""
        if not HAS_LLM_CONFIG:
            self.status_label.config(text="LLM config not available")
            return

        provider = self.provider.get()
        model = self.model.get()
        base_url = self.base_url.get()

        if not model:
            self.status_label.config(text="Select a model first")
            return

        self.status_label.config(text="Detecting context...")
        self.parent.update_idletasks()

        try:
            provider_enum = LLMProvider(provider)
            ctx_len = detect_context_length(provider_enum, model, base_url)
            if ctx_len:
                self.context_length.set(ctx_len)
                self.status_label.config(text=f"Context: {ctx_len:,} tokens")
            else:
                self.status_label.config(text="Could not detect context length")
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)[:30]}")

    def _test_connection(self):
        """Test connection to configured provider."""
        if not HAS_LLM_CONFIG:
            self.status_label.config(text="LLM config not available")
            return

        provider = self.provider.get()
        base_url = self.base_url.get()
        api_key = self.api_key.get() if provider in ("openai", "anthropic") else None
        model = self.model.get() or None

        self.status_label.config(text="Testing connection...")
        self.test_button.config(state=tk.DISABLED)
        self.parent.update_idletasks()

        def run_test():
            try:
                provider_enum = LLMProvider(provider)
                success, message = test_connection(provider_enum, base_url, api_key, model)
                self.parent.after(0, lambda: self._show_test_result(success, message))
            except Exception as e:
                self.parent.after(0, lambda: self._show_test_result(False, str(e)))

        thread = threading.Thread(target=run_test, daemon=True)
        thread.start()

    def _show_test_result(self, success: bool, message: str):
        """Show test connection result."""
        self.test_button.config(state=tk.NORMAL)
        prefix = "✓ " if success else "✗ "
        self.status_label.config(text=prefix + message[:40])

    def _edit_prompts(self):
        """Open the prompts editor dialog."""
        if not HAS_LLM_CONFIG or PromptConfig is None:
            self.prompts_status_label.config(text="Prompt editing not available")
            return

        # Use current prompts or defaults
        current = self.custom_prompts or DEFAULT_PROMPTS

        # Open dialog
        dialog = PromptEditorDialog(self.parent, current)
        result = dialog.show()

        if result is not None:
            self.custom_prompts = result
            self.prompts_status_label.config(text="Using custom prompts")
        # If cancelled, keep existing prompts

    def get_settings(self) -> dict:
        """Get current settings as a dict."""
        provider = self.provider.get()
        return {
            "provider": provider,
            "model": self.model.get(),
            "base_url": self.base_url.get(),
            "api_key": self.api_key.get() if provider in ("openai", "anthropic") else None,
            "context_length": self.context_length.get(),
            "prompts": self.custom_prompts,
        }

    def pack(self, **kwargs):
        """Allow panel to be packed like a regular widget."""
        self.outer_frame.pack(**kwargs)


class SystemProfilePanel:
    """Panel showing detected system hardware and profile."""

    def __init__(self, parent, llm_panel: LLMSettingsPanel, agent_config_panel=None):
        if not HAS_TKINTER:
            raise ImportError("tkinter is required")

        self.parent = parent
        self.llm_panel = llm_panel
        self.agent_config_panel = agent_config_panel  # Set after init

        # State variables
        self.expanded = tk.BooleanVar(value=False)
        self.detected_specs = None
        self.detected_profile = None

        self._create_widgets()

        # Auto-detect on startup (in background to avoid blocking)
        if HAS_SYSTEM_DETECTION:
            self.parent.after(100, self._detect_hardware)

    def set_agent_config_panel(self, panel):
        """Set the agent config panel reference (for auto-optimization)."""
        self.agent_config_panel = panel

    def _create_widgets(self):
        """Create the panel widgets."""
        # Outer frame
        self.outer_frame = ttk.Frame(self.parent)

        # Header row (always visible)
        header_frame = ttk.Frame(self.outer_frame)
        header_frame.pack(fill=tk.X)

        self.toggle_button = ttk.Button(
            header_frame,
            text="▶ System Profile",
            command=self._toggle_expanded,
            width=18
        )
        self.toggle_button.pack(side=tk.LEFT)

        # Status label shown when collapsed
        self.status_label = ttk.Label(header_frame, text="Detecting hardware...")
        self.status_label.pack(side=tk.LEFT, padx=10)

        # Expandable content frame (hidden by default)
        self.content_frame = ttk.LabelFrame(
            self.outer_frame,
            text="System Hardware Profile",
            padding="10"
        )

        self._create_content_widgets()

    def _create_content_widgets(self):
        """Create widgets inside the expandable panel."""
        if not HAS_SYSTEM_DETECTION:
            ttk.Label(
                self.content_frame,
                text="System detection not available (missing psutil)",
                foreground="gray"
            ).pack(anchor=tk.W)
            return

        # Hardware info display
        self.hw_info_frame = ttk.Frame(self.content_frame)
        self.hw_info_frame.pack(fill=tk.X, pady=5)

        # Platform row
        self.platform_label = ttk.Label(self.hw_info_frame, text="Platform: Detecting...")
        self.platform_label.pack(anchor=tk.W)

        # CPU row
        self.cpu_label = ttk.Label(self.hw_info_frame, text="CPU: Detecting...")
        self.cpu_label.pack(anchor=tk.W)

        # RAM row
        self.ram_label = ttk.Label(self.hw_info_frame, text="RAM: Detecting...")
        self.ram_label.pack(anchor=tk.W)

        # GPU row
        self.gpu_label = ttk.Label(self.hw_info_frame, text="GPU: Detecting...")
        self.gpu_label.pack(anchor=tk.W)

        # Separator
        ttk.Separator(self.content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Profile info
        self.profile_frame = ttk.Frame(self.content_frame)
        self.profile_frame.pack(fill=tk.X, pady=5)

        ttk.Label(self.profile_frame, text="Detected Profile:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.profile_name_label = ttk.Label(self.profile_frame, text="Detecting...")
        self.profile_name_label.pack(anchor=tk.W, padx=(10, 0))

        self.profile_desc_label = ttk.Label(self.profile_frame, text="", foreground="gray")
        self.profile_desc_label.pack(anchor=tk.W, padx=(10, 0))

        # Recommendations
        self.rec_frame = ttk.Frame(self.content_frame)
        self.rec_frame.pack(fill=tk.X, pady=5)

        ttk.Label(self.rec_frame, text="Recommendations:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.rec_model_label = ttk.Label(self.rec_frame, text="Max model size: --")
        self.rec_model_label.pack(anchor=tk.W, padx=(10, 0))
        self.rec_workers_label = ttk.Label(self.rec_frame, text="Parallel workers: --")
        self.rec_workers_label.pack(anchor=tk.W, padx=(10, 0))
        self.rec_context_label = ttk.Label(self.rec_frame, text="Context length: --")
        self.rec_context_label.pack(anchor=tk.W, padx=(10, 0))

        # Button row
        button_row = ttk.Frame(self.content_frame)
        button_row.pack(fill=tk.X, pady=10)

        self.optimize_button = ttk.Button(
            button_row,
            text="Auto-Optimize Settings",
            command=self._apply_profile
        )
        self.optimize_button.pack(side=tk.LEFT)

        self.rescan_button = ttk.Button(
            button_row,
            text="Re-scan Hardware",
            command=self._detect_hardware
        )
        self.rescan_button.pack(side=tk.LEFT, padx=5)

    def _toggle_expanded(self):
        """Toggle panel expansion."""
        if self.expanded.get():
            self.content_frame.pack_forget()
            self.toggle_button.config(text="▶ System Profile")
            self.expanded.set(False)
        else:
            self.content_frame.pack(fill=tk.X, pady=5)
            self.toggle_button.config(text="▼ System Profile")
            self.expanded.set(True)

    def _detect_hardware(self):
        """Detect hardware in background thread."""
        if not HAS_SYSTEM_DETECTION:
            self.status_label.config(text="Detection unavailable")
            return

        def detect():
            try:
                specs = detect_system_specs()
                profile = detect_optimal_profile(specs)
                # Update UI on main thread
                self.parent.after(0, lambda: self._update_display(specs, profile))
            except Exception as e:
                self.parent.after(0, lambda: self._show_error(str(e)))

        import threading
        thread = threading.Thread(target=detect, daemon=True)
        thread.start()

    def _update_display(self, specs, profile):
        """Update the display with detected specs."""
        self.detected_specs = specs
        self.detected_profile = profile

        # Update collapsed status
        profile_display = profile.name.replace('_', ' ').title()
        self.status_label.config(text=f"{profile_display} ({specs.ram_gb:.0f}GB RAM)")

        # Update expanded info
        self.platform_label.config(text=f"Platform: {specs.platform.title()} ({specs.architecture})")
        self.cpu_label.config(text=f"CPU Cores: {specs.cpu_cores}")
        self.ram_label.config(text=f"RAM: {specs.ram_gb:.0f} GB")

        if specs.gpu_type != "none":
            vram_str = f"{specs.gpu_vram_gb:.0f} GB"
            if specs.is_apple_silicon:
                vram_str += " unified"
            self.gpu_label.config(text=f"GPU: {specs.gpu_name} ({vram_str})")
        else:
            self.gpu_label.config(text="GPU: None detected")

        # Update profile info
        self.profile_name_label.config(text=profile_display)
        self.profile_desc_label.config(text=profile.description)

        # Update recommendations
        self.rec_model_label.config(text=f"Max model size: {profile.max_model_size_b}B")
        self.rec_workers_label.config(text=f"Parallel workers: {profile.max_parallel_workers}")
        self.rec_context_label.config(text=f"Context length: {profile.context_length:,}")

    def _show_error(self, error: str):
        """Show error in display."""
        self.status_label.config(text="Detection failed")
        self.platform_label.config(text=f"Error: {error}")

    def _apply_profile(self):
        """Apply detected profile to settings."""
        if not self.detected_profile or not HAS_AGENT_CONFIG:
            return

        profile = self.detected_profile

        # Apply context length to LLM settings
        self.llm_panel.context_length.set(profile.context_length)

        # Apply models to agent config if available
        if self.agent_config_panel and HAS_AGENT_CONFIG:
            available_models = self.llm_panel.detected_models or []

            # Create a temporary config and apply profile
            llm_settings = self.llm_panel.get_settings()
            config = create_optimized_config(
                available_models=available_models,
                provider=llm_settings.get("provider", "ollama"),
                base_url=llm_settings.get("base_url", "http://localhost:11434"),
            )
            apply_profile_to_config(profile, config, available_models)

            # Apply to UI
            for agent_name in self.agent_config_panel.AGENT_NAMES:
                agent_config = config.agent_configs.get(agent_name)
                if agent_config and agent_config.model:
                    self.agent_config_panel.agent_models[agent_name].set(agent_config.model)

            self.agent_config_panel._update_status()

        # Show confirmation
        self.status_label.config(text=f"Applied {self.detected_profile.name} profile")

    def get_profile(self):
        """Get the detected profile."""
        return self.detected_profile

    def pack(self, **kwargs):
        """Pack the panel."""
        self.outer_frame.pack(**kwargs)

    def grid(self, **kwargs):
        """Grid the panel."""
        self.outer_frame.grid(**kwargs)


class AgentModelConfigPanel:
    """Expandable/collapsible panel for per-agent model configuration."""

    # Agent display names
    AGENT_NAMES = {
        "structure": "Structure Detection",
        "characters": "Character Extraction",
        "summaries": "Chapter Summaries",
        "pronunciation": "Pronunciation Guide",
    }

    def __init__(self, parent, llm_panel: LLMSettingsPanel):
        if not HAS_TKINTER:
            raise ImportError("tkinter is required")

        self.parent = parent
        self.llm_panel = llm_panel  # Reference for model detection

        # State variables
        self.expanded = tk.BooleanVar(value=False)
        self.editing_enabled = tk.BooleanVar(value=False)  # Prevent accidental changes
        self.experimental_enabled = tk.BooleanVar(value=False)  # Experimental features off by default
        self.auto_optimize = tk.BooleanVar(value=True)
        self.agent_models: dict[str, tk.StringVar] = {}

        # Advanced tuning knobs (defaults match current pipeline behavior)
        # These are intentionally per-run so you can experimentally find a sweet spot.
        self.chapter_marker_chunk_chars = tk.IntVar(value=15000)
        self.chapter_marker_overlap_chars = tk.IntVar(value=1000)
        self.chapter_narrative_chunk_chars = tk.IntVar(value=20000)
        self.chapter_narrative_overlap_chars = tk.IntVar(value=2000)
        self.character_llm_chunk_chars = tk.IntVar(value=8000)
        self.character_mention_context_chars = tk.IntVar(value=100)
        self.summary_chunk_words = tk.IntVar(value=2500)
        self.summary_chunk_overlap_words = tk.IntVar(value=200)

        # Initialize model variables for each agent
        for agent_name in self.AGENT_NAMES:
            self.agent_models[agent_name] = tk.StringVar(value="Default")

        self._create_widgets()
        self._update_editing_state()  # Apply initial disabled state

    def _create_widgets(self):
        """Create the panel widgets."""
        # Outer frame
        self.outer_frame = ttk.Frame(self.parent)

        # Header row (always visible)
        header_frame = ttk.Frame(self.outer_frame)
        header_frame.pack(fill=tk.X)

        self.toggle_button = ttk.Button(
            header_frame,
            text="▶ Agent Model Config",
            command=self._toggle_expanded,
            width=20
        )
        self.toggle_button.pack(side=tk.LEFT)

        # Status label shown when collapsed
        self.status_label = ttk.Label(header_frame, text="Using default models")
        self.status_label.pack(side=tk.LEFT, padx=10)

        # Expandable content frame (hidden by default)
        self.content_frame = ttk.LabelFrame(
            self.outer_frame,
            text="Per-Agent Model Selection",
            padding="10"
        )

        self._create_content_widgets()

    def _create_content_widgets(self):
        """Create widgets inside the expandable panel."""
        # Enable editing checkbox
        enable_row = ttk.Frame(self.content_frame)
        enable_row.pack(fill=tk.X, pady=(0, 10))

        ttk.Checkbutton(
            enable_row,
            text="Enable editing (prevents accidental changes)",
            variable=self.editing_enabled,
            command=self._update_editing_state
        ).pack(side=tk.LEFT)

        ttk.Separator(self.content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 10))

        # Description
        ttk.Label(
            self.content_frame,
            text="Assign different models to each analysis task for optimal results.",
            wraplength=500
        ).pack(anchor=tk.W, pady=(0, 10))

        # Auto-optimize checkbox
        auto_row = ttk.Frame(self.content_frame)
        auto_row.pack(fill=tk.X, pady=5)

        self.auto_optimize_checkbox = ttk.Checkbutton(
            auto_row,
            text="Auto-optimize model assignment",
            variable=self.auto_optimize,
            command=self._on_auto_optimize_change
        )
        self.auto_optimize_checkbox.pack(side=tk.LEFT)

        # Model suitability thresholds (in billions of parameters)
        # "overkill" = model is too large for simple task
        # "underpowered" = model is too small for complex task
        self._model_suitability = {
            "structure": {"type": "overkill", "threshold": 30,
                          "warning": "Large models may over-think simple pattern matching. Consider 7B-20B."},
            "pronunciation": {"type": "overkill", "threshold": 30,
                              "warning": "Large models may over-think pronunciation flagging. Consider 7B-20B."},
            "characters": {"type": "underpowered", "threshold": 30,
                           "warning": "Character analysis benefits from larger models. Consider 30B+."},
            "summaries": {"type": "underpowered", "threshold": 14,
                          "warning": "Summary generation benefits from larger models. Consider 14B+."},
        }

        # Warning labels for each agent
        self._warning_labels: dict[str, ttk.Label] = {}

        # Agent model grid
        grid_frame = ttk.Frame(self.content_frame)
        grid_frame.pack(fill=tk.X, pady=10)

        for i, (agent_name, display_name) in enumerate(self.AGENT_NAMES.items()):
            # Container for this agent (row + warning)
            agent_frame = ttk.Frame(grid_frame)
            agent_frame.pack(fill=tk.X, pady=3)

            # Row for this agent
            row_frame = ttk.Frame(agent_frame)
            row_frame.pack(fill=tk.X)

            # Agent name label
            ttk.Label(
                row_frame,
                text=f"{display_name}:",
                width=20,
                anchor=tk.W
            ).pack(side=tk.LEFT)

            # Model combobox
            combo = ttk.Combobox(
                row_frame,
                textvariable=self.agent_models[agent_name],
                width=25,
                state="readonly"
            )
            combo.pack(side=tk.LEFT, padx=5)
            make_combobox_auto_expand(combo)  # Auto-expand for long model names
            # Store reference for updating values
            setattr(self, f"combo_{agent_name}", combo)

            # Auto button for this agent
            def make_auto_callback(an):
                return lambda: self._auto_suggest_for_agent(an)

            auto_btn = ttk.Button(
                row_frame,
                text="Auto",
                command=make_auto_callback(agent_name),
                width=6
            )
            auto_btn.pack(side=tk.LEFT, padx=2)
            # Store reference for enabling/disabling
            setattr(self, f"auto_btn_{agent_name}", auto_btn)

            # Warning label (hidden by default)
            warning_label = ttk.Label(
                agent_frame,
                text="",
                foreground="orange",
                wraplength=400
            )
            warning_label.pack(anchor=tk.W, padx=(150, 0))
            self._warning_labels[agent_name] = warning_label

            # Add trace to show warnings when model changes
            def make_trace_callback(an):
                return lambda *args: self._check_model_suitability(an)

            self.agent_models[agent_name].trace_add("write", make_trace_callback(agent_name))

        # Button row
        button_row = ttk.Frame(self.content_frame)
        button_row.pack(fill=tk.X, pady=10)

        self.optimize_all_button = ttk.Button(
            button_row,
            text="Optimize All",
            command=self._optimize_all
        )
        self.optimize_all_button.pack(side=tk.LEFT)

        self.refresh_models_button = ttk.Button(
            button_row,
            text="Refresh Models",
            command=self._refresh_models
        )
        self.refresh_models_button.pack(side=tk.LEFT, padx=5)

        # Advanced tuning (chunking) controls
        ttk.Separator(self.content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        self.tuning_frame = ttk.LabelFrame(
            self.content_frame,
            text="Advanced Chunking (Experimental)",
            padding="10",
        )
        self.tuning_frame.pack(fill=tk.X, pady=5)

        # Enable experimental features checkbox
        exp_enable_row = ttk.Frame(self.tuning_frame)
        exp_enable_row.pack(fill=tk.X, pady=(0, 10))

        ttk.Checkbutton(
            exp_enable_row,
            text="Enable experimental features editing",
            variable=self.experimental_enabled,
            command=self._update_experimental_state
        ).pack(side=tk.LEFT)

        ttk.Separator(self.tuning_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 8))

        ttk.Label(
            self.tuning_frame,
            text="These settings control how much text is sent per LLM call and how much context is stored per character mention. Defaults match current behavior.",
            wraplength=520,
            foreground="gray",
        ).pack(anchor=tk.W, pady=(0, 8))

        # Store references to tuning entry widgets
        self._tuning_entries: list[ttk.Entry] = []

        def add_row(parent, label: str, var: tk.IntVar, width: int = 10):
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=34, anchor=tk.W).pack(side=tk.LEFT)
            entry = ttk.Entry(row, textvariable=var, width=width)
            entry.pack(side=tk.LEFT, padx=5)
            self._tuning_entries.append(entry)

        add_row(self.tuning_frame, "Chapter marker chunk size (chars):", self.chapter_marker_chunk_chars)
        add_row(self.tuning_frame, "Chapter marker overlap (chars):", self.chapter_marker_overlap_chars)
        add_row(self.tuning_frame, "Narrative chunk size (chars):", self.chapter_narrative_chunk_chars)
        add_row(self.tuning_frame, "Narrative overlap (chars):", self.chapter_narrative_overlap_chars)
        ttk.Separator(self.tuning_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        add_row(self.tuning_frame, "Character LLM chunk size (chars):", self.character_llm_chunk_chars)
        add_row(self.tuning_frame, "Character mention context window (chars):", self.character_mention_context_chars)
        ttk.Separator(self.tuning_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        add_row(self.tuning_frame, "Summary chunk size (words):", self.summary_chunk_words)
        add_row(self.tuning_frame, "Summary chunk overlap (words):", self.summary_chunk_overlap_words)

        def reset_defaults():
            self.chapter_marker_chunk_chars.set(15000)
            self.chapter_marker_overlap_chars.set(1000)
            self.chapter_narrative_chunk_chars.set(20000)
            self.chapter_narrative_overlap_chars.set(2000)
            self.character_llm_chunk_chars.set(8000)
            self.character_mention_context_chars.set(100)
            self.summary_chunk_words.set(2500)
            self.summary_chunk_overlap_words.set(200)

        self.reset_tuning_button = ttk.Button(
            self.tuning_frame,
            text="Reset tuning to defaults",
            command=reset_defaults,
        )
        self.reset_tuning_button.pack(anchor=tk.W, pady=(10, 0))

    def _toggle_expanded(self):
        """Toggle panel expansion."""
        if self.expanded.get():
            self.content_frame.pack_forget()
            self.toggle_button.config(text="▶ Agent Model Config")
            self.expanded.set(False)
        else:
            self.content_frame.pack(fill=tk.X, pady=5)
            self.toggle_button.config(text="▼ Agent Model Config")
            self.expanded.set(True)
            # Refresh model lists when expanding
            self._refresh_models()

    def _update_editing_state(self):
        """Enable or disable all editable widgets based on editing_enabled."""
        enabled = self.editing_enabled.get()
        state = "readonly" if enabled else "disabled"
        button_state = "normal" if enabled else "disabled"

        # Update auto-optimize checkbox
        self.auto_optimize_checkbox.config(state=button_state)

        # Update agent comboboxes and auto buttons
        for agent_name in self.AGENT_NAMES:
            combo = getattr(self, f"combo_{agent_name}", None)
            auto_btn = getattr(self, f"auto_btn_{agent_name}", None)
            if combo:
                combo.config(state=state if enabled else "disabled")
            if auto_btn:
                auto_btn.config(state=button_state)

        # Update main buttons
        self.optimize_all_button.config(state=button_state)
        self.refresh_models_button.config(state=button_state)

        # Also update experimental state (which depends on editing being enabled)
        self._update_experimental_state()

    def _update_experimental_state(self):
        """Enable or disable experimental tuning widgets."""
        # Experimental features require both editing_enabled AND experimental_enabled
        enabled = self.editing_enabled.get() and self.experimental_enabled.get()
        entry_state = "normal" if enabled else "disabled"
        button_state = "normal" if enabled else "disabled"

        # Update all tuning entry widgets
        for entry in self._tuning_entries:
            entry.config(state=entry_state)

        # Update reset button
        self.reset_tuning_button.config(state=button_state)

    def _on_auto_optimize_change(self):
        """Handle auto-optimize checkbox change."""
        if self.auto_optimize.get():
            self._optimize_all()

    def _refresh_models(self):
        """Refresh available models from LLM panel."""
        # Get models from LLM panel
        models = self.llm_panel.detected_models or []
        model_values = ["Default"] + models

        # Update all comboboxes
        for agent_name in self.AGENT_NAMES:
            combo = getattr(self, f"combo_{agent_name}", None)
            if combo:
                current = self.agent_models[agent_name].get()
                combo["values"] = model_values
                # Restore selection if still valid
                if current not in model_values:
                    self.agent_models[agent_name].set("Default")

    def _auto_suggest_for_agent(self, agent_name: str):
        """Suggest best model for a specific agent."""
        if not HAS_AGENT_CONFIG:
            return

        available = set(m.lower() for m in self.llm_panel.detected_models or [])
        recommendations = RECOMMENDED_AGENT_MODELS.get(agent_name, {})

        for model in recommendations.get("models", []):
            # Check for exact match or partial match (model:size format)
            if model.lower() in available:
                self.agent_models[agent_name].set(model)
                return
            # Check for partial matches
            for avail_model in (self.llm_panel.detected_models or []):
                if model.lower() in avail_model.lower():
                    self.agent_models[agent_name].set(avail_model)
                    return

        # No match found - use default
        self.agent_models[agent_name].set("Default")

    def _optimize_all(self):
        """Apply optimal models to all agents."""
        if not HAS_AGENT_CONFIG:
            return

        available_models = self.llm_panel.detected_models or []
        if not available_models:
            # No models detected - trigger detection
            self.llm_panel._detect_models()
            available_models = self.llm_panel.detected_models or []

        if not available_models:
            return

        # Use create_optimized_config to get recommendations
        llm_settings = self.llm_panel.get_settings()
        config = create_optimized_config(
            available_models=available_models,
            provider=llm_settings.get("provider", "ollama"),
            base_url=llm_settings.get("base_url", "http://localhost:11434"),
        )

        # Apply to UI
        for agent_name in self.AGENT_NAMES:
            agent_config = config.agent_configs.get(agent_name)
            if agent_config and agent_config.model:
                self.agent_models[agent_name].set(agent_config.model)
            else:
                self.agent_models[agent_name].set("Default")

        self._update_status()

    def _update_status(self):
        """Update the status label."""
        non_default = sum(
            1 for v in self.agent_models.values()
            if v.get() != "Default"
        )
        if non_default == 0:
            self.status_label.config(text="Using default models")
        elif non_default == len(self.AGENT_NAMES):
            self.status_label.config(text="All agents configured")
        else:
            self.status_label.config(text=f"{non_default} agents configured")

    def _estimate_model_size(self, model_name: str) -> int:
        """
        Estimate model size in billions from model name.

        Parses patterns like "qwen3:14b", "gpt-oss:120b", "llama3.2", etc.
        Returns 0 if size cannot be determined.
        """
        import re

        if not model_name or model_name == "Default":
            return 0

        # Common patterns: "model:Nb", "model-Nb", "modelNb"
        patterns = [
            r':(\d+)b',           # qwen3:14b, gpt-oss:120b
            r'-(\d+)b',           # llama-7b
            r'(\d+)b$',           # llama7b
            r':(\d+\.?\d*)b',     # qwen3:3.8b
            r'(\d+)x(\d+)b',      # mixtral8x7b -> 56b effective
        ]

        model_lower = model_name.lower()

        for pattern in patterns:
            match = re.search(pattern, model_lower)
            if match:
                if len(match.groups()) == 2:
                    # Mixture of experts (e.g., 8x7b)
                    return int(match.group(1)) * int(match.group(2))
                try:
                    return int(float(match.group(1)))
                except ValueError:
                    continue

        # Known model sizes for common models without size in name
        known_sizes = {
            "llama3.2": 3,
            "llama3.1": 8,
            "mistral": 7,
            "gemma": 7,
            "phi-3": 3,
            "phi-4": 14,
        }

        for name, size in known_sizes.items():
            if name in model_lower:
                return size

        return 0  # Unknown

    def _check_model_suitability(self, agent_name: str):
        """Check if selected model is suitable for agent and show warning if not."""
        if agent_name not in self._model_suitability:
            return

        model = self.agent_models[agent_name].get()
        if not model or model == "Default":
            # Clear warning for default selection
            self._warning_labels[agent_name].config(text="")
            return

        size = self._estimate_model_size(model)
        if size == 0:
            # Couldn't determine size - no warning
            self._warning_labels[agent_name].config(text="")
            return

        suitability = self._model_suitability[agent_name]
        threshold = suitability["threshold"]
        warn_type = suitability["type"]

        show_warning = False
        if warn_type == "overkill" and size > threshold:
            show_warning = True
        elif warn_type == "underpowered" and size < threshold:
            show_warning = True

        if show_warning:
            self._warning_labels[agent_name].config(text=f"⚠️ {suitability['warning']}")
        else:
            self._warning_labels[agent_name].config(text="")

    def get_orchestrator_config(self) -> "OrchestratorConfig":
        """Build OrchestratorConfig from current settings.

        Starts with RECOMMENDED_AGENT_MODELS as baseline, then applies
        any user-specified overrides.
        """
        if not HAS_AGENT_CONFIG:
            return None

        llm_settings = self.llm_panel.get_settings()
        provider = llm_settings.get("provider", "ollama")
        base_url = llm_settings.get("base_url", "http://localhost:11434")

        # Start with optimized config based on available models
        # This applies RECOMMENDED_AGENT_MODELS automatically
        available_models = self.llm_panel.detected_models or []
        if available_models:
            config = create_optimized_config(
                available_models=available_models,
                provider=provider,
                base_url=base_url,
            )
            # Update default model to user's selection
            config.default_model = llm_settings.get("model", "llama3.2")
        else:
            # No models detected - fall back to simple config
            config = OrchestratorConfig(
                default_model=llm_settings.get("model", "llama3.2"),
                default_provider=provider,
                default_base_url=base_url,
            )

        # Apply user-specified per-agent overrides
        for agent_name, model_var in self.agent_models.items():
            model = model_var.get()
            if model and model != "Default":
                config.set_agent_config(agent_name, AgentConfig(
                    model=model,
                    provider=config.default_provider,
                    base_url=config.default_base_url,
                ))

        # Apply tuning knobs
        if PipelineTuningConfig is not None:
            config.tuning = PipelineTuningConfig(
                chapter_marker_chunk_chars=int(self.chapter_marker_chunk_chars.get()),
                chapter_marker_chunk_overlap_chars=int(self.chapter_marker_overlap_chars.get()),
                chapter_narrative_chunk_chars=int(self.chapter_narrative_chunk_chars.get()),
                chapter_narrative_chunk_overlap_chars=int(self.chapter_narrative_overlap_chars.get()),
                character_llm_chunk_chars=int(self.character_llm_chunk_chars.get()),
                character_mention_context_chars=int(self.character_mention_context_chars.get()),
                summary_chunk_words=int(self.summary_chunk_words.get()),
                summary_chunk_overlap_words=int(self.summary_chunk_overlap_words.get()),
            )

        return config

    def pack(self, **kwargs):
        """Allow panel to be packed like a regular widget."""
        self.outer_frame.pack(**kwargs)


class AudiobookPrepGUI:
    """Main desktop GUI application."""
    
    def __init__(self):
        if not HAS_TKINTER:
            raise ImportError("tkinter is required for desktop GUI")
        
        self.root = tk.Tk()
        self.root.title("Audiobook Prep")
        self.root.geometry("800x700")
        self.root.minsize(600, 400)
        
        # Variables
        self.input_file = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "output"))
        self.output_file = tk.StringVar()
        self.html_output = tk.StringVar()
        self.generate_html = tk.BooleanVar(value=True)
        self.wpm = tk.IntVar(value=150)
        self.use_llm = tk.BooleanVar(value=True)
        self.debug_logging = tk.BooleanVar(value=True)
        self.verbose_logging = tk.BooleanVar(value=True)

        self.analysis_result: Optional[AnalysisResult] = None
        self._last_run_dir: Optional[Path] = None  # Per-run output directory

        self._create_widgets()
        self._load_settings()  # Load persisted settings
        self._setup_auto_save()  # Setup automatic settings saving
        
    def _create_widgets(self):
        """Create GUI widgets."""
        # Create canvas with scrollbar for scrollable content
        self.canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)

        # Scrollable frame inside canvas
        main_frame = ttk.Frame(self.canvas, padding="10")

        # Configure scrolling
        main_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=main_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Pack scrollbar and canvas
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Make canvas window expand to canvas width
        def _configure_canvas_width(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)
        self.canvas.bind("<Configure>", _configure_canvas_width)

        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Linux mousewheel support (Button-4/5)
        def _on_mousewheel_linux(event):
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")
        self.canvas.bind_all("<Button-4>", _on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", _on_mousewheel_linux)

        # Title
        title_label = tk.Label(
            main_frame,
            text="Audiobook Prep",
            font=("Arial", 18, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Input file section
        input_frame = ttk.LabelFrame(main_frame, text="Input File", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(input_frame, text="Book file:").pack(anchor=tk.W)
        input_row = ttk.Frame(input_frame)
        input_row.pack(fill=tk.X, pady=5)
        
        ttk.Entry(input_row, textvariable=self.input_file, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(input_row, text="Browse...", command=self._browse_input).pack(side=tk.LEFT)
        
        # Output section
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="10")
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(output_frame, text="Output directory:").pack(anchor=tk.W)
        output_dir_row = ttk.Frame(output_frame)
        output_dir_row.pack(fill=tk.X, pady=5)
        
        ttk.Entry(output_dir_row, textvariable=self.output_dir, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(output_dir_row, text="Browse...", command=self._browse_output_dir).pack(side=tk.LEFT)

        # Note: Per-run directories are created automatically (e.g., output/book_20260107_143200/)
        ttk.Label(output_frame, text="Auto-increments when you select a new input file", font=("TkDefaultFont", 9, "italic")).pack(anchor=tk.W, pady=(5, 0))

        # HTML export option
        ttk.Checkbutton(
            output_frame,
            text="Generate HTML report",
            variable=self.generate_html,
        ).pack(anchor=tk.W, pady=(10, 0))
        
        # Options section
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.pack(fill=tk.X, pady=5)
        
        wpm_row = ttk.Frame(options_frame)
        wpm_row.pack(fill=tk.X, pady=5)
        ttk.Label(wpm_row, text="Words per minute:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Spinbox(wpm_row, from_=100, to=200, textvariable=self.wpm, width=10).pack(side=tk.LEFT)
        
        ttk.Checkbutton(
            options_frame,
            text="Use LLM refinement (recommended)",
            variable=self.use_llm
        ).pack(anchor=tk.W, pady=5)

        ttk.Checkbutton(
            options_frame,
            text="Enable LLM debug logging",
            variable=self.debug_logging,
            command=self._toggle_debug_logging
        ).pack(anchor=tk.W, pady=5)

        ttk.Checkbutton(
            options_frame,
            text="Show pipeline logs (chapter detection, character merging)",
            variable=self.verbose_logging,
            command=self._toggle_verbose_logging
        ).pack(anchor=tk.W, pady=5)

        # LLM Settings panel (collapsible)
        self.llm_panel = LLMSettingsPanel(main_frame)
        self.llm_panel.pack(fill=tk.X, pady=5)

        # System Profile panel (collapsible) - shows detected hardware and profile
        self.system_profile_panel = SystemProfilePanel(main_frame, self.llm_panel)
        self.system_profile_panel.pack(fill=tk.X, pady=5)

        # Agent Model Configuration panel (collapsible)
        self.agent_config_panel = AgentModelConfigPanel(main_frame, self.llm_panel)
        self.agent_config_panel.pack(fill=tk.X, pady=5)

        # Link system profile to agent config for auto-optimization
        self.system_profile_panel.set_agent_config_panel(self.agent_config_panel)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=20)
        
        self.analyze_button = ttk.Button(
            button_frame,
            text="Analyze Book",
            command=self._analyze,
            style="Accent.TButton"
        )
        self.analyze_button.pack(side=tk.LEFT, padx=5)
        
        self.view_results_button = ttk.Button(
            button_frame,
            text="View Results (TUI)",
            command=self._view_results,
            state=tk.DISABLED
        )
        self.view_results_button.pack(side=tk.LEFT, padx=5)
        
        self.open_html_button = ttk.Button(
            button_frame,
            text="Open HTML Report",
            command=self._open_html,
            state=tk.DISABLED
        )
        self.open_html_button.pack(side=tk.LEFT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.pack(fill=tk.X, pady=(10, 0))

    def _toggle_debug_logging(self):
        """Toggle LLM debug logging on/off."""
        from ..logging_config import set_llm_debug_enabled
        set_llm_debug_enabled(self.debug_logging.get())

    def _toggle_verbose_logging(self):
        """Toggle pipeline verbose logging on/off."""
        from ..logging_config import set_pipeline_logging_enabled
        set_pipeline_logging_enabled(self.verbose_logging.get())

    def _get_next_run_number(self, base_dir: Path, book_name: str) -> int:
        """Find the next available run number for a book.

        Scans existing directories matching pattern: bookname_NNN
        and returns the next available number.
        """
        if not base_dir.exists():
            return 1

        # Find all existing directories matching pattern: bookname_NNN
        import re
        pattern = re.compile(rf"^{re.escape(book_name)}_(\d+)$")

        max_num = 0
        for item in base_dir.iterdir():
            if item.is_dir():
                match = pattern.match(item.name)
                if match:
                    num = int(match.group(1))
                    max_num = max(max_num, num)

        return max_num + 1

    def _browse_input(self):
        """Browse for input file."""
        filename = filedialog.askopenfilename(
            title="Select Book File",
            filetypes=[
                ("All Supported", ("*.pdf", "*.epub", "*.docx", "*.txt", "*.md")),
                ("PDF", "*.pdf"),
                ("EPUB", "*.epub"),
                ("Word", "*.docx"),
                ("Text", ("*.txt", "*.md")),
                ("All Files", "*.*")
            ]
        )
        if filename:
            self.input_file.set(filename)

            # Auto-suggest output directory with incrementing number
            input_path = Path(filename)
            book_name = input_path.stem
            base_output = Path("output")
            next_num = self._get_next_run_number(base_output, book_name)
            suggested_path = base_output / f"{book_name}_{next_num:03d}"
            self.output_dir.set(str(suggested_path))
    
    def _browse_output_dir(self):
        """Browse for output directory."""
        dirname = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_dir.get()
        )
        if dirname:
            self.output_dir.set(dirname)

    def _analyze(self):
        """Start analysis in background thread."""
        if not self.input_file.get():
            messagebox.showerror("Error", "Please select an input file.")
            return
        
        input_path = Path(self.input_file.get())
        if not input_path.exists():
            messagebox.showerror("Error", f"File not found: {input_path}")
            return

        # Validate LLM settings if enabled
        if self.use_llm.get():
            llm_settings = self.llm_panel.get_settings()
            if not llm_settings.get("model"):
                messagebox.showerror(
                    "LLM Configuration Error",
                    "No model selected.\n\n"
                    "Please expand 'LLM Settings', select a provider, "
                    "and click 'Detect' to find available models."
                )
                return

        # Disable analyze button
        self.analyze_button.config(state=tk.DISABLED)
        self.status_var.set("Starting analysis...")
        
        # Show progress window
        progress = ProgressWindow(self.root)
        progress.progress_bar.start()
        
        # Run analysis in background thread
        thread = threading.Thread(
            target=self._run_analysis,
            args=(input_path, progress),
            daemon=True
        )
        thread.start()
        
        # Check thread completion
        self._check_analysis_thread(thread, progress)
    
    def _run_analysis(self, input_path: Path, progress: ProgressWindow):
        """Run analysis (called in background thread)."""
        try:
            if not HAS_ANALYZER:
                raise ImportError("Analyzer module not available")

            # Get LLM settings from panel
            llm_settings = self.llm_panel.get_settings() if self.use_llm.get() else {}

            # Get orchestrator config for per-agent model selection
            orchestrator_config = None
            if self.use_llm.get() and HAS_AGENT_CONFIG:
                orchestrator_config = self.agent_config_panel.get_orchestrator_config()

            analyzer = AudiobookAnalyzer(
                words_per_minute=self.wpm.get(),
                llm_refine=self.use_llm.get(),
                llm_model=llm_settings.get("model") or None,
                llm_base_url=llm_settings.get("base_url") or None,
                llm_provider=llm_settings.get("provider", "lm_studio"),
                llm_api_key=llm_settings.get("api_key"),
                llm_context_length=llm_settings.get("context_length", 32768),
                llm_prompts=llm_settings.get("prompts"),
                orchestrator_config=orchestrator_config,
                output_dir=Path(self.output_dir.get()),
            )

            # Assign metrics collector to progress window for enhanced tracking
            if hasattr(analyzer, '_metrics') and analyzer._metrics:
                progress.metrics = analyzer._metrics
                # Start polling now that metrics are available
                progress._poll_progress()

            # Capture print statements for progress updates
            import sys
            from io import StringIO
            
            class ProgressCapture:
                def __init__(self, progress_window):
                    self.progress = progress_window
                    self.buffer = StringIO()
                
                def write(self, text):
                    self.buffer.write(text)
                    # Update progress on key messages
                    if "📖 Ingesting" in text:
                        self.progress.update("Ingesting document...")
                    elif "🔧 Refining" in text:
                        self.progress.update("Refining text (may load word data)...")
                    elif "🔤 Loading word" in text:
                        self.progress.update("Loading word segmentation data...")
                    elif "📑 Detecting chapters" in text:
                        self.progress.update("Detecting chapters...")
                    elif "📑 Analyzing structure" in text:
                        self.progress.update("Analyzing structure...")
                    elif "👥 Extracting characters" in text:
                        self.progress.update("Extracting characters...")
                    elif "📝 Generating summaries" in text:
                        self.progress.update("Generating chapter summaries...")
                    elif "🗣️  Flagging pronunciations" in text:
                        self.progress.update("Flagging pronunciations...")
                    elif "🤖 Running LLM refinement" in text:
                        self.progress.update("Running LLM refinement...")
                    elif "Generating profile for" in text:
                        char_name = text.split("Generating profile for")[-1].strip()
                        self.progress.update(f"Generating profile for {char_name}...")
                    elif "✅ Analysis saved" in text:
                        self.progress.update("Saving results...")
                
                def flush(self):
                    pass
            
            progress_capture = ProgressCapture(progress)
            old_stdout = sys.stdout
            sys.stdout = progress_capture
            
            try:
                result = analyzer.analyze(input_path)
                self.analysis_result = result
            finally:
                sys.stdout = old_stdout
            
            # Use per-run directory created by analyzer
            if analyzer._last_run_dir:
                self._last_run_dir = analyzer._last_run_dir  # Store for later use
                json_path = analyzer._last_run_dir / "analysis.json"
                html_path = analyzer._last_run_dir / "report.html" if self.generate_html.get() else None
                progress.update(f"Output: {analyzer._last_run_dir}")
            else:
                # Fallback (shouldn't happen if output_dir was passed)
                output_dir = Path(self.output_dir.get())
                output_dir.mkdir(parents=True, exist_ok=True)
                json_path = output_dir / f"{input_path.stem}.analysis.json"
                html_path = output_dir / f"{input_path.stem}.html" if self.generate_html.get() else None

            # Save JSON
            analyzer.save_to_json(result, json_path)
            progress.update("Saving JSON...")

            # Save HTML if requested
            if html_path:
                try:
                    from ..export.html_report import export_html_report
                    export_html_report(
                        result,
                        html_path,
                        llm_model=analyzer.llm_model,
                        analysis_duration_seconds=analyzer._last_analysis_duration,
                    )
                    progress.update("Saving HTML...")
                except Exception as e:
                    import traceback
                    error_msg = str(e)
                    traceback.print_exc()  # Log to console for debugging
                    # Show error in GUI
                    self.root.after(0, lambda msg=error_msg: messagebox.showwarning(
                        "HTML Export Warning",
                        f"HTML report could not be generated:\n\n{msg[:300]}"
                    ))

            progress.update("Analysis complete!")

            # Show completion summary with final metrics
            if hasattr(analyzer, '_metrics') and analyzer._metrics:
                try:
                    final_snapshot = analyzer._metrics.get_progress_snapshot()
                    progress.show_completion_summary(final_snapshot)
                except Exception:
                    pass  # If summary fails, analysis still succeeded

        except Exception as e:
            progress.update(f"Error: {str(e)}")
            messagebox.showerror("Analysis Error", f"Analysis failed:\n{str(e)}")
        finally:
            progress.close()
            self.root.after(0, self._analysis_complete)
    
    def _check_analysis_thread(self, thread: threading.Thread, progress: ProgressWindow):
        """Check if analysis thread is complete."""
        if thread.is_alive():
            self.root.after(100, lambda: self._check_analysis_thread(thread, progress))
        else:
            # Thread finished, progress window will close itself
            pass
    
    def _analysis_complete(self):
        """Called when analysis completes."""
        self.analyze_button.config(state=tk.NORMAL)
        self.view_results_button.config(state=tk.NORMAL)
        if self.generate_html.get():
            self.open_html_button.config(state=tk.NORMAL)
        self.status_var.set("Analysis complete!")
    
    def _view_results(self):
        """Open TUI with results."""
        if not self.analysis_result:
            messagebox.showwarning("No Results", "Please run analysis first.")
            return
        
        if not HAS_TUI:
            messagebox.showerror("Error", "TUI module not available.")
            return
        
        # Run TUI in separate thread (it blocks)
        thread = threading.Thread(target=lambda: run_tui(self.analysis_result), daemon=True)
        thread.start()
    
    def _open_html(self):
        """Open HTML report in browser."""
        if not self.generate_html.get():
            messagebox.showwarning("No HTML", "HTML generation was not enabled.")
            return

        # Use per-run directory
        if not self._last_run_dir:
            messagebox.showwarning("No HTML", "Please run analysis first.")
            return

        html_path = self._last_run_dir / "report.html"
        if not html_path.exists():
            messagebox.showerror("Error", f"HTML file not found: {html_path}")
            return

        import webbrowser
        file_url = f"file://{html_path.absolute()}"
        webbrowser.open(file_url)

    def _get_settings_file(self) -> Path:
        """Get path to settings file."""
        # Use XDG_CONFIG_HOME if available, otherwise ~/.config
        config_dir = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
        settings_dir = config_dir / 'audiobook_prep'
        settings_dir.mkdir(parents=True, exist_ok=True)
        return settings_dir / 'gui_settings.json'

    def _save_settings(self):
        """Save current settings to file."""
        try:
            settings = {
                'output_dir': self.output_dir.get(),
                'generate_html': self.generate_html.get(),
                'wpm': self.wpm.get(),
                'use_llm': self.use_llm.get(),
                'llm_settings': self.llm_panel.get_settings(),
                'agent_models': {
                    agent_name: model_var.get()
                    for agent_name, model_var in self.agent_config_panel.agent_models.items()
                },
            }

            settings_file = self._get_settings_file()
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2, default=str)
        except Exception as e:
            # Don't crash GUI if settings save fails
            print(f"Warning: Failed to save settings: {e}")

    def _load_settings(self):
        """Load settings from file."""
        try:
            settings_file = self._get_settings_file()
            if not settings_file.exists():
                return  # No settings file yet

            with open(settings_file, 'r') as f:
                settings = json.load(f)

            # Restore basic settings
            if 'output_dir' in settings:
                self.output_dir.set(settings['output_dir'])
            if 'generate_html' in settings:
                self.generate_html.set(settings['generate_html'])
            if 'wpm' in settings:
                self.wpm.set(settings['wpm'])
            if 'use_llm' in settings:
                self.use_llm.set(settings['use_llm'])

            # Restore LLM settings
            if 'llm_settings' in settings:
                llm = settings['llm_settings']
                if 'provider' in llm:
                    self.llm_panel.provider.set(llm['provider'])
                    self.llm_panel._update_for_provider()
                if 'model' in llm:
                    self.llm_panel.model.set(llm['model'])
                if 'base_url' in llm:
                    self.llm_panel.base_url.set(llm['base_url'])
                if 'context_length' in llm:
                    self.llm_panel.context_length.set(llm['context_length'])
                if 'api_key' in llm and llm['api_key']:
                    self.llm_panel.api_key.set(llm['api_key'])

                # Detect models after loading settings
                if llm.get('provider') in ('ollama', 'lm_studio'):
                    self.root.after(500, self.llm_panel._detect_models)

            # Restore agent model selections
            if 'agent_models' in settings:
                for agent_name, model in settings['agent_models'].items():
                    if agent_name in self.agent_config_panel.agent_models:
                        self.agent_config_panel.agent_models[agent_name].set(model)

        except Exception as e:
            # Don't crash GUI if settings load fails
            print(f"Warning: Failed to load settings: {e}")

    def _on_setting_change(self, *args):
        """Called when any setting changes to save automatically."""
        self._save_settings()

    def _setup_auto_save(self):
        """Setup automatic saving when settings change."""
        # Add traces to main settings variables
        self.output_dir.trace_add('write', self._on_setting_change)
        self.generate_html.trace_add('write', self._on_setting_change)
        self.wpm.trace_add('write', self._on_setting_change)
        self.use_llm.trace_add('write', self._on_setting_change)

        # Add traces to LLM panel settings
        self.llm_panel.provider.trace_add('write', self._on_setting_change)
        self.llm_panel.model.trace_add('write', self._on_setting_change)
        self.llm_panel.base_url.trace_add('write', self._on_setting_change)
        self.llm_panel.context_length.trace_add('write', self._on_setting_change)

        # Add traces to agent model selections
        for model_var in self.agent_config_panel.agent_models.values():
            model_var.trace_add('write', self._on_setting_change)

    def run(self):
        """Start GUI main loop."""
        self.root.mainloop()


def main():
    """Launch desktop GUI."""
    if not HAS_TKINTER:
        print("Error: tkinter is not available.")
        print("\nTo install tkinter on Linux:")
        print("  sudo apt-get install python3-tk")
        print("\nOr on Ubuntu/Debian:")
        print("  sudo apt install python3-tk")
        print("\nAfter installation, try again.")
        return 1
    
    app = AudiobookPrepGUI()
    app.run()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

