FROM debian:bookworm-slim

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      qemu-system-x86 qemu-utils genisoimage unzip ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY run-vm.sh /usr/local/bin/run-vm
COPY prepare-installer.sh /usr/local/bin/prepare-installer
RUN chmod 0755 /usr/local/bin/run-vm /usr/local/bin/prepare-installer

EXPOSE 5900
ENTRYPOINT ["/usr/local/bin/run-vm"]
