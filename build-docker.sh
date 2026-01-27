#!/bin/bash
# Build Raspberry Pi image using Docker

set -e

# Get current user's UID/GID to avoid permission issues
USER_ID=$(id -u)
GROUP_ID=$(id -g)

echo "Building Docker image..."
docker build \
    --build-arg USER_ID=${USER_ID} \
    --build-arg GROUP_ID=${GROUP_ID} \
    -t lemon-pi-builder .

echo ""
echo "Running image builder..."
docker run --rm --privileged \
    -v "$(pwd):/workspace" \
    -v /dev:/dev \
    lemon-pi-builder \
    bash -c "sudo python3 build_image.py $* && sudo chown builder:builder /workspace/*-citrascope.img"
