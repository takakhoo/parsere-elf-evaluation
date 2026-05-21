# parsere/

Ben,

This is your `main.py` with three minimal edits. Diff is small enough to inline review.

## What I changed

**1. ELF template definition.** Added `ELF_PARSE_TREE_TEMPLATE` after `URI_PARSE_TREE_TEMPLATE` around line 591. The byte literals come from my corpus generator output (see `evaluations/elf/scripts/gen_template.py`). Three children:
- `elf_header`: 1 alternative (the 64-byte ELF header is identical across all corpus members)
- `program_header`: 4 alternatives (varies the second program header's type field)
- `section_header`: 5 alternatives (varies which sections carry real data versus zeroed bytes)

Yields 1 × 4 × 5 = 20 instantiations through Cartesian product.

**2. Format switch case.** Added `case "elf":` to the dispatch in `main()` around line 844, so `--format elf` resolves to the new template.

**3. Zero-edge guard.** Changed the condition in the uniquifying step (line 683) from `len(e1) < len(e2) and len(e1 - e2) / len(e1) < 0.1` to `len(e1) > 0 and len(e1) < len(e2) and len(e1 - e2) / len(e1) < 0.1`.

Without this guard, any template with a child that has only one alternative crashes with `ZeroDivisionError` because the rule's edge set is empty. My `elf_header` child hits this immediately.

## Reading order if you want to verify the changes

1. **`ParseTreeTemplate` class**. Your `instantiate()` and `difference()` methods are doing all the heavy lifting. I didn't touch them.
2. **`QEMUTracer` class**. Wraps `qemu-x86_64 -d in_asm -D` and parses the resulting log. I didn't touch this either.
3. **`run()` function**. The pipeline orchestration. The only change here is the one-line zero-edge guard.
4. **`ELF_PARSE_TREE_TEMPLATE`** at line 591. New code. Byte literals are real, sliced from corpus files.
5. **Format switch in `main()`** at line 844. New case for ELF.

## Dependencies

- Python 3.13 (for the `type ttuple[T] = tuple[T, ...]` syntax in your code)
- networkx
- pydot
- pyelftools
- tqdm
- cxxfilt

All via `pip install`.

## Standalone usage

If you have all dependencies plus a working `qemu-x86_64` binary and a target harness:

```bash
python3 main.py \
  --target-path /path/to/elf_harness \
  --format elf \
  --qemu-path /usr/bin/qemu-x86_64 \
  --addr2line-path /usr/bin/addr2line
```

Output files (`out.dot`, `out.svg`, `parsere.out`) land in the current directory.

On macOS this won't work directly because Homebrew's QEMU doesn't include user-mode emulation. Use the Docker image in `../docker/` instead.

## Upstreaming

When you're ready I can send the three edits as a single PR against `kenballus/parsere`. Total diff is around 150 lines including the byte literals.

Taka
