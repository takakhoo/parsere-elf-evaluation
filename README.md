# ParseRE ELF Evaluation and Paper Draft

This repository is a research-assistant extension and reproducibility snapshot for [ParseRE](https://github.com/kenballus/parsere), a binary-analysis prototype that relates structural differences in known input formats to differences in QEMU logging output. It adds an ELF evaluation, containerized harnesses for three parser libraries, evaluation artifacts, and an IEEE-style working paper draft.

The manuscript at [`paper/main.pdf`](paper/main.pdf) is a draft, not a submission to a specific conference. Several evaluations remain incomplete, and the results below distinguish committed measurements from planned or pending work.

![First page of the paper draft](images/paper_preview.png)

## Repository contents

```text
.
├── paper/                 LaTeX source, figures, references, and compiled draft
├── parsere/main.py        ParseRE snapshot with ELF support and an empty-edge guard
├── harnesses/             C harnesses for json-c, curl, and libelf
├── docker/                Reproducible Linux/amd64 build and execution environment
├── evaluations/
│   ├── elf/               Generated corpus, scripts, outputs, and manual review
│   ├── json/              Committed json-c output; accuracy review pending
│   ├── url/               Committed curl output; accuracy review pending
│   └── hpack/             Planned evaluation; no results yet
├── images/                Selected traces, graphs, and paper preview assets
├── references/            Related-work notes
└── docs/                  Contribution notes
```

## Implemented work

- Added a deterministic fixed-layout ELF64 corpus generator and a three-part ParseRE template covering the ELF header, program headers, and section region.
- Added an ELF harness that exercises libelf header, section, string-table, and symbol-table APIs.
- Added a Docker environment that builds json-c, curl, and libelf harnesses and runs the analyses under `qemu-x86_64`.
- Added a guard for empty edge sets in the uniqueness-filtering step, preventing a `ZeroDivisionError` when a template child has only one alternative.
- Documented the committed URI, JSON, and ELF outputs and manually reviewed every production-labeled ELF block.

## Evaluation status

ParseRE builds ordered pairs with `itertools.permutations(inputs, 2)`, so an evaluation with (N) inputs performs (N(N-1)) ordered comparisons. Counts below were checked directly against the committed templates and output files.

| Format | Parser | Inputs | Ordered comparisons | Committed output | Accuracy status |
|---|---|---:|---:|---|---|
| URI | curl | 1,458 | 2,124,306 | 191 production-labeled blocks + 21 ambiguous blocks | Manual TP/FP/FN review pending |
| JSON | json-c | 27 | 702 | 295 production-labeled blocks | Manual TP/FP/FN review pending |
| ELF | libelf | 20 | 380 | 68 production-labeled blocks + 202 ambiguous blocks | 62/68 strict true positives (91.2%); 1 additional marginal case |
| URI | Apache APR | Planned | -- | No committed run | Pending |
| HPACK | nghttp2 | Planned | -- | No committed implementation or run | Pending |

For the ELF result, the five strict false positives are inside `__gelf_getehdr_rdlock`, an ELF-header validation routine reached during section traversal. The full function-level review is in [`evaluations/elf/output/MANUAL_LABELING.md`](evaluations/elf/output/MANUAL_LABELING.md).

## Quick reproduction

Build from the repository root so the Docker build context contains `harnesses/` and `parsere/`:

```bash
git clone https://github.com/takakhoo/ParseRE_ELF_etc.git
cd ParseRE_ELF_etc

docker build --platform linux/amd64 \
  -t parsere-runner \
  -f docker/Dockerfile .
```

Run the ELF evaluation and write outputs to a separate directory:

```bash
mkdir -p reproduced/elf
docker run --platform linux/amd64 --rm \
  -v "$PWD/reproduced/elf:/output" \
  parsere-runner elf
```

Replace `elf` with `json` or `url` for the other implemented harnesses. The first image build can take several minutes because curl is compiled from source. The URL analysis is substantially slower than the JSON and ELF analyses because it compares more than two million ordered input pairs.

## ELF evaluation

The ELF template contains three children:

- `elf_header`: one fixed 64-byte ELF header;
- `program_header`: four alternatives that vary the second program header type; and
- `section_header`: five alternatives that vary populated and empty section data.

Their Cartesian product produces 20 valid 1,048-byte ELF64 inputs. Libelf reads the program-header variants through the same basic path, so no production-specific `program_header` label survives the uniqueness filter. Section and symbol-table variations exercise conditional consumer logic, producing 68 `section_header` labels.

To regenerate the deterministic corpus and emitted template:

```bash
python3 evaluations/elf/scripts/gen_elf_corpus.py evaluations/elf/corpus
python3 evaluations/elf/scripts/gen_template.py
```

See [`evaluations/elf/README.md`](evaluations/elf/README.md) for the layout and [`evaluations/elf/output/RESULTS.md`](evaluations/elf/output/RESULTS.md) for the recorded run.

## Important limitations

- The current tracer invokes QEMU with `-d in_asm`. That log records translation blocks when QEMU translates them; it is not a complete record of every block execution. The implementation therefore constructs a trace-derived graph from translation-log order. Before publication, the method should be validated against execution callbacks such as the official [QEMU TCG plugin interface](https://www.qemu.org/docs/master/devel/tcg-plugins.html) or another dynamic tracing mechanism; QEMU's [emulation documentation](https://www.qemu.org/docs/master/about/emulation.html) provides additional context on translation blocks.
- Only the ELF production labels have a committed manual accuracy review. URI and JSON accuracy values must remain unreported until their labeled blocks are reviewed.
- Apache APR and HPACK are planned evaluations, not completed results.
- The harnesses intentionally place parser code inside the target executable's address range by linking the parser libraries statically. Dynamically linked parser code falls outside the executable segment retained by the current tracer and is therefore filtered out.
- The artifact targets Linux x86-64 user-mode emulation and assumes one executable `PT_LOAD` segment in the target binary.

## Paper draft

The paper source is in [`paper/`](paper/). Build it with:

```bash
cd paper
tectonic main.tex
```

Generic `TODO` markers identify incomplete measurements and editorial decisions:

```bash
grep -RIn '\[TODO:' paper --include='*.tex'
```

The draft should not claim a complete four-format evaluation until the pending URI, JSON, Apache APR, and HPACK work is finished.

## Licensing

This snapshot does not currently include a license file, and the included `parsere/main.py` is derived from the upstream ParseRE repository, which also has no detected license. The code is publicly viewable for research review, but the repository should not be described as an open-source release until the authors resolve licensing.
