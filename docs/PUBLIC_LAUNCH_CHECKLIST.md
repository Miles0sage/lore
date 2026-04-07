# Public Launch Checklist

Date: 2026-04-07
Owner: Lore team

## 1) Must Be True Before Publishing

1. `pip install lore-agents` works from a clean machine.
2. The benchmark article contains the correct public repository URL.
3. Public docs describe the OSS flow first: scaffold, audit, search, install.
4. Private/operator workflows are clearly marked as advanced.
5. CI tests run on pull requests.

## 2) Launch-Day Validation Commands

Run these from a clean shell in repository root:

```bash
python -m pip install --upgrade pip
pip install -e .
python -m lore.cli scaffold circuit_breaker >/tmp/cb.py
python -m lore.cli search "cost guard" --limit 3
python -m lore.cli audit . --max-files 40 --max-chars 120000
python -m pytest tests/ -q --tb=no
```

## 3) Public Narrative (Keep It Tight)

1. Lore is an AI agent reliability harness.
2. It adds four production controls quickly: circuit breaker, DLQ, cost guard, observability.
3. It audits existing codebases and suggests concrete fixes.
4. It works alongside existing frameworks.

## 4) Distribution Sequence

1. Publish benchmark article (DEV + Hashnode).
2. Publish HN post with scorecard in first comment.
3. Share 6-post thread with concrete findings and CTA.
4. Ask first 10 users to run audit and share findings.

## 5) Week-1 Metrics

1. Installs: target 100+.
2. Audits run: target 50+.
3. External repos with public findings: target 10+.
4. Design partner calls booked: target 3+.

## 6) Known Gating Risks

1. PyPI publication incomplete or delayed.
2. Docs drift back to private/internal features.
3. No external social proof collected in first week.

## 7) After Launch (Week 2-4)

1. Publish first 3 case studies with quantitative outcomes.
2. Add CI policy gate examples for common frameworks.
3. Introduce report tier for teams and hiring managers.
