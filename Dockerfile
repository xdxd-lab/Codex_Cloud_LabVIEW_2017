FROM debian:bookworm-slim

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      qemu-system-x86 qemu-utils ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY run-vm.sh /usr/local/bin/run-vm
RUN chmod 0755 /usr/local/bin/run-vm

EXPOSE 5900
ENTRYPOINT ["/usr/local/bin/run-vm"]
