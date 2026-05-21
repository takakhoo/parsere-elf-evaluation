# ParseRE all-in-one runner.
# Builds harness(es) + runs ParseRE inside a container with QEMU user-mode.
#
# Usage:
#   docker build --platform linux/amd64 -t parsere-runner -f Dockerfile .
#   docker run --rm -v "$PWD/output:/output" parsere-runner json
#
FROM --platform=linux/amd64 python:3.13-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    libelf-dev \
    zlib1g-dev \
    pkg-config \
    qemu-user \
    graphviz \
    binutils \
    autoconf \
    libtool \
 && rm -rf /var/lib/apt/lists/*

# ---- json-c harness ----
WORKDIR /harnesses
RUN git clone https://github.com/json-c/json-c \
 && cd json-c \
 && git checkout 89485680314df3b4dfb2aaed14f89d212d57c119 \
 && mkdir build && cd build \
 && cmake .. && make -j$(nproc)

COPY harnesses/json_c_harness.c /harnesses/json_c_harness.c
RUN gcc -Wl,-z,now -no-pie -g -O0 -fno-inline \
    -I/harnesses/json-c/build -I/harnesses/json-c \
    /harnesses/json_c_harness.c /harnesses/json-c/build/libjson-c.a \
    -o /harnesses/json_c_harness

# ---- curl URL harness (built from source, static link) ----
WORKDIR /harnesses
RUN git clone https://github.com/curl/curl \
 && cd curl \
 && git checkout 462244447e8ba3a53b1ba9f0ba7baa52d8777daa \
 && autoreconf -fi \
 && ./configure --without-ssl --without-zlib --without-brotli --without-zstd \
    --without-default-ssl-backend --without-ca-bundle --without-ca-path \
    --without-ca-fallback --without-ca-embed --without-libpsl \
    --without-libgsasl --without-librtmp --without-winidn --without-apple-idn \
    --without-libidn2 --without-nghttp2 --without-ngtcp2 --without-openssl-quic \
    --without-nghttp3 --without-quiche --without-msh3 --without-libuv \
    --without-zsh-functions-dir --without-fish-functions-dir --without-shared \
    --disable-alt-svc --disable-headers-api --disable-docs \
    CFLAGS="-g -O0" \
 && make -j$(nproc)

COPY harnesses/curl_url_harness.c /harnesses/curl_url_harness.c
RUN gcc -Wl,-z,now -no-pie -g -O0 -fno-inline \
    -I/harnesses/curl/include \
    /harnesses/curl_url_harness.c /harnesses/curl/lib/.libs/libcurl.a \
    -o /harnesses/curl_url_harness

# ---- ELF harness (static link to avoid dynamic-linker trace pollution) ----
COPY harnesses/elf_harness.c /harnesses/elf_harness.c
RUN gcc -Wl,-z,now -no-pie -g -O0 -fno-inline -static \
    /harnesses/elf_harness.c -lelf -lz \
    -o /harnesses/elf_harness

# ---- ParseRE ----
WORKDIR /parsere
COPY parsere/main.py /parsere/main.py

RUN pip install --no-cache-dir \
    networkx pydot pyelftools tqdm cxxfilt

COPY run.sh /parsere/run.sh
RUN chmod +x /parsere/run.sh

ENTRYPOINT ["/parsere/run.sh"]
