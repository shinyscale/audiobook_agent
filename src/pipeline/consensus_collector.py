"""
Global consensus vote collector.

Provides a simple way to collect consensus voting records from various
pipeline components without threading complex return values through
the call stack.

Usage:
    from src.pipeline.consensus_collector import consensus_collector

    # At start of analysis
    consensus_collector.reset()

    # In competitive voting code
    consensus_collector.record_vote(...)

    # At end of analysis
    log = consensus_collector.build_log()
"""

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class VoteRecord:
    """Record of a single consensus voting decision."""

    vote_type: str  # "alias", "boundary", "summary_event", "summary_character"
    subject: str  # What was being voted on
    context: Optional[str] = None  # Additional context
    votes: list = field(default_factory=list)  # Individual model votes
    vote_count: int = 0
    yes_count: int = 0
    threshold: float = 0.67
    outcome: str = "unknown"  # "accepted", "rejected", "skipped"
    reason: Optional[str] = None


class ConsensusCollector:
    """Thread-safe collector for consensus voting records."""

    def __init__(self):
        self._lock = threading.Lock()
        self._votes: list[VoteRecord] = []
        self._config = {
            "enabled": False,
            "mode": "none",
            "models": [],
            "stages": [],
        }

    def reset(self):
        """Clear all collected votes. Call at start of analysis."""
        with self._lock:
            self._votes = []
            self._config = {
                "enabled": False,
                "mode": "none",
                "models": [],
                "stages": [],
            }
            # Clear the live votes file
            try:
                votes_file = Path("output/VOTES.json")
                if votes_file.exists():
                    votes_file.unlink()
            except Exception:
                pass

    def configure(
        self,
        enabled: bool = False,
        mode: str = "none",
        models: Optional[list[str]] = None,
        stages: Optional[list[str]] = None,
    ):
        """Set consensus configuration."""
        with self._lock:
            self._config["enabled"] = enabled
            self._config["mode"] = mode
            self._config["models"] = models or []
            self._config["stages"] = stages or []

    def record_vote(
        self,
        vote_type: str,
        subject: str,
        votes: list[bool],
        threshold: float,
        outcome: str,
        context: Optional[str] = None,
        reason: Optional[str] = None,
    ):
        """Record a single voting decision."""
        with self._lock:
            vote = VoteRecord(
                vote_type=vote_type,
                subject=subject,
                context=context,
                votes=votes,
                vote_count=len(votes),
                yes_count=sum(votes) if votes else 0,
                threshold=threshold,
                outcome=outcome,
                reason=reason,
            )
            self._votes.append(vote)

            # Write to VOTES.json for live monitoring
            self._write_live_votes()

    def _write_live_votes(self):
        """Write votes to VOTES.json for live monitoring by oracle monitor."""
        try:
            votes_file = Path("output/VOTES.json")
            votes_file.parent.mkdir(parents=True, exist_ok=True)

            # Build vote list for JSON
            votes_data = []
            for vote in self._votes:  # Show all votes
                votes_data.append({
                    "vote_type": vote.vote_type,
                    "subject": vote.subject,
                    "context": vote.context,
                    "votes": vote.votes,
                    "vote_count": vote.vote_count,
                    "yes_count": vote.yes_count,
                    "threshold": vote.threshold,
                    "outcome": vote.outcome,
                    "reason": vote.reason,
                })

            with open(votes_file, "w") as f:
                json.dump({
                    "config": self._config,
                    "total_votes": len(self._votes),
                    "votes": votes_data,
                }, f, indent=2)
        except Exception:
            pass  # Don't let file writing break the pipeline

    def get_votes(self) -> list[VoteRecord]:
        """Get all collected votes."""
        with self._lock:
            return list(self._votes)

    def build_log(self) -> dict:
        """
        Build a ConsensusLog-compatible dictionary.

        Can be used to create models.ConsensusLog:
            from src.models import ConsensusLog
            log = ConsensusLog(**consensus_collector.build_log())
        """
        with self._lock:
            alias_votes = []
            boundary_votes = []
            summary_votes = []

            for vote in self._votes:
                vote_dict = {
                    "vote_type": vote.vote_type,
                    "subject": vote.subject,
                    "context": vote.context,
                    "votes": vote.votes,
                    "vote_count": vote.vote_count,
                    "yes_count": vote.yes_count,
                    "threshold": vote.threshold,
                    "outcome": vote.outcome,
                    "reason": vote.reason,
                }

                if vote.vote_type == "alias":
                    alias_votes.append(vote_dict)
                elif vote.vote_type == "boundary":
                    boundary_votes.append(vote_dict)
                else:  # summary_merge, summary_event, etc.
                    summary_votes.append(vote_dict)

            accepted = sum(1 for v in self._votes if v.outcome == "accepted")
            rejected = sum(1 for v in self._votes if v.outcome == "rejected")

            return {
                "enabled": self._config["enabled"],
                "mode": self._config["mode"],
                "models": self._config["models"],
                "stages": self._config["stages"],
                "alias_votes": alias_votes,
                "boundary_votes": boundary_votes,
                "summary_votes": summary_votes,
                "total_votes": len(self._votes),
                "accepted_count": accepted,
                "rejected_count": rejected,
            }


# Global singleton instance
consensus_collector = ConsensusCollector()
