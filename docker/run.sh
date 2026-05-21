#!/bin/bash
set -e

FORMAT="${1:-json}"

case "$FORMAT" in
  json)
    TARGET="/harnesses/json_c_harness"
    ;;
  url|uri)
    TARGET="/harnesses/curl_url_harness"
    ;;
  elf)
    TARGET="/harnesses/elf_harness"
    ;;
  *)
    echo "Unknown format: $FORMAT"
    echo "Usage: docker run parsere-runner [json|url|elf]"
    exit 1
    ;;
esac

echo "=== ParseRE: format=$FORMAT target=$TARGET ==="
echo "Python: $(python3 --version)"
echo "QEMU: $(which qemu-x86_64)"

cd /parsere

python3 main.py \
  --target-path "$TARGET" \
  --format "$FORMAT" \
  --qemu-path /usr/bin/qemu-x86_64 \
  --addr2line-path /usr/bin/addr2line

echo "=== Copying outputs ==="
mkdir -p /output
cp -f out.dot out.svg parsere.out /output/ 2>/dev/null || true
echo "Done. Outputs in /output/"
