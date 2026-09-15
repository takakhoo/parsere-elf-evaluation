# Contributing notes

## What this repo is for

A working snapshot of a ParseRE paper draft and its current reproducibility artifact. The local implementation changes may eventually be separated into an upstream contribution after licensing and contribution requirements are clarified.

## Branch policy

Use short-lived branches for independent changes and keep `main` in a buildable state.

## Commit policy

Imperative mood, lowercase first word, no trailing period. Examples:

```
add ELF template byte literals to main.py
fix zero-division in uniquify step when rule has empty edge set
update Dockerfile to use python:3.13-bookworm base
```

Use co-author trailers only when they accurately reflect authorship and all named contributors agree.

## Where things go

| Adding | Folder |
|--------|--------|
| New evaluation | `evaluations/<format>/` with README, corpus or script, output |
| New harness | `harnesses/<format>_harness.c`, then update Dockerfile |
| Related work | `references/` or `paper/sections/related-work.tex` |
| Paper section | `paper/sections/<name>.tex`, then `\input` from `main.tex` |
| Images and screenshots | `images/`, reference from READMEs with relative paths |

## Don't commit

- Personal scratch directories
- Debug logs from QEMU
- Half-finished paper drafts that contradict the merged version
- Anything outside this repo
- Secrets or credentials

## Build before pushing

After editing `paper/`, build locally to catch LaTeX errors:

```bash
cd paper
tectonic main.tex
```

If Tectonic is unavailable, upload the `paper/` folder to Overleaf and compile `main.tex` there.
