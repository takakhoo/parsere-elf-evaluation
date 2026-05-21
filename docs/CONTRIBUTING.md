# Contributing notes

Quick reference for everyone working in this repo.

## What this repo is for

A working snapshot of the ParseRE paper while we finish the ACSAC 2026 submission. After submission this will become a reproducibility artifact and eventually a PR back to Ben's upstream ParseRE.

## Branches

`main` only for now. If we end up doing parallel work close to the deadline we can branch.

## Commit style

Imperative mood, lowercase first word, no trailing period in subject. Body is wrap-72 prose. Examples:

```
add ELF template byte literals to main.py
fix zero-division in uniquify step when rule has empty edge set
update Dockerfile to use python:3.13-bookworm base
```

No co-authors trailers in any commit ever. This is Taka's repo and Taka's commits.

## Where to add things

| Adding... | Goes in... |
|-----------|-----------|
| A new evaluation | `evaluations/<format>/` with its own README, corpus or script, output |
| A new harness | `harnesses/<format>_harness.c`, then update Dockerfile |
| Notes on related work | `references/` or directly in `paper/sections/related-work.tex` |
| A paper section | `paper/sections/<name>.tex`, then `\input` it from `main.tex` |
| Images and screenshots | `images/`, reference them from READMEs with relative paths |

## Don't commit

- Personal scratch directories
- Debug logs from QEMU (`/tmp/trace.log` style outputs)
- Half-finished paper drafts that contradict the merged version
- Anything in `~/Desktop/Cyber Research/` outside this repo
- API keys, GitHub tokens, OAuth secrets (we have none of these anyway)

## Build the paper PDF before pushing

If you edited `paper/`, build the PDF locally first to catch LaTeX errors:

```bash
cd paper
latexmk -pdf main.tex
```

If you do not have latexmk, drop the folder into Overleaf and let it compile.
