# JSON Evaluation (json-c)

Target: [json-c](https://github.com/json-c/json-c), commit `89485680314df3b4dfb2aaed14f89d212d57c119`.

Entry point: `json_tokener_parse(input)`.

The JSON template was defined by Ben before this work started. The whole evaluation is reproducible from this repo.

## Headline numbers

| Metric | Value |
|--------|-------|
| Template instantiations | 27 |
| Pairwise comparisons | 729 |
| CFG nodes after cleanup | 464 |
| CFG edges | 400 |
| Labeled basic blocks | 294 (63.4% of graph) |
| Productions used | 6 |

## Label distribution

| Production | Labeled BBs | Fraction of labels |
|-----------|------------:|-------------------:|
| number    | 110 | 37.4% |
| object-element | 77 | 26.2% |
| string    | 39 | 13.3% |
| array     | 36 | 12.2% |
| boolean   | 24 | 8.2% |
| nan       | 9  | 3.1% |

The dominance of `number` reflects the complexity of C-level numeric parsing: sign handling, decimal point, exponent notation (`e`/`E`), overflow checks, `strtod` wrappers. Every step is a separate basic block.

`nan` is small because its parsing path is a three-character string comparison.

## TP/FP/FN status

**Waiting on Rishav.** He ran the manual labeling pass on these results during the May 19 session and was going to send back labeled SVG text files. Once those arrive we can fill in the accuracy column in the paper's cross-format table.

Until then, the `parsere.out` and `out.svg` files in this folder are the raw output and the labels are unverified at the per-block level.

## Running

```bash
mkdir -p output
docker run --platform linux/amd64 --rm -v "$PWD/output:/output" parsere-runner json
```

About 30 seconds end-to-end.
