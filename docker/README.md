# docker/

Ben,

One Docker image builds all three harnesses and ships your patched ParseRE inside. Same container runs any of the three evaluations.

## Build

```bash
cd docker
docker build --platform linux/amd64 -t parsere-runner -f Dockerfile .
```

First build is 10 to 15 minutes. Most of that is compiling curl from source so we get a static `libcurl.a`. Subsequent builds use the layer cache and finish in seconds.

## Run

```bash
mkdir -p out
docker run --platform linux/amd64 --rm -v "$PWD/out:/output" parsere-runner [json|url|elf]
```

Outputs land in `out/`:

- `out.dot`: labeled CFG in Graphviz format
- `out.svg`: rendered CFG, browseable in any browser
- `parsere.out`: address-range to label mapping (one line per labeled basic block)

## Why `--platform linux/amd64`

I'm on an M1 Mac. Docker Desktop defaults to `linux/arm64` images on Apple Silicon. ParseRE traces x86-64 binaries with `qemu-x86_64` user-mode, so we need the container itself to be x86-64. The `--platform` flag forces that. Docker Desktop then uses Rosetta or QEMU to emulate the container, and `qemu-x86_64` runs inside that.

It's slower than native but fine. URL takes around 8 minutes, JSON about 30 seconds, ELF about 10 seconds.

## Base image choice

I started with `debian:bookworm` but it ships Python 3.11, and your code uses `type ttuple[T] = tuple[T, ...]` syntax from Python 3.12+. Building Python 3.13 from source inside the container added 20 minutes to every rebuild. Switched to the official `python:3.13-bookworm` image, which solved both problems.

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

I used this a lot when debugging the static-linking issue. Each `IN:` record in the trace is one basic block. If you see `_dl_init` or `_dl_relocate_object` near the top, the harness is dynamically linked and you need to rebuild it static.

## run.sh

This is the entry point. Picks the right harness from the format argument, sets the ParseRE flags, copies output into the mounted `/output` directory. Reading the script is the fastest way to see exactly what gets invoked.

Taka
