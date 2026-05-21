# URL Evaluation (curl)

Target: [curl](https://github.com/curl/curl), commit `462244447e8ba3a53b1ba9f0ba7baa52d8777daa`.

Entry point: `curl_url_set(handle, CURLUPART_URL, input, ...)`.

The URI template was defined by Ben. This evaluation took the longest to debug because of the static-linking lesson described below.

## Headline numbers

| Metric | Value |
|--------|-------|
| Template instantiations | 1458 |
| Pairwise comparisons | 2,125,764 |
| CFG nodes after cleanup | 522 |
| CFG edges | 558 |
| Labeled basic blocks | 211 (40.4% of graph) |
| Productions used | 11 (including "None") |

## Label distribution

| Production | Labeled BBs | Fraction |
|-----------|------------:|---------:|
| host | 91 | 43.1% |
| port | 31 | 14.7% |
| segment | 30 | 14.2% |
| userinfo@ | 25 | 11.8% |
| None (ambiguous) | 21 | 10.0% |
| ?query | 3 | 1.4% |
| :port | 3 | 1.4% |
| #fragment | 3 | 1.4% |
| query | 2 | 0.9% |
| fragment | 2 | 0.9% |
| path-abempty | 1 | 0.5% |

`host` dominates because curl's URL parser does extensive host validation: IPv4 vs IPv6 vs hostname, IDNA, bracket handling. Lots of code, all attributable to the `host` production.

The duplicate-looking labels (`port` vs `:port`, `query` vs `?query`, `fragment` vs `#fragment`) come from the template's leaf naming. The colon/question-mark/hash prefixes indicate that the delimiter character was included in the label string. This is a template-design quirk in Ben's URI definition; the underlying code is correctly attributed.

## The static-linking lesson

The first attempt at this evaluation produced zero labeled blocks.

The harness was linked with `-lcurl` against the system libcurl, which loaded dynamically at runtime. Dynamic linking adds a large startup phase before `main()` runs: ld.so resolves every imported symbol, traverses the DT_NEEDED list, runs the .init array. All of that work happens *every time the binary is invoked*, regardless of what input it gets.

ParseRE's useless-edges filter looks for edges that appear in every trace. Edges that always fire are not informative about which input feature is being processed. The dynamic linker code is, by definition, run on every input. ParseRE wiped the entire graph because every node had a dynamic-linker prefix.

Fix: rebuild curl from source with `--without-shared` to get a static `libcurl.a`, link the harness against that. The dynamic-linker startup is still there (we still rely on libc dynamically), but the parser code is no longer behind it.

The Dockerfile bakes this in: there is a multi-step curl build with all optional features disabled and `--without-shared`. The fact that this works is the main reason every harness in this repo is statically linked where possible.

## TP/FP/FN status

**Waiting on Rishav.** Same as JSON. He labeled the URI output during the May 19 session and was going to send back text files. The accuracy column in the paper's cross-format table remains blank until they arrive.

## Running

```bash
mkdir -p output
docker run --platform linux/amd64 --rm -v "$PWD/output:/output" parsere-runner url
```

About 8 minutes end-to-end on an M1 because of the 2.1 million pairwise comparisons. Most of the time is the pairwise diff computation, not the QEMU tracing.
