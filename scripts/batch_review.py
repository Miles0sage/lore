#!/usr/bin/env python3
"""
Batch review and publish all high-priority proposals in the raw queue.

Usage:
    python3 /root/lore/scripts/batch_review.py [--dry-run] [--reviewer NAME]

Approves all proposals with publish_recommendation=review_now and
priority_score >= MIN_PRIORITY, then publishes them to wiki.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make lore importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lore import proposals, publisher, routing

MIN_PRIORITY = 0.60
AUTO_REVIEWER = "lore-batch-review"


def run(dry_run: bool = False, reviewer: str = AUTO_REVIEWER, min_priority: float = MIN_PRIORITY):
    queue = proposals.list_proposals(limit=100)
    candidates = [
        p for p in queue
        if p["publish_recommendation"] in {"review_now"}
        and float(p["priority_score"]) >= min_priority
        and p["status"] in {"proposed", "in_review"}
    ]

    if not candidates:
        print("No review_now proposals found.")
        return

    print(f"Found {len(candidates)} candidates (min_priority={min_priority}):")
    for p in candidates:
        print(f"  [{p['priority_score']:.2f}] {p['id'][:50]} — {p['title'][:60]}")

    if dry_run:
        print("\n[dry-run] No changes made.")
        return

    approved, published, failed = [], [], []

    for p in candidates:
        pid = p["id"]
        # Step 1: approve
        try:
            proposals.review_proposal(pid, "approved", reviewer=reviewer, notes="batch auto-approved")
            approved.append(pid)
            print(f"  ✓ approved: {pid}")
        except Exception as e:
            failed.append((pid, f"approve: {e}"))
            print(f"  ✗ approve failed: {pid} — {e}")
            continue

        # Step 2: publish
        try:
            result = publisher.publish_proposal(pid, reviewer=reviewer, notes="batch auto-published")
            published.append(result["article_id"])
            print(f"  ✓ published: {result['article_id']} → {result['article_path']}")
            routing.log_router_event(
                task_type="publish",
                model="gpt-5.4",
                status="ok",
                description=f"batch published: {result['article_id']}",
                accepted=True,
            )
        except Exception as e:
            failed.append((pid, f"publish: {e}"))
            print(f"  ✗ publish failed: {pid} — {e}")

    print(f"\nDone: {len(approved)} approved, {len(published)} published, {len(failed)} failed")
    if failed:
        print("Failures:")
        for pid, reason in failed:
            print(f"  {pid}: {reason}")

    return {"approved": approved, "published": published, "failed": failed}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reviewer", default=AUTO_REVIEWER)
    parser.add_argument("--min-priority", type=float, default=MIN_PRIORITY)
    args = parser.parse_args()
    run(dry_run=args.dry_run, reviewer=args.reviewer, min_priority=args.min_priority)
