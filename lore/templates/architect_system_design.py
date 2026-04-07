# LORE SCAFFOLD: architect_system_design
"""
Architect System Design — The Architect, Designer of Systems

Architecture decision records (ADRs) and system design review. The Architect
sees the whole before building any part. Each decision is recorded so future
agents inherit the wisdom of past choices.

Usage:
    review = ArchitectureReview()
    review.record_decision(ADR(title="Use PostgreSQL", context="Need ACID + JSON",
                               decision="PostgreSQL 16", consequences="Hosting cost higher"))
    issues = review.check_constraints(proposed_changes)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ADR:
    """Architecture Decision Record — immutable."""
    title: str
    context: str
    decision: str
    consequences: str
    status: str = "accepted"  # proposed | accepted | deprecated | superseded
    timestamp: float = field(default_factory=time.time)
    superseded_by: str = ""


@dataclass(frozen=True)
class DesignConstraint:
    """A constraint the architecture must satisfy."""
    name: str
    description: str
    check_fn_name: str = ""  # Name of function to validate
    severity: str = "high"  # low | medium | high | critical


@dataclass(frozen=True)
class ConstraintViolation:
    """Immutable record of a constraint violation."""
    constraint: str
    description: str
    severity: str
    suggested_fix: str = ""


class ArchitectureReview:
    """Maintains ADRs and validates proposed changes against constraints."""

    def __init__(self):
        self._decisions: list[ADR] = []
        self._constraints: list[DesignConstraint] = []

    def record_decision(self, adr: ADR) -> None:
        """Record a new architecture decision."""
        self._decisions = [*self._decisions, adr]

    def supersede_decision(self, old_title: str, new_adr: ADR) -> None:
        """Mark an old decision as superseded and record the new one."""
        updated = []
        for d in self._decisions:
            if d.title == old_title:
                updated.append(ADR(
                    title=d.title, context=d.context, decision=d.decision,
                    consequences=d.consequences, status="superseded",
                    timestamp=d.timestamp, superseded_by=new_adr.title,
                ))
            else:
                updated.append(d)
        self._decisions = updated
        self._decisions = [*self._decisions, new_adr]

    def add_constraint(self, constraint: DesignConstraint) -> None:
        """Add a design constraint."""
        self._constraints = [*self._constraints, constraint]

    def check_constraints(self, proposed_changes: dict) -> list[ConstraintViolation]:
        """Check proposed changes against all constraints.

        Override with domain-specific validation logic.
        """
        violations: list[ConstraintViolation] = []

        for constraint in self._constraints:
            # Example: check if changes violate naming conventions
            if constraint.name == "no_mutable_state" and proposed_changes.get("uses_mutation"):
                violations.append(ConstraintViolation(
                    constraint=constraint.name,
                    description="Proposed changes use mutable state",
                    severity=constraint.severity,
                    suggested_fix="Use immutable dataclasses or frozen dicts",
                ))

        return violations

    def propose_changes(self, title: str, description: str, changes: dict) -> dict:
        """Propose a change and validate it against constraints."""
        violations = self.check_constraints(changes)
        approved = all(v.severity not in ("critical", "high") for v in violations)

        return {
            "title": title,
            "description": description,
            "violations": [
                {"constraint": v.constraint, "severity": v.severity, "fix": v.suggested_fix}
                for v in violations
            ],
            "approved": approved,
            "active_decisions": len([d for d in self._decisions if d.status == "accepted"]),
        }

    def list_decisions(self, status: str | None = None) -> list[dict]:
        """List all ADRs, optionally filtered by status."""
        decisions = self._decisions
        if status:
            decisions = [d for d in decisions if d.status == status]
        return [
            {"title": d.title, "decision": d.decision, "status": d.status, "superseded_by": d.superseded_by}
            for d in decisions
        ]
