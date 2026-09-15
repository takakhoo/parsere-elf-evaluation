# docker/

One Docker image builds the three implemented harnesses and includes the local ParseRE snapshot. The same container runs the JSON, URI, and ELF evaluations.

## Build

Run this command from the repository root so Docker can access `harnesses/` and `parsere/`:

```bash
docker build --platform linux/amd64 -t parsere-runner -f docker/Dockerfile .
```

The first build may take several minutes because it compiles curl from source to produce a static `libcurl.a`. Subsequent builds can reuse Docker's layer cache.

## Run

```bash
mkdir -p out
docker run --platform linux/amd64 --rm -v "$PWD/out:/output" parsere-runner [json|url|elf]
```

Outputs land in `out/`:

- `out.dot`: labeled trace-derived graph in Graphviz format
- `out.svg`: rendered trace-derived graph, viewable in a browser
- `parsere.out`: address-range to label mapping (one line per labeled basic block)

## Why `--platform linux/amd64`

Docker Desktop defaults to `linux/arm64` images on Apple Silicon. ParseRE analyzes x86-64 binaries with `qemu-x86_64` user-mode, so the container must be x86-64. The `--platform` flag selects that architecture; Docker Desktop then emulates the container when necessary.

Emulation is slower than a native amd64 run. Recorded Apple Silicon timings were approximately eight minutes for URL, 30 seconds for JSON, and 10 seconds for ELF; actual times depend on the host and Docker cache state.

## Base image choice

The image uses `python:3.13-bookworm` because the code uses Python 3.12+ generic type-alias syntax. Starting from Debian bookworm's Python 3.11 would otherwise require building a newer interpreter inside the image.

## Useful debugging command

If something looks off, this one-liner replays a single input through the harness manually and shows the QEMU trace:

```bash
docker run --platform linux/amd64 --rm \
  -v "$PWD/../evaluations/elf/corpus:/corpus" \
  --entrypoint /bin/bash parsere-runner -c '
    qemu-x86_64 -d in_asm -D /tmp/trace.log /harnesses/elf_harness < /corpus/full.elf
    echo "exit=$?"
    head -40 /tmp/trace.log
  '
```

This command is useful when debugging the linking and address-range assumptions. Each `IN:` record describes a QEMU translation block. If parser-library routines live in a shared object, their addresses fall outside the executable segment retained by the current tracer; link the parser library into the harness or extend the tracer to retain shared-library mappings.

## run.sh

This is the entry point. Picks the right harness from the format argument, sets the ParseRE flags, copies output into the mounted `/output` directory. Reading the script is the fastest way to see exactly what gets invoked.
