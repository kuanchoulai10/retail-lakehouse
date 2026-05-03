---
name: writing-docs
description: Use when writing or editing English-language technical documentation under `docs/` in the retail-lakehouse project — concept guides, how-it-works pages, deployment walkthroughs, configuration references, or troubleshooting pages.
---

# Writing retail-lakehouse Docs

## Overview

The project's documentation reads like an article, not a wiki dump. Every paragraph carries weight: opens with the subject, leads with the *why*, hands off to authoritative references. The reader should be able to skim and still walk away with the load-bearing claims.

## Core principles

1. **Open with the subject.** No "In this document we will..." preludes. The first sentence states what the page is about; the second states why the reader cares.
2. **Lead with *why* before *how*.** Configuration steps without motivation are noise. Establish the problem each section solves before showing commands.
3. **Bold the claim, not the keyword.** `**The query is more than just text — it's a fully-formed plan**` carries the load. `**query**` highlights a word for no reason. Reserve `**bold**` for whole phrases that, if read in isolation, summarise the section.
4. **Prefer prose to bullets.** Use bullets only when items are genuinely parallel and unordered. If they have different shapes or unequal weight, use prose.
5. **Numbered lists only for sequential steps** that must run in order.
6. **Tables for reference data** — configs, env vars, options, sync waves, comparison matrices. Never for narrative flow.
7. **Backtick anything that appears in code** — file paths, env vars, identifiers, commands, component names. `Pod`, `Lease`, `snapshot`, `GLAC_JOB_TYPE`.
8. **Don't translate technical terms.** Even in prose, `Pod` stays `Pod`, never "container instance". `Leader Election` stays `Leader Election`.
9. **Active voice.** "Trino fetches data from connectors" beats "data is fetched by Trino from connectors".
10. **Defend the system from misattribution** when the failure mode looks like a bug but isn't. "Spark Operator is not buggy — it's the correct response to API Server overload" reframes the reader's mental model and is often the highest-value sentence on the page.
11. **Cite authoritative sources.** Diagrams from books or upstream projects get a captioned link. Close every page with a `## References` section listing the canonical external docs you drew from.

## Structure templates

Pick the template that matches the page's intent. Don't blend them.

### Concept / How-it-works

For pages explaining what a system is and how it works internally.

```
# How X Works
(or: # X Architecture)

One-paragraph opener: what X is, what problem it solves, why it exists in this stack.

## Architecture Components
Definition-list per component (use the `: text` syntax).
Each component: 2-4 sentences covering responsibility, lifecycle, key interactions.

## Core Concepts
Prose explanation of the abstractions a reader needs to follow the rest of the page.
One H3 per concept. Bold the claim sentence within each.

## Behind the Scenes
The execution model, protocol flow, or data path. This is where Mermaid sequence diagrams earn their keep.

## References
- Canonical upstream docs
- Foundational papers or talks
```

### Deployment / Configuration

For pages walking through how to deploy or configure a component.

```
# Configure X / Deploy X

One-paragraph opener: the goal, the major areas you'll touch, the assumed starting state.

Bulleted breakdown of the areas, each linking to its H2 below.

## Configure {Area 1}
Open with *why* this area matters. Then the *how*: code blocks with `title=` and `hl_lines=` to anchor the reader's eye.

## Configure {Area 2}
...

## References
```

### Troubleshooting

For pages diagnosing a specific failure mode.

```
# {Failure mode as noun phrase}
(e.g. "Minikube Worker Node Cannot Pull External Container Images")

## Symptom
The exact output the reader will see — kubectl get pods rows, log snippets, error messages. Verbatim, not paraphrased.

## Root Cause
The *why*. Trace the chain from observable symptom to underlying mechanism. Use prose for causal chains; numbers and timing matter ("the 5-second HTTP timeout × 2 retries = the 10-second renewDeadline").

## This project's strategy
What we do about it, with the assumption that the reader will adopt the same approach.

## If you still need {alternative path}
Fallback options for cases the project's strategy doesn't cover.

## Quick reference
Single table summarising scenario → recommended action. Optional but valuable when there are 3+ paths.
```

## Diagrams

| Diagram | Use for |
|---|---|
| **Mermaid sequence** | Protocols, auth flows, request/response patterns |
| **Mermaid flowchart** | Simple state machines or decision trees with fewer than ~10 nodes |
| **Linked image** | Architecture diagrams from upstream projects (cited with caption) |
| **Prose** | Complex architectures, causal chains, anything that would need labelled callouts |

**Avoid ASCII art** with box-drawing characters (`│`, `▼`, `└─`). It's a shortcut for the writer that becomes a maintenance burden — diffs are noisy, alignment breaks under font changes, and it rarely communicates more than two sentences of prose would. The only exception is showing a literal directory tree (the output of `tree`).

**Avoid Mermaid for full-system architectures.** A 30-node Mermaid graph is harder to read than three paragraphs of prose. If your diagram needs scrolling, it's the wrong tool.

## Admonitions

Use sparingly. **At most one admonition per H2 section.** If you find yourself stacking two, the section is doing too much — split it or fold the points into prose.

| Type | Use for |
|---|---|
| `!!! warning` | Footguns; ways the reader will hurt themselves |
| `!!! info` | Clarification of a non-obvious behaviour |
| `!!! tip` | Non-obvious shortcut or recommended default |
| `!!! important` | Hard prerequisites that block everything else |

Don't use `!!! success` / `!!! failure` / `!!! danger` to decorate normal output blocks. Plain code blocks are fine.

## Voice

- **Address the reader as "you" only when personal action is implied** ("you'll need to copy these values"). Don't pepper "you" through descriptive prose.
- **Don't editorialise** ("this is amazing", "luckily"). State the fact.
- **Cut filler.** "It is important to note that" → cut. "Basically" → cut. "In order to" → "to".
- **Mix sentence lengths.** Short sentences land claims. Longer ones develop them.

## Code blocks

- Always set the language hint (` ```yaml`, ` ```bash`, ` ```sql`).
- Add `title="path/to/file"` when the snippet is from a real file in the repo. Readers want to know where to find it.
- Use `hl_lines="N M"` to point at the lines that matter when context is needed.
- Use `--8<--` includes for snippets that should track a real source file rather than be copy-pasted.
- Bare commands and one-off shell snippets don't need `title`.

## Common mistakes

| Mistake | Fix |
|---|---|
| Opening with "This document covers..." | Cut. Open with the subject directly. |
| Bold-everywhere | Demote keyword-bold to backticks. Keep `**bold**` for whole-claim emphasis. |
| ASCII flow diagrams | Replace with prose or a Mermaid sequence diagram. |
| Stacking admonitions | Fold into prose, or split the H2 section. |
| Generic table columns ("Item / Description") | Name columns by their semantic role ("Wave / Component / Dependency"). |
| Missing References section | Add it. Docs without external links feel orphaned. |
| Translating technical terms | `Pod`, `Lease`, `snapshot`, `Leader Election` — verbatim, always. |
| Mixing structure templates | Pick one (concept / deployment / troubleshooting). Don't blend. |

## Quick checklist before merging

- [ ] First sentence states the subject; second states why the reader cares
- [ ] Every H2 leads with *why*, not *how*
- [ ] No ASCII art (except literal `tree` output)
- [ ] At most one admonition per H2
- [ ] All file paths, env vars, identifiers in backticks
- [ ] Code blocks have language hints
- [ ] `## References` section at the bottom
- [ ] Page fits one of the three structure templates without blending
