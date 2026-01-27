FROM ubuntu:24.04

# Install build dependencies
RUN apt-get update && apt-get install -y \
    kpartx \
    qemu-user-static \
    python3 \
    python3-pip \
    python3-venv \
    file \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Create user to match host UID/GID (will be set at runtime)
# This avoids permission issues on mounted volumes
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} builder 2>/dev/null || groupmod -n builder $(getent group ${GROUP_ID} | cut -d: -f1) && \
    useradd -m -u ${USER_ID} -g ${GROUP_ID} -G sudo builder && \
    echo "builder ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

USER builder
WORKDIR /workspace

# Copy build scripts
COPY --chown=builder:builder . .

# Default command shows help
CMD ["python3", "build_image.py", "--help"]
