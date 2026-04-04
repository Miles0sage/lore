---
backlinks: []
concepts:
- claude code
- notebooklm
- hook framework
- skill system
- mcp server
- token cost hygiene
- semantic code intelligence
- subagents
- claude code action
confidence: medium
created: '2026-04-04'
domain: ai-agents
id: claude-code-notebooklm-source-pack-2026
sources:
- https://docs.anthropic.com/en/docs/claude-code/hooks
- https://docs.anthropic.com/en/docs/claude-code/overview
- https://github.com/anthropics/claude-code-action
- https://github.com/obra/superpowers
- https://github.com/ryoppippi/ccusage
- https://github.com/alirezarezvani/claude-skills
- https://github.com/oraios/serena
- https://github.com/danielrosehill/Claude-Code-MCP-List
- https://support.google.com/notebooklm/answer/16206866?hl=en
status: published
title: Claude Code NotebookLM Source Pack 2026
updated: '2026-04-04'
---

# Claude Code NotebookLM Source Pack 2026

*Sources: official docs + GitHub repos + NotebookLM help | Date: 2026-04-04*

---

## Purpose

This article is a **clean source pack** for feeding NotebookLM with current, high-signal material about Claude Code and the ecosystem built on top of it.

The main rule is simple: prefer **official Anthropic docs and real GitHub repos** over low-signal comparison blogs.

---

## Best First Sources

### 1. Anthropic official docs

- **Claude Code hooks reference**  
  Best source for lifecycle events, hook configuration, session start/end hooks, and tool matchers.

- **Claude Code overview**  
  Best primary source for the product surface itself before looking at community add-ons.

### 2. High-signal GitHub repos

- **`anthropics/claude-code-action`**  
  Shows Claude Code moving into CI and automation workflows, not just local terminal use.

- **`obra/superpowers`**  
  The clearest example of Claude Code becoming a workflow system. The important signal is not just stars; it is that users built reusable planning, debugging, TDD, and parallel-agent methods on top of Claude Code.

- **`ryoppippi/ccusage`**  
  Proof that token-cost hygiene became important enough to justify a dedicated analytics tool.

- **`alirezarezvani/claude-skills`**  
  Strong signal that skills are a real extension layer, not a niche trick.

- **`oraios/serena`**  
  High-value semantic code intelligence via MCP and LSP-style navigation.

- **`danielrosehill/Claude-Code-MCP-List`**  
  Small but practical discovery layer for MCP tooling around Claude Code.

---

## What People Built On Top Of Claude Code

The ecosystem clusters around six extension surfaces:

### Hooks

Official docs show hooks around tool use, prompt submission, session lifecycle, compaction, and subagent stop events. That makes hooks one of the most important control surfaces for:

- safety checks
- formatting
- test enforcement
- notifications
- session restore

### Skills

Skills turned Claude Code from a single agent into a reusable workflow runtime. The best-known pattern is not “one better prompt”; it is packaging repeatable operational methods like planning, code review, TDD, and debugging.

### MCP toolchains

MCP is how Claude Code gets live external capabilities. The most important practical use cases are:

- semantic code navigation
- documentation retrieval
- memory
- browser or system tools
- database and cloud access

### Cost tracking

The existence of tools like `ccusage` is a strong ecosystem signal: as adoption grew, users needed operational visibility, not just better completions.

### Semantic code intelligence

Projects like `serena` matter because they change Claude Code from text-pattern editing into symbol-aware navigation and refactoring support.

### CI / automation

The GitHub Action layer matters because it shows Claude Code escaping the terminal and becoming part of PR, review, and workflow automation.

---

## Why This Matters For Research

If you ask NotebookLM only “what is Claude Code,” you get a shallow answer. If you give it the sources above, it can answer the more useful question:

**What is the actual shape of the Claude Code ecosystem, and which extensions have real adoption gravity?**

The recurring answers are:

- hooks for control
- skills for reusable workflows
- MCP for tool access
- observability for cost and trust
- semantic code tooling for scale

---

## NotebookLM Limits That Matter

Google’s help docs state that standard NotebookLM supports:

- up to **100 notebooks**
- up to **50 sources per notebook**
- up to **500K words per source**

That means you do **not** need to flood it with weak sources. A better strategy is to load 8-12 strong ones first, then add only the gaps.

---

## Recommended Ingestion Order

1. Claude Code overview
2. Claude Code hooks docs
3. `anthropics/claude-code-action`
4. `obra/superpowers`
5. `ryoppippi/ccusage`
6. `alirezarezvani/claude-skills`
7. `oraios/serena`
8. `danielrosehill/Claude-Code-MCP-List`

This order works because it moves from:

- product surface
- extension mechanics
- what people actually built

---

## Best NotebookLM Questions

Use short, sequential questions rather than one giant prompt.

Recommended sequence:

1. What extension surfaces around Claude Code appear repeatedly across the official docs and GitHub ecosystem?
2. Which ecosystem projects look like durable infrastructure rather than hype?
3. What do the strongest repos suggest about where Claude Code users feel the product is incomplete?
4. Which patterns should a competing open coding agent copy, and which should it ignore?
5. What are the most defensible product wedges against Claude Code based on this source set?

## Key Concepts
[[Claude Code Ecosystem — What People Have Built]] [[claude code]] [[NotebookLM]] [[hook framework]] [[skill system]] [[MCP server]] [[token cost hygiene]] [[semantic code intelligence]] [[subagents]] [[claude code action]]

## Sources
- Anthropic Claude Code hooks docs — https://docs.anthropic.com/en/docs/claude-code/hooks
- Anthropic Claude Code overview — https://docs.anthropic.com/en/docs/claude-code/overview
- GitHub: anthropics/claude-code-action — https://github.com/anthropics/claude-code-action
- GitHub: obra/superpowers — https://github.com/obra/superpowers
- GitHub: ryoppippi/ccusage — https://github.com/ryoppippi/ccusage
- GitHub: alirezarezvani/claude-skills — https://github.com/alirezarezvani/claude-skills
- GitHub: oraios/serena — https://github.com/oraios/serena
- GitHub: danielrosehill/Claude-Code-MCP-List — https://github.com/danielrosehill/Claude-Code-MCP-List
- Google NotebookLM Help — https://support.google.com/notebooklm/answer/16206866?hl=en
