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

try:
    from ..analyzer import AudiobookAnalyzer
    from ..models import AnalysisResult
    HAS_ANALYZER = True
except ImportError:
    HAS_ANALYZER = False

try:
    from ..llm.config import (
        LLMProvider,
        DEFAULT_URLS,
        detect_available_models,
        detect_context_length,
        test_connection,
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


class ProgressWindow:
    """Window showing analysis progress."""
    
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Analyzing...")
        self.window.geometry("600x200")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center on parent
        self.window.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 300
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 100
        self.window.geometry(f"+{x}+{y}")
        
        # Progress bar
        self.progress_var = tk.StringVar(value="Initializing...")
        self.progress_label = tk.Label(
            self.window,
            textvariable=self.progress_var,
            font=("Arial", 10),
            wraplength=550
        )
        self.progress_label.pack(pady=20, padx=20)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            self.window,
            mode='indeterminate',
            length=550
        )
        self.progress_bar.pack(pady=10, padx=20)
        
        # Cancel button
        self.cancel_button = tk.Button(
            self.window,
            text="Cancel",
            command=self.cancel,
            state=tk.DISABLED  # For now, don't allow cancel
        )
        self.cancel_button.pack(pady=10)
        
        self.cancelled = False
        
    def cancel(self):
        """Cancel analysis."""
        self.cancelled = True
        self.window.destroy()
    
    def update(self, message: str):
        """Update progress message."""
        self.progress_var.set(message)
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
        self.provider = tk.StringVar(value="lm_studio")
        self.model = tk.StringVar()
        self.base_url = tk.StringVar()
        self.api_key = tk.StringVar()
        self.context_length = tk.IntVar(value=32768)
        self.detected_models: list[str] = []
        self.custom_prompts: Optional["PromptConfig"] = None  # User-customized prompts

        self._create_widgets()
        self._update_for_provider()

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

        self.detect_models_button = ttk.Button(
            model_row,
            text="Detect",
            command=self._detect_models,
            width=8
        )
        self.detect_models_button.pack(side=tk.LEFT, padx=2)

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


class AudiobookPrepGUI:
    """Main desktop GUI application."""
    
    def __init__(self):
        if not HAS_TKINTER:
            raise ImportError("tkinter is required for desktop GUI")
        
        self.root = tk.Tk()
        self.root.title("Audiobook Prep")
        self.root.geometry("800x600")
        
        # Variables
        self.input_file = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "output"))
        self.output_file = tk.StringVar()
        self.html_output = tk.StringVar()
        self.generate_html = tk.BooleanVar(value=True)
        self.wpm = tk.IntVar(value=150)
        self.use_llm = tk.BooleanVar(value=True)
        
        self.analysis_result: Optional[AnalysisResult] = None
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Create GUI widgets."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
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
        
        ttk.Label(output_frame, text="JSON filename (optional, auto-generated if empty):").pack(anchor=tk.W, pady=(10, 0))
        ttk.Entry(output_frame, textvariable=self.output_file, width=50).pack(anchor=tk.W, pady=5)

        # HTML export option
        html_row = ttk.Frame(output_frame)
        html_row.pack(fill=tk.X, pady=(10, 0))

        ttk.Checkbutton(
            html_row,
            text="Generate HTML report",
            variable=self.generate_html,
            command=self._toggle_html_entry
        ).pack(side=tk.LEFT)

        self.html_entry_frame = ttk.Frame(output_frame)
        self.html_entry_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.html_entry_frame, text="HTML filename:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(self.html_entry_frame, textvariable=self.html_output, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
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

        # LLM Settings panel (collapsible)
        self.llm_panel = LLMSettingsPanel(main_frame)
        self.llm_panel.pack(fill=tk.X, pady=5)

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
            # Auto-suggest output filename
            if not self.output_file.get():
                input_path = Path(filename)
                self.output_file.set(f"{input_path.stem}.analysis.json")
                if not self.html_output.get():
                    self.html_output.set(f"{input_path.stem}.html")
    
    def _browse_output_dir(self):
        """Browse for output directory."""
        dirname = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_dir.get()
        )
        if dirname:
            self.output_dir.set(dirname)

    def _toggle_html_entry(self):
        """Show/hide HTML filename entry based on checkbox."""
        if self.generate_html.get():
            self.html_entry_frame.pack(fill=tk.X, pady=5)
            # Auto-generate filename if empty and input file is set
            if not self.html_output.get() and self.input_file.get():
                input_path = Path(self.input_file.get())
                self.html_output.set(f"{input_path.stem}.html")
        else:
            self.html_entry_frame.pack_forget()

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

            analyzer = AudiobookAnalyzer(
                words_per_minute=self.wpm.get(),
                llm_refine=self.use_llm.get(),
                llm_model=llm_settings.get("model") or None,
                llm_base_url=llm_settings.get("base_url") or None,
                llm_provider=llm_settings.get("provider", "lm_studio"),
                llm_api_key=llm_settings.get("api_key"),
                llm_context_length=llm_settings.get("context_length", 32768),
                llm_prompts=llm_settings.get("prompts"),
            )
            
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
                    elif "📑 Analyzing structure" in text:
                        self.progress.update("Analyzing structure...")
                    elif "👥 Extracting characters" in text:
                        self.progress.update("Extracting characters...")
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
            
            # Determine output paths
            output_dir = Path(self.output_dir.get())
            output_dir.mkdir(parents=True, exist_ok=True)
            
            json_filename = self.output_file.get() or f"{input_path.stem}.analysis.json"
            json_path = output_dir / json_filename
            
            # Determine HTML path if generation is enabled
            html_path = None
            if self.generate_html.get():
                html_filename = self.html_output.get() or f"{input_path.stem}.html"
                html_path = output_dir / html_filename

            # Save JSON
            analyzer.analyze_to_json(input_path, json_path)
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
                    print(f"Warning: HTML export failed: {e}")
            
            progress.update("Analysis complete!")
            
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

        # Get HTML filename (use auto-generated name if empty)
        html_filename = self.html_output.get()
        if not html_filename and self.input_file.get():
            html_filename = f"{Path(self.input_file.get()).stem}.html"

        if not html_filename:
            messagebox.showwarning("No HTML", "No HTML file was generated.")
            return

        html_path = Path(self.output_dir.get()) / html_filename
        if not html_path.exists():
            messagebox.showerror("Error", f"HTML file not found: {html_path}")
            return
        
        import webbrowser
        import urllib.parse
        file_url = f"file://{html_path.absolute()}"
        webbrowser.open(file_url)
    
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

