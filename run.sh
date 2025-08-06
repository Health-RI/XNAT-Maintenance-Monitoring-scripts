#!/bin/bash

# XNAT Scripts Docker Runner
# This script runs the XNAT reporting scripts from GitHub Container Registry
# with configurable volume mounts.

set -e

# Configuration
REGISTRY="ghcr.io"
REPOSITORY_OWNER="health-ri"
IMAGE_NAME="xnat-maintenance-monitoring-scripts"
DEFAULT_TAG="latest"

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS] <script_name> [script_args...]"
    echo ""
    echo "Options:"
    echo "  -t, --tag TAG           Docker image tag to use (default: latest)"
    echo "  -v, --volume MOUNT      Additional volume mount (format: 'src:dest')"
    echo "                          Can be specified multiple times"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 users_per_project --xnat_url https://xnat.health-ri.nl"
    echo "  $0 -t v1.2.3 users_per_project --xnat_url https://xnat.health-ri.nl"
    echo "  $0 -v /input:/data/input -v /output:/data/output disk_usages ..."
}

# Parse command line arguments
IMAGE_TAG="$DEFAULT_TAG"
VOLUME_MOUNTS=()
SCRIPT_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -v|--volume)
            VOLUME_MOUNTS+=("$2")
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            SCRIPT_ARGS+=("$@")
            break
            ;;
    esac
done

# Check if script name is provided
if [ ${#SCRIPT_ARGS[@]} -eq 0 ]; then
    usage
    exit 1
fi

FULL_IMAGE_NAME="${REGISTRY}/${REPOSITORY_OWNER}/${IMAGE_NAME}:${IMAGE_TAG}"

# Try to pull image from registry
echo "Pulling Docker image: ${FULL_IMAGE_NAME}"
if ! docker pull "$FULL_IMAGE_NAME" 2>/dev/null; then
    echo "Failed to pull image from registry"
    
    # Check if image exists locally
    if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "^${FULL_IMAGE_NAME}$"; then
        echo "Using local image: ${FULL_IMAGE_NAME}"
    else
        echo "Error: Image not available locally or from registry"
        exit 1
    fi
fi

# Build volume mount arguments
VOLUME_ARGS=()

# Default mount: current directory to /data
VOLUME_ARGS+=("-v" "$(pwd):/data")

# Add additional volume mounts from command line arguments
for mount in "${VOLUME_MOUNTS[@]}"; do
    if [[ "$mount" == *":"* ]]; then
        src="${mount%:*}"
        dest="${mount#*:}"
        if [ -e "$src" ]; then
            VOLUME_ARGS+=("-v" "$src:$dest")
            echo "Adding volume mount: $src -> $dest"
        else
            echo "Warning: Source path does not exist, skipping: $src"
        fi
    else
        echo "Warning: Invalid mount format, skipping: $mount"
    fi
done

# Run the container
echo "Running script: ${SCRIPT_ARGS[0]}"
docker run --rm -it "${VOLUME_ARGS[@]}" "$FULL_IMAGE_NAME" "${SCRIPT_ARGS[@]}"
