# evaluations/elf/

This directory contains the ELF evaluation developed for the paper draft. The corpus and template generators are deterministic, and the committed run includes raw output plus a manual review of every production-labeled block.

## What landed here

```
elf/
├── README.md              evaluation documentation
├── corpus/                8 ELF64 files, 1048 bytes each, all valid per readelf
├── output/                real ParseRE output from May 21
│   ├── parsere.out        270 records: 68 section_header, 202 None
│   ├── out.dot            trace-derived graph with addr2line annotations
│   ├── out.svg            rendered graph, viewable in a browser
│   ├── RESULTS.md         summary with tables and observations
│   └── MANUAL_LABELING.md per-function TP/FP breakdown
└── scripts/
    ├── gen_elf_corpus.py  builds the 8 corpus files
    ├── gen_template.py    builds elf_template.py from the corpus
    └── elf_template.py    generated, contains the byte literals
```

## Headline numbers

| Metric | Value |
|--------|------:|
| Template instantiations | 20 (1 × 4 × 5) |
| Pairwise comparisons | 380 |
| Trace-derived graph nodes | 358 |
| Consecutive-record edges | 354 |
| Labeled basic blocks | 68 (all `section_header`) |
| Ambiguous (`None`) blocks | 202 |
| True positives | 62 |
| False positives | 5 |
| Marginal cases | 1 |
| **Strict accuracy** | **91.2%** |

Per-function TP/FP breakdown is in `output/MANUAL_LABELING.md`.

## How the corpus is generated

`scripts/gen_elf_corpus.py` builds eight valid ELF64 files with a fixed layout:

```
[0:64]      ELF header (Elf64_Ehdr)
[64:176]    Program header table (2 × Elf64_Phdr)
[176:240]   .shstrtab data (section-name string table)
[240:360]   .strtab data (symbol-name string table)
[360:600]   .symtab data (10 Elf64_Sym entries)
[600:664]   .text data (placeholder code)
[664:1048]  Section header table (6 × Elf64_Shdr)
```

Every file is exactly 1048 bytes. The eight variants differ only in two dimensions:

1. The second program header's `p_type`: `PT_NOTE`, `PT_INTERP`, `PT_DYNAMIC`, or `PT_NULL`
2. Which sections are populated: full, no-symtab, no-strtab, no-symtab-or-strtab, no-text

Every file passes `readelf -a` validation.

## How the template plugs in

The ELF byte alternatives are generated rather than handwritten because header offsets must match the content layout and the section header table must point at valid regions. The template generator (`scripts/gen_template.py`):

1. Generates every corpus variant in memory.
2. Slices each variant into three regions: header (0-64), program headers (64-176), section region (176-1048).
3. Collects unique byte sequences per region across the variants.
4. Emits a `ParseTreeTemplate` definition with three children.

The byte literals it produces are also inlined directly into `parsere/main.py` at the `ELF_PARSE_TREE_TEMPLATE` definition. When `instantiate()` does the Cartesian product, it generates 1 × 4 × 5 = 20 byte strings, each of which is a valid 1048-byte ELF file.

## Running the evaluation

From the repo root:

```bash
mkdir -p evaluations/elf/output
docker run --platform linux/amd64 --rm \
  -v "$PWD/evaluations/elf/output:/output" \
  parsere-runner elf
```

The committed Apple Silicon run completed in roughly 10 seconds; most of that time was QEMU startup for the 20 inputs.

## Reproducing the corpus

You can regenerate at any time:

```bash
cd evaluations/elf/scripts
python3 gen_elf_corpus.py ../corpus    # writes the 8 ELF files
python3 gen_template.py                 # writes elf_template.py
```

The generator is deterministic so byte literals should match exactly. If they ever drift, update the `ELF_PARSE_TREE_TEMPLATE` in `parsere/main.py` and rebuild the Docker image.

## Why `program_header` is unlabeled

The `program_header` production has four variants but receives no labels because:

Libelf reads program headers with `gelf_getphdr`, which unpacks 56 bytes into a struct. The `p_type` field is stored in the struct, but libelf does not branch on it during parsing. The retained translation-log evidence through `gelf_getphdr` is therefore identical for PT_NOTE, PT_INTERP, PT_DYNAMIC, and PT_NULL inputs, leaving no differential record to label.

Section types are different because the harness has a real conditional on `sh_type`. Variants with a real symtab take the symtab-walking branch and execute `gelf_getsym` and `elf_strptr`. Variants where the symtab is empty skip the branch.

This result motivates a hypothesis in the paper draft: when a fixed-layout parser uses uniform record readers, production labels may appear mainly where conditional consumer code operates on the parsed structures. Broader evaluation is needed before generalizing beyond this harness and library.

## Why the corpus is small

The other evaluations have much larger corpora (JSON 27, URL 1458). My ELF corpus is 20. A larger corpus would require more orthogonal variation dimensions, and the obvious candidates each break the fixed-layout invariant:

- Varying `e_machine` would require multi-architecture support beyond the current harness.
- Varying the number of program headers would change the offset of the section data.
- Varying `e_class` (32-bit vs 64-bit) would require completely different struct layouts.

The 20-instantiation corpus demonstrates one contrast with the committed text-format runs. A larger and more varied binary corpus is necessary before making broader claims about binary parsers.
