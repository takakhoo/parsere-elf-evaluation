# evaluations/json/

Ben,

Real run of your JSON template against json-c. Used your `JSON_PARSE_TREE_TEMPLATE` as-is; I didn't touch it.

## Target

[json-c](https://github.com/json-c/json-c), commit `89485680314df3b4dfb2aaed14f89d212d57c119`. Built with cmake, linked statically through `libjson-c.a`.

Entry point: `json_tokener_parse(input)`.

## Headline numbers

| Metric | Value |
|--------|------:|
| Template instantiations | 27 |
| Pairwise comparisons | 729 |
| CFG nodes after cleanup | 464 |
| CFG edges | 400 |
| Labeled basic blocks | 294 (63.4% of graph) |
| Productions used | 6 |

## Label distribution

| Production | Labeled BBs | % of labels |
|-----------|------------:|------------:|
| number    | 110 | 37.4% |
| object-element | 77 | 26.2% |
| string    | 39 | 13.3% |
| array     | 36 | 12.2% |
| boolean   | 24 | 8.2% |
| nan       | 9  | 3.1% |

`number` dominates because C-level numeric parsing is heavy: sign handling, decimal point, exponent, overflow checks, `strtod` wrappers. Each step is a separate basic block.

`nan` is tiny because it's a three-character string comparison.

## TP/FP/FN status

Waiting on Rishav. He ran the manual labeling pass on these results during our May 19 session and was going to send back labeled SVG text files. Until then, `parsere.out` and `out.svg` are the raw output and the per-block accuracy is unverified.

The current paper has a `\textit{[RISHAV: ...]}` marker where the accuracy number goes.

## Running

```bash
mkdir -p output
docker run --platform linux/amd64 --rm -v "$PWD/output:/output" parsere-runner json
```

About 30 seconds end-to-end.

Taka
