# Paper Source

LaTeX source for the ACSAC 2026 submission. Drop this whole folder into Overleaf and set `main.tex` as the root document.

## File layout

```
paper/
├── main.tex          top-level, \input{}s every section
├── IEEEtran.cls      IEEE conference class (do not modify)
├── references.bib    bibliography
└── sections/
    ├── introduction.tex
    ├── background.tex
    ├── design.tex
    ├── implementation.tex
    ├── evaluation.tex
    ├── related-work.tex
    └── future-work.tex
```

## Compiling locally

If you have a TeX distribution installed:

```bash
cd paper
latexmk -pdf main.tex
```

Or step-by-step:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

The output is `main.pdf`. ACSAC 2026 limits the body to 11 pages excluding references and the optional 5-page appendix.

## Style notes

This paper follows the writing rules in [the repo root README](../README.md). A few things worth flagging:

- IEEE conference format, `compsoc` option.
- Anonymous submission. `\author{Anonymous}` in `main.tex`. Do not put real names in until ACSAC notification.
- The body cap is 11 pages. The current draft is around 9 pages with placeholders for HPACK and the Rishav-pending accuracy numbers.
- An Ethics section and an LLM Usage statement are mandatory per the ACSAC 2026 CFP. Both are in `future-work.tex`.

## Open items embedded in the .tex files

Search for `[BEN:` or `[RISHAV:` in any of the section files to find inline questions and missing-data markers. These render as italic in the compiled PDF so they are obvious during review. They will all be cleared before submission.

```bash
grep -n "\[BEN:\|\[RISHAV:\|TODO" sections/*.tex
```

## What still needs writing

- Fill in JSON and URI accuracy numbers once Rishav's labeled SVGs arrive
- Fill in HPACK evaluation results when Ben finishes the experiment
- Replace the Apache APR row in the cross-format table with real numbers
- Final proofread for em-dashes and "X is Y, not Z" patterns
- Page count check after all placeholders fill in
