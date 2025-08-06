#!/bin/bash

# XNAT Scripts Docker Build and Push Script
# This script builds the Docker image and pushes it to GitHub Container Registry

set -e

# Configuration
REGISTRY="ghcr.io"
REPOSITORY_OWNER="health-ri"
IMAGE_NAME="xnat-maintenance-monitoring-scripts"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to display usage
usage() {
    echo "Usage: $0 [options] <tag>"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  --no-push      Build only, don't push to registry"
    echo "  --latest       Tag as latest as well"
    echo ""
    echo "Examples:"
    echo "  $0 v1.2.3                  # Build and push with specific tag"
    echo "  $0 --no-push v1.2.3        # Build only, don't push"
    echo "  $0 --latest v1.2.3         # Build, push with tag and latest"
}

# Parse arguments
PUSH=true
TAG_AS_LATEST=false
IMAGE_TAG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        --no-push)
            PUSH=false
            shift
            ;;
        --latest)
            TAG_AS_LATEST=true
            shift
            ;;
        -*)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            IMAGE_TAG="$1"
            shift
            ;;
    esac
done

# Check if tag is provided
if [ -z "$IMAGE_TAG" ]; then
    echo "Error: Tag is required"
    usage
    exit 1
fi

FULL_IMAGE_NAME="${REGISTRY}/${REPOSITORY_OWNER}/${IMAGE_NAME}"

echo "Building Docker image..."
echo "Repository: ${FULL_IMAGE_NAME}"
echo "Tag: ${IMAGE_TAG}"

# Build the image
docker build -t "${FULL_IMAGE_NAME}:${IMAGE_TAG}" "$SCRIPT_DIR"

if [ "$TAG_AS_LATEST" = true ]; then
    echo "Tagging as latest..."
    docker tag "${FULL_IMAGE_NAME}:${IMAGE_TAG}" "${FULL_IMAGE_NAME}:latest"
fi

echo "Build completed successfully"

if [ "$PUSH" = true ]; then
    echo "Pushing to registry..."
    
    docker push "${FULL_IMAGE_NAME}:${IMAGE_TAG}"
    
    if [ "$TAG_AS_LATEST" = true ]; then
        docker push "${FULL_IMAGE_NAME}:latest"
    fi
    
    echo "Push completed successfully"
    echo "Image available at: ${FULL_IMAGE_NAME}:${IMAGE_TAG}"
else
    echo "Skipping push (--no-push specified)"
fi

echo "Done!"
