# Docker Runner

One image builds all three harnesses (json-c, curl, libelf), ships the patched ParseRE, and runs any of the three evaluations.

## Building

```bash
cd docker
docker build --platform linux/amd64 -t parsere-runner -f Dockerfile .
```

First build takes 10 to 15 minutes. Most of that is compiling curl from source (the `--without-shared` configure flag forces a static `.a` library, which ParseRE needs to avoid dynamic-linker pollution in the traces).

## Running

```bash
mkdir -p out
docker run --platform linux/amd64 --rm -v "$PWD/out:/output" parsere-runner [json|url|elf]
```

Outputs land in `out/`:

- `out.dot`: the labeled CFG in Graphviz format
- `out.svg`: rendered version, opens in any browser
- `parsere.out`: address-range to label mapping (one line per labeled basic block)

## Why `--platform linux/amd64`

ParseRE traces x86-64 binaries with `qemu-x86_64` (user-mode emulation). On Apple Silicon, Docker Desktop normally runs `linux/arm64` images; we force `linux/amd64` so the harnesses are actually x86-64 binaries that QEMU user-mode can trace. The platform flag tells Docker to use Rosetta-or-QEMU emulation for the container itself, then `qemu-x86_64` runs inside it.

This is slower than native execution, but the trace collection happens once per input (20 inputs for ELF, 27 for JSON, 1458 for URL). Even URL completes in under 10 minutes on an M1.

## Base image choice

`python:3.13-bookworm`. We tried `debian:bookworm` first but it ships Python 3.11, and ParseRE's source uses `type ttuple[T] = tuple[T, ...]` syntax that only parses in 3.12+. Building Python 3.13 from source inside the container worked but added 20 minutes to every rebuild. The official Python image was easier.

## Inspecting the image without running the full pipeline

If you want to poke at the built harnesses or the ParseRE source directly:

```bash
docker run --platform linux/amd64 --rm -it --entrypoint /bin/bash parsere-runner
# inside the container:
ls /harnesses/
ls /parsere/
```

To replay a single input through one harness manually (this is the most useful debug command):

```bash
docker run --platform linux/amd64 --rm \
  -v "$PWD/../evaluations/elf/corpus:/corpus" \
  --entrypoint /bin/bash parsere-runner -c '
    qemu-x86_64 -d in_asm -D /tmp/trace.log /harnesses/elf_harness < /corpus/full.elf
    echo "exit=$?"
    head -40 /tmp/trace.log
  '
```

## run.sh

The `run.sh` script is what runs when the container starts. It picks the right harness based on the format argument, sets the ParseRE flags, and copies the output files into the mounted `/output` directory. Reading it is the fastest way to see exactly what gets invoked.
