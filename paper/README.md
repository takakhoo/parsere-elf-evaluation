# Paper draft

This directory contains an IEEE-style working draft titled **“Recovering Semantics from Unknown Binaries with Known Input Formats.”** It is not identified with a specific conference or submission cycle.

The draft is intentionally incomplete. The committed ELF evaluation includes manual label review; URI and JSON accuracy review remains pending; Apache APR and HPACK are planned but not implemented in this artifact. Generic `TODO` markers in the LaTeX source identify those gaps.

```text
paper/
├── main.tex          top-level document
├── main.pdf          compiled working draft
├── IEEEtran.cls      document class
├── references.bib    bibliography
├── figures/          TikZ sources and compiled figures
└── sections/         one LaTeX file per section
```

## Build

Using Tectonic:

```bash
cd paper
tectonic main.tex
```

Using a traditional TeX installation:

```bash
cd paper
latexmk -pdf main.tex
```

## Open items

List every unresolved item with:

```bash
grep -RIn '\[TODO:' . --include='*.tex'
```

The main open items are:

- manual TP/FP/FN review for the committed URI and JSON outputs;
- Apache APR and HPACK implementations and measurements;
- validation of the `-d in_asm` translation-log methodology against an execution-level trace;
- a public artifact/license decision and final author information; and
- final related-work, ethics, and reproducibility review.

## Figures

The four paper figures are maintained as TikZ sources:

- `motivating.tex`: URI input-difference example;
- `pipeline.tex`: end-to-end ParseRE pipeline;
- `elf-layout.tex`: fixed-layout ELF corpus; and
- `elf-cfg-fragment.tex`: selected ELF-labeled blocks from the committed output.

Regenerate them with:

```bash
cd paper/figures
tectonic motivating.tex pipeline.tex elf-layout.tex elf-cfg-fragment.tex
```

## Draft conventions

- Use anonymous author metadata until the authors decide how the draft will circulate.
- Do not report accuracy for an evaluation without a committed manual review.
- Do not describe planned formats as completed evaluations.
- Keep numerical claims synchronized with the committed templates and output files.
- Describe this repository as source-available research code, not an open-source release, until licensing is resolved.
