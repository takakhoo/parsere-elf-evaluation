# Patched ParseRE

The patched single-file ParseRE engine. Diffs against Ben's upstream at [github.com/kenballus/parsere](https://github.com/kenballus/parsere) are minimal.

## What changed

Three edits, all in `main.py`:

1. **ELF template definition** (around line 591). Adds `ELF_PARSE_TREE_TEMPLATE` with three children: `elf_header` (1 alternative), `program_header` (4 alternatives), `section_header` (5 alternatives). Yields 20 instantiations through Cartesian product.

2. **Format switch case** (around line 844). Adds `case "elf":` to the dispatch in `main()` so `--format elf` resolves to the new template.

3. **Zero-edge guard** (line 683). Changed the condition in the uniquifying step from `len(e1) < len(e2) and len(e1 - e2) / len(e1) < 0.1` to `len(e1) > 0 and len(e1) < len(e2) and len(e1 - e2) / len(e1) < 0.1`. Without this guard, any template with a child that has only one alternative causes a `ZeroDivisionError` (the rule produces zero edges in the per-rule map).

## Reading order

If you want to understand the engine quickly, read in this order:

1. `ParseTreeTemplate` class definition. The whole engine pivots on its `instantiate()` and `difference()` methods.
2. `QEMUTracer` class. Wraps `qemu-x86_64 -d in_asm -D` and parses the resulting log.
3. `run()` function (the long one). This is the main pipeline:
   - instantiate the template into concrete inputs
   - trace each input under QEMU
   - compute pairwise parse-tree diffs
   - associate edge deltas with rule diffs (for pairs that differ in exactly one rule)
   - two-step uniqueness filter to remove shared code
   - color propagation
4. `JSON_PARSE_TREE_TEMPLATE`, `URI_PARSE_TREE_TEMPLATE`, `ELF_PARSE_TREE_TEMPLATE`. These are data, not code. They define what corpus gets generated for each format.

## Dependencies

- Python 3.13 (the `type ttuple[T] = tuple[T, ...]` syntax is 3.12+, and the broader ParseRE code uses 3.13 features)
- networkx
- pydot
- pyelftools
- tqdm
- cxxfilt

All available via `pip install`.

## Running standalone (no Docker)

If you have all dependencies plus a working `qemu-x86_64` binary and a target harness:

```bash
python3 main.py \
  --target-path /path/to/harness \
  --format elf \
  --qemu-path /usr/bin/qemu-x86_64 \
  --addr2line-path /usr/bin/addr2line
```

Output files (`out.dot`, `out.svg`, `parsere.out`) are written to the current directory.

On macOS this does not work directly because Homebrew's QEMU does not ship `qemu-x86_64` (user-mode). Use the Docker image in the [`docker/`](../docker/) folder instead.

## Submitting the upstream patch

When this lands at ACSAC, the three edits should go upstream as a single PR against [github.com/kenballus/parsere](https://github.com/kenballus/parsere). The diff is small enough to inline review.
