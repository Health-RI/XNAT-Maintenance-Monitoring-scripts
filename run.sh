#!/bin/bash

# XNAT Scripts Docker Runner
# This script builds and runs the XNAT reporting scripts in a Docker container
# with the current directory mounted as a volume.

set -e

IMAGE_NAME="xnat-scripts"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to display usage
usage() {
    echo "Usage: $0 <script_name> [script_args...]"
    echo ""
    echo "Examples:"
    echo "  $0 users_per_project --xnat_url https://xnat.health-ri.nl"
    echo "  $0 disk_usages --xnat_url https://xnat.health-ri.nl --report_path report.txt --study_overview overview.csv"
    echo ""
    echo "The current directory will be mounted into the container, so input and output files"
    echo "should be placed in the current working directory."
}

# Check if at least one argument is provided
if [ $# -eq 0 ]; then
    usage
    exit 1
fi

# Build the Docker image
echo "Building Docker image..."
docker build -t "$IMAGE_NAME" "$SCRIPT_DIR"

# Run the container with current directory mounted
echo "Running script: $1"
docker run --rm -it -v "$(pwd)":/data "$IMAGE_NAME" "$@"