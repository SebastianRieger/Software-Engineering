FROM debian:bookworm

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    qemu-user-static \
    binfmt-support \
    util-linux \
    parted \
    e2fsprogs \
    dosfstools \
    kpartx \
    curl \
    xz-utils \
    pigz \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN dpkg-reconfigure qemu-user-static 2>/dev/null || true

COPY run-build.sh  /usr/local/bin/run-build.sh
COPY customize.sh  /usr/local/bin/customize.sh
RUN sed -i 's/\r$//' /usr/local/bin/run-build.sh /usr/local/bin/customize.sh \
    && chmod +x   /usr/local/bin/run-build.sh /usr/local/bin/customize.sh

CMD ["/usr/local/bin/run-build.sh"]
