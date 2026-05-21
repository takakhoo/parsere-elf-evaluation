# ELF Evaluation

The fourth evaluation in the ParseRE paper. Target library: libelf from elfutils, the reference implementation used by Ghidra, radare2, and most binary analysis toolchains.

## Files

```
elf/
├── README.md          you are here
├── corpus/            8 generated ELF64 files, 1048 bytes each
├── output/            real run output from May 21
│   ├── parsere.out
│   ├── out.dot
│   ├── out.svg
│   ├── RESULTS.md
│   └── MANUAL_LABELING.md
└── scripts/
    ├── gen_elf_corpus.py    builds the 8 corpus files
    ├── gen_template.py      builds elf_template.py from the corpus
    └── elf_template.py      generated, contains baked byte literals
```

## Headline numbers

| Metric | Value |
|--------|-------|
| Template instantiations | 20 (1 x 4 x 5) |
| Pairwise comparisons | 380 |
| CFG nodes after cleanup | 358 |
| CFG edges | 354 |
| Labeled basic blocks | 68 (all `section_header`) |
| Ambiguous (`None`) blocks | 202 |
| True positives | 62 |
| False positives | 5 |
| **Strict accuracy** | **91.2%** |

Per-function breakdown is in [output/MANUAL_LABELING.md](output/MANUAL_LABELING.md).

## How the corpus was generated

[`scripts/gen_elf_corpus.py`](scripts/gen_elf_corpus.py) builds eight valid ELF64 files with a fixed layout:

```
[0:64]      ELF header (Elf64_Ehdr)
[64:176]    Program header table (2 x Elf64_Phdr)
[176:240]   .shstrtab data (section-name string table)
[240:360]   .strtab data (symbol-name string table)
[360:600]   .symtab data (10 Elf64_Sym entries)
[600:664]   .text data (placeholder code)
[664:1048]  Section header table (6 x Elf64_Shdr)
```

The eight variants differ only in:
1. The type of the second program header: PT_NOTE, PT_INTERP, PT_DYNAMIC, or PT_NULL
2. Which sections are populated (symbol table, string table, text, in various combinations)

Every file is exactly 1048 bytes. Every file passes `readelf -a` validation.

## How the template was generated

The trick with binary formats is that you cannot just write byte-level alternatives by hand; the offsets in the header have to match the actual positions of the content. So [`scripts/gen_template.py`](scripts/gen_template.py) builds the template programmatically:

1. Generate every corpus variant in memory.
2. Slice each variant into three regions: ELF header (bytes 0-64), program header table (bytes 64-176), section region (bytes 176-1048).
3. Collect the unique byte sequences in each region across all variants.
4. Emit a ParseTreeTemplate definition with three children: `elf_header` (1 unique sequence), `program_header` (4 unique sequences), `section_header` (5 unique sequences).

When ParseRE's `instantiate()` does the Cartesian product, it produces 1 x 4 x 5 = 20 byte strings, each of which is a valid 1048-byte ELF file.

[`scripts/elf_template.py`](scripts/elf_template.py) is the output of `gen_template.py`. The same byte constants are inlined directly into [`../../parsere/main.py`](../../parsere/main.py) at the `ELF_PARSE_TREE_TEMPLATE` definition.

## Running the evaluation

From the repo root:

```bash
mkdir -p evaluations/elf/output
docker run --platform linux/amd64 --rm \
  -v "$PWD/evaluations/elf/output:/output" \
  parsere-runner elf
```

About 10 seconds end-to-end on an M1. Most of that is QEMU startup for the 20 inputs.

## Reproducing the corpus

You can regenerate the corpus files at any time:

```bash
cd evaluations/elf/scripts
python3 gen_elf_corpus.py ../corpus
```

And rebuild the template:

```bash
python3 gen_template.py
# produces elf_template.py
```

If the regeneration changes the byte literals (it should not, the generator is deterministic), update the `ELF_PARSE_TREE_TEMPLATE` in `parsere/main.py` accordingly. The Docker image needs a rebuild after that change.

## Why `program_header` produced zero labels

This is the most interesting finding from the ELF evaluation, and it ended up shaping the discussion section of the paper.

The four `program_header` variants differ only in the `p_type` field of the second phdr (PT_NOTE vs PT_INTERP vs PT_DYNAMIC vs PT_NULL). Libelf reads program headers with `gelf_getphdr`, which is a fixed function that does:

```c
GElf_Phdr *gelf_getphdr(Elf *elf, int ndx, GElf_Phdr *dst) {
    // Same 56-byte unpack regardless of p_type
    memcpy(&dst->p_type, raw + 0, 4);
    memcpy(&dst->p_flags, raw + 4, 4);
    memcpy(&dst->p_offset, raw + 8, 8);
    // ... etc
    return dst;
}
```

There is no type-specific dispatch. The `p_type` field gets read into a struct, but libelf does not branch on it. So the basic-block trace through `gelf_getphdr` is identical for all four variants, the edge sets come out identical, and ParseRE's difference algorithm finds no edges to attribute to `program_header`.

Contrast with `section_header`: the harness has a real conditional:

```c
if (shdr.sh_type == SHT_SYMTAB || shdr.sh_type == SHT_DYNSYM) {
    // walk the symbol table
    Elf_Data *data = elf_getdata(scn, NULL);
    ...
}
```

Variants that have a non-null symtab take this branch and execute `elf_getdata`, `gelf_getsym`, and `elf_strptr`. Variants where the symtab is empty skip the branch. Different traces, different edge sets, attribution works.

This generalizes to a paper-worthy observation: text formats have per-production parser functions, so every production gets its own labels. Binary formats have uniform record readers, so labels appear only where consumer code conditionally processes the parsed structures. ParseRE captures exactly that distinction without anyone having to tell it.

## Why this evaluation is small (20 instantiations)

The other evaluations have much larger corpora:

- JSON: 27 instantiations
- URL: 1458 instantiations
- ELF: 20 instantiations

A larger ELF corpus would require more orthogonal variation dimensions. The current template varies two things (phdr type and section presence). Adding more would mean varying `e_machine` (x86 vs ARM, but our harness is x86-64-only), varying the number of program headers (but the existing layout assumes exactly 2), or varying `e_class` (32-bit vs 64-bit). Each of these requires rewriting `gen_elf_corpus.py` to handle multiple layouts.

For an ACSAC paper that wants a clean cross-format comparison, the 20-instantiation corpus is sufficient to demonstrate the binary-vs-text contrast. A larger corpus would be a natural follow-up.
