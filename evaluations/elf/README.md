# evaluations/elf/

Ben,

This is the ELF evaluation I built for the paper. The whole thing is reproducible: regenerate the corpus, rebuild the template, rerun ParseRE, and the numbers come out identical.

## What landed here

```
elf/
├── README.md              you are here
├── corpus/                8 ELF64 files, 1048 bytes each, all valid per readelf
├── output/                real ParseRE output from May 21
│   ├── parsere.out        269 lines, 68 of them labeled section_header
│   ├── out.dot            full CFG with addr2line annotations
│   ├── out.svg            rendered CFG, open in a browser
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
| CFG nodes after cleanup | 358 |
| CFG edges | 354 |
| Labeled basic blocks | 68 (all `section_header`) |
| Ambiguous (`None`) blocks | 202 |
| True positives | 62 |
| False positives | 5 |
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

The trick with binary formats is that you can't write byte alternatives by hand. The offsets in the ELF header have to match the actual positions of the content, the section header table has to point at real sections, etc. So I wrote a generator (`scripts/gen_template.py`) that:

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

About 10 seconds end-to-end on my M1. Most of it is QEMU startup for the 20 inputs.

## Reproducing the corpus

You can regenerate at any time:

```bash
cd evaluations/elf/scripts
python3 gen_elf_corpus.py ../corpus    # writes the 8 ELF files
python3 gen_template.py                 # writes elf_template.py
```

The generator is deterministic so byte literals should match exactly. If they ever drift, update the `ELF_PARSE_TREE_TEMPLATE` in `parsere/main.py` and rebuild the Docker image.

## The `program_header` mystery (resolved)

When I first ran this I expected `program_header` to get labels because I had four variants of it. Got zero. Spent half an hour double-checking the template before I figured it out:

Libelf reads program headers with `gelf_getphdr`. It's a single function that unpacks 56 bytes into a struct. The `p_type` field gets stored in the struct, but libelf doesn't branch on it during parsing. So the trace through `gelf_getphdr` is byte-for-byte identical for PT_NOTE, PT_INTERP, PT_DYNAMIC, and PT_NULL inputs. No trace difference, no labels.

Section types are different because the harness has a real conditional on `sh_type`. Variants with a real symtab take the symtab-walking branch and execute `gelf_getsym` and `elf_strptr`. Variants where the symtab is empty skip the branch.

This generalizes to a paper-worthy observation that ended up in Section IV-E: text formats have per-production parser routines, binary formats have uniform record readers, and the labels appear where conditional consumer code lives.

## Why the corpus is small

The other evaluations have much larger corpora (JSON 27, URL 1458). My ELF corpus is 20. A larger corpus would require more orthogonal variation dimensions, and the obvious candidates each break the fixed-layout invariant:

- Varying `e_machine` would require multi-architecture support that our harness doesn't have.
- Varying the number of program headers would change the offset of the section data.
- Varying `e_class` (32-bit vs 64-bit) would require completely different struct layouts.

For the paper's cross-format comparison, 20 instantiations is enough to demonstrate the binary vs text contrast. Larger corpora are natural follow-up work.

Taka
