# Related Work, Linked

The paper's related-work section is in [`../paper/sections/related-work.tex`](../paper/sections/related-work.tex). This folder is a casual companion: links, short notes on each cited paper, why we cite it.

## The closest cousins

### Tenet (Markus Gaasedelen, 2021)
[https://github.com/gaasedelen/tenet](https://github.com/gaasedelen/tenet)

IDA Pro plugin that highlights basic blocks differing between execution traces. Two-input differential analysis, no input-side labels. ParseRE generalizes this to N inputs with grammar attribution.

### Lighthouse (Markus Gaasedelen, 2017)
[https://github.com/gaasedelen/lighthouse](https://github.com/gaasedelen/lighthouse)

Coverage exploration in IDA. Same author, same niche, less differential. Worth citing in the same paragraph as Tenet.

### PolyFile / PolyTracker (Trail of Bits)
[https://github.com/trailofbits/polyfile](https://github.com/trailofbits/polyfile)
[https://github.com/trailofbits/polytracker](https://github.com/trailofbits/polytracker)

The "annotate the input" tools. PolyFile parses a file and tells you which byte ranges are which structures. PolyTracker tracks data flow through a program at the LLVM IR level and produces a graph mapping input bytes to operations.

The methodological line we walk away from: PolyTracker needs LLVM instrumentation. That requires source code. ParseRE works on the binary alone, which is the actual reverse-engineering scenario.

## Grammar recovery (the inverse problem)

These tools answer "what does this binary eat?" given only the binary. ParseRE answers "given that this binary eats X, where is X handled?" The two problems are sequential, not competing.

### Tupni (Microsoft Research, CCS 2008)
[https://www.microsoft.com/en-us/research/publication/tupni-automatic-reverse-engineering-of-input-formats/](https://www.microsoft.com/en-us/research/publication/tupni-automatic-reverse-engineering-of-input-formats/)

Dynamic analysis to infer input formats from observed program execution.

### Polyglot (CMU, CCS 2007)
[https://dl.acm.org/doi/10.1145/1315245.1315276](https://dl.acm.org/doi/10.1145/1315245.1315276)

Extracts protocol message formats via dynamic binary analysis.

### AUTOGRAM (Höschele and Zeller, ASE 2016)
Mining context-free input grammars by observing what a program rejects vs. accepts. Source code dependent.

### Gopinath et al. (2020)
"Mining input grammars from dynamic control flow." Closer in spirit to ParseRE in that it uses control flow, but for grammar inference, not label transfer.

### Prospex (2009)
Protocol state machine recovery from network traces.

## Differential testing for parsers

### HTTP Garden (Ben Kallus et al., 2024)
The paper we are *not* citing because of dual-blind review. Ben's other paper at the same submission deadline. Cite in camera-ready.

### T-Reqs (Jabiyev et al., CCS 2021)
Differential testing of HTTP parsers. Same family of techniques as HTTP Garden, different focus.

### ParDiff (Zheng et al., 2024)
Static differential analysis of protocol parsers. Complementary to ParseRE: ParDiff finds disagreement between parsers, ParseRE could then localize where the disagreement lives.

## How to position ParseRE against all of this

Ben's framing from the May 19 transcript:

> "It's crucial that reviewers not confuse these two related but not the same problems."

The two problems being:
1. Grammar recovery (what does this binary eat?). Existing work.
2. Label transfer (where does it eat the thing we know it eats?). ParseRE.

The related-work section in the paper has three subsections corresponding to the three lines of prior work, and explicitly positions ParseRE against each.

## Other references worth knowing about

- angr (Shoshitaishvili et al., S&P 2016) for the SoK on binary analysis, and as a model for how to write a tool paper.
- KLEE (Cadar et al., OSDI 2008) for the canonical symbolic execution paper.
- BAP (Brumley et al., CAV 2011) for the binary analysis platform line of work.
- Chomsky 1956 for the language hierarchy citation we use in the intro.

The full BibTeX with the exact entries we cite is in [`../paper/references.bib`](../paper/references.bib).
