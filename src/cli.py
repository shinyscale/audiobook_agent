#!/usr/bin/env python3
"""
Audiobook Prep - Command Line Interface

Analyzes manuscripts for audiobook narration preparation.
"""

import argparse
import os
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description='Analyze manuscripts for audiobook narration preparation.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s analyze book.pdf
  %(prog)s analyze book.epub --output prep.json
  %(prog)s analyze manuscript.docx --wpm 160
        """
    )

    # Global options (before subcommands)
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable verbose LLM request/response logging to console and ~/.audiobook-prep/llm.log'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show pipeline diagnostic logging (chapter detection, character merging) to console and ~/.audiobook-prep/pipeline.log'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze a manuscript file'
    )
    analyze_parser.add_argument(
        'file',
        type=str,
        help='Path to manuscript file (PDF, DOCX, EPUB, or TXT)'
    )
    analyze_parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output JSON file path (default: <input>.analysis.json)'
    )
    analyze_parser.add_argument(
        '--wpm',
        type=int,
        default=150,
        help='Words per minute for duration estimates (default: 150)'
    )
    analyze_parser.add_argument(
        '--min-mentions',
        type=int,
        default=2,
        help='Minimum mentions to include a character (default: 2)'
    )
    analyze_parser.add_argument(
        '--keep-text',
        action='store_true',
        help='Include raw text in output (increases file size)'
    )
    analyze_parser.add_argument(
        '--no-llm',
        action='store_true',
        help='Skip LLM refinement step'
    )
    analyze_parser.add_argument(
        '--llm-model',
        type=str,
        default=None,
        help='Ollama model for LLM refinement (default: gpt-oss:120b)'
    )
    analyze_parser.add_argument(
        '--html',
        type=str,
        nargs='?',
        const=True,
        metavar='PATH',
        help='Export HTML report. If PATH is provided, use that path. Otherwise, save to output folder.'
    )
    analyze_parser.add_argument(
        '--tui',
        action='store_true',
        help='Open interactive TUI after analysis'
    )
    analyze_parser.add_argument(
        '--write-canonical-md',
        action='store_true',
        help='Write canonical markdown artifact alongside analysis output'
    )
    analyze_parser.add_argument(
        '--pdf-ocr',
        action='store_true',
        help='Enable OCR fallback for scanned/image-heavy PDFs (requires ocrmypdf or pytesseract)'
    )
    analyze_parser.add_argument(
        '--auto-optimize',
        action='store_true',
        help='Auto-detect hardware and use optimal settings for this machine'
    )
    analyze_parser.add_argument(
        '--profile',
        type=str,
        choices=['dgx', 'workstation', 'laptop', 'macbook_pro', 'macbook_air', 'cpu_only'],
        help='Use specific hardware profile (dgx, workstation, laptop, macbook_pro, macbook_air, cpu_only)'
    )

    # Specs command (show system specs)
    specs_parser = subparsers.add_parser(
        'specs',
        help='Display detected system specs and recommended settings'
    )

    # Summary command (quick view without full analysis)
    summary_parser = subparsers.add_parser(
        'summary',
        help='Show quick summary of a manuscript'
    )
    summary_parser.add_argument(
        'file',
        type=str,
        help='Path to manuscript file'
    )
    
    args = parser.parse_args()

    # Set up debug logging if requested via flag or environment variable
    debug_enabled = args.debug or os.environ.get('AUDIOBOOK_DEBUG', '').lower() in ('1', 'true', 'yes')
    if debug_enabled:
        from .logging_config import setup_llm_logging
        setup_llm_logging(enabled=True)

    # Set up verbose pipeline logging if requested
    verbose_enabled = args.verbose or os.environ.get('AUDIOBOOK_VERBOSE', '').lower() in ('1', 'true', 'yes')
    if verbose_enabled:
        from .logging_config import setup_pipeline_logging
        setup_pipeline_logging(level="INFO")

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == 'analyze':
        run_analyze(args)
    elif args.command == 'summary':
        run_summary(args)
    elif args.command == 'specs':
        run_specs()


def run_specs():
    """Display detected system specs and recommended settings."""
    from .system import detect_system_specs, detect_optimal_profile, format_specs_display

    print("\nDetecting system hardware...")
    specs = detect_system_specs()
    profile = detect_optimal_profile(specs)

    print("\n" + format_specs_display(specs, profile))
    print()


def run_analyze(args):
    """Run full analysis."""
    from .analyzer import AudiobookAnalyzer

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    # Handle auto-optimize and profile flags
    orchestrator_config = None
    if args.auto_optimize or args.profile:
        try:
            from .system import detect_system_specs, detect_optimal_profile, HARDWARE_PROFILES, format_specs_display
            from .agents.config import OrchestratorConfig, create_optimized_config

            if args.profile:
                # Use specified profile
                profile = HARDWARE_PROFILES.get(args.profile)
                if not profile:
                    print(f"Error: Unknown profile '{args.profile}'")
                    sys.exit(1)
                print(f"\n📊 Using hardware profile: {profile.name}")
                print(f"   {profile.description}")
            else:
                # Auto-detect and use optimal profile
                print("\n🔍 Detecting system hardware...")
                specs = detect_system_specs()
                profile = detect_optimal_profile(specs)
                print(format_specs_display(specs, profile))

            # Create config from profile
            orchestrator_config = create_optimized_config(
                available_models=[],  # Will be populated by analyzer
                provider="ollama",
                base_url="http://localhost:11434",
            )

            # Apply profile settings
            from .system.profiles import apply_profile_to_config
            apply_profile_to_config(profile, orchestrator_config)

            # Set context length from profile
            orchestrator_config.context_length = profile.context_length

            print(f"\n   Max model size: {profile.max_model_size_b}B")
            print(f"   Parallel workers: {profile.max_parallel_workers}")
            print(f"   Context length: {profile.context_length:,}")
            print()

        except ImportError as e:
            print(f"Warning: System detection not available ({e}), using defaults")
        except Exception as e:
            print(f"Warning: Failed to apply profile ({e}), using defaults")

    # Enable per-run output directories by default
    output_dir = Path('output')

    analyzer = AudiobookAnalyzer(
        words_per_minute=args.wpm,
        min_character_mentions=args.min_mentions,
        llm_refine=not args.no_llm,
        llm_model=args.llm_model,
        ocr_fallback=args.pdf_ocr,
        write_canonical_md=args.write_canonical_md,
        orchestrator_config=orchestrator_config,
        output_dir=output_dir,
    )

    try:
        result = analyzer.analyze(file_path)

        # Print summary
        print_analysis_summary(result)

        # Save JSON - use per-run directory if available, otherwise fallback to default
        if args.output:
            # User explicitly specified output path
            output_path = Path(args.output)
        elif analyzer._last_run_dir:
            # Per-run directory was created, save there
            output_path = analyzer._last_run_dir / "analysis.json"
        else:
            # Fallback to default behavior
            output_path = file_path.with_suffix('.analysis.json')
        analyzer.save_to_json(result, output_path)

        # Export HTML if requested
        if args.html:
            try:
                from .export.html_report import export_html_report
                # Determine HTML output path
                if args.html is True:
                    # Use per-run directory if available, otherwise default to output folder
                    if analyzer._last_run_dir:
                        html_path = analyzer._last_run_dir / "report.html"
                    else:
                        html_output_dir = Path('output')
                        html_output_dir.mkdir(exist_ok=True)
                        html_path = html_output_dir / file_path.with_suffix('.html').name
                else:
                    # Use provided path
                    html_path = Path(args.html)
                    # If it's a directory, create filename based on input
                    if html_path.is_dir() or (not html_path.suffix and not html_path.exists()):
                        html_path = Path(html_path) / file_path.with_suffix('.html').name

                export_html_report(
                    result,
                    html_path,
                    llm_model=analyzer.llm_model,
                    analysis_duration_seconds=analyzer._last_analysis_duration,
                )
            except ImportError:
                print("Warning: HTML export not available (missing src/export module)")
            except Exception as e:
                print(f"Warning: HTML export failed: {e}")

        # Launch TUI if requested
        if args.tui:
            try:
                from .gui.tui import run_tui
                run_tui(result)
            except ImportError:
                print("Warning: TUI not available (missing src/gui module or textual)")
            except Exception as e:
                print(f"Warning: TUI failed: {e}")

    except Exception as e:
        print(f"Error during analysis: {e}")
        sys.exit(1)


def run_summary(args):
    """Run quick summary."""
    from .ingestion import get_ingester
    
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    try:
        ingester = get_ingester(file_path)
        doc = ingester.extract(file_path)
        
        print(f"\n📖 {doc.title or file_path.name}")
        if doc.author:
            print(f"   by {doc.author}")
        print(f"\n   Format: {doc.source_format.upper()}")
        print(f"   Words: {doc.word_count:,}")
        print(f"   Characters: {doc.character_count:,}")
        
        if doc.chapters:
            print(f"   Chapters detected: {len(doc.chapters)}")
        
        # Estimate duration at 150 WPM
        duration_mins = doc.word_count / 150
        hours = int(duration_mins // 60)
        mins = int(duration_mins % 60)
        print(f"   Est. duration: {hours}h {mins}m (at 150 WPM)")
        
        if doc.extraction_warnings:
            print("\n   Warnings:")
            for w in doc.extraction_warnings:
                print(f"   ⚠️  {w}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def print_analysis_summary(result):
    """Print a human-readable summary of analysis results."""
    from .models import StructureType
    
    print("\n" + "=" * 60)
    print("ANALYSIS SUMMARY")
    print("=" * 60)
    
    # Book info
    print(f"\n📖 {result.metadata.title or 'Unknown Title'}")
    if result.metadata.author:
        print(f"   by {result.metadata.author}")
    
    # Duration
    hours = int(result.metadata.estimated_total_duration_minutes // 60)
    mins = int(result.metadata.estimated_total_duration_minutes % 60)
    print(f"\n⏱️  Estimated duration: {hours}h {mins}m")
    print(f"   ({result.metadata.total_word_count:,} words at {result.metadata.words_per_minute} WPM)")
    
    # Structure
    print(f"\n📑 Structure:")
    type_counts = {}
    for elem in result.structure:
        type_name = elem.type.value
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
    for type_name, count in sorted(type_counts.items()):
        print(f"   {type_name}: {count}")
    
    # Characters
    print(f"\n👥 Characters: {len(result.characters)}")
    for char in result.characters[:5]:  # Top 5
        aliases = f" (aka {', '.join(char.aliases[:2])})" if char.aliases else ""
        print(f"   • {char.canonical_name}{aliases} - {char.mention_count} mentions")
    if len(result.characters) > 5:
        print(f"   ... and {len(result.characters) - 5} more")
    
    # Pronunciations
    print(f"\n🗣️  Pronunciation flags: {len(result.pronunciations)}")
    by_reason = {}
    for p in result.pronunciations:
        reason = p.flag_reason.value
        by_reason[reason] = by_reason.get(reason, 0) + 1
    for reason, count in sorted(by_reason.items(), key=lambda x: -x[1]):
        print(f"   {reason}: {count}")
    
    # Warnings
    if result.warnings:
        print(f"\n⚠️  Warnings:")
        for w in result.warnings[:5]:
            print(f"   {w}")
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
