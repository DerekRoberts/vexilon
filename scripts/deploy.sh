#!/usr/bin/env bash
set -euo pipefail

# Deployment script for Hugging Face Spaces
# Usage: ./scripts/deploy.sh <space_name>

if [ -z "${1:-}" ]; then
    echo "Error: Space name must be provided."
    echo "Usage: $0 <space_name>"
    exit 1
fi

SPACE_NAME=$1

if [ -z "${HF_TOKEN:-}" ]; then
    echo "Error: HF_TOKEN environment variable must be set."
    exit 1
fi

# Ensure working directory is clean before proceeding locally
if [ -z "${GITHUB_ACTIONS:-}" ] && ! git diff --quiet; then
    echo "Error: Working directory must be clean before deploying locally. Please commit or stash your changes."
    exit 1
fi

if [ -n "${GITHUB_ACTIONS:-}" ]; then
    git config user.email "github-actions@github.com"
    git config user.name "GitHub Actions"
fi

# Make sure we are at the root of the repo
cd "$(dirname "$0")/.."

# Remove the remote if it already exists
git remote remove hf 2>/dev/null || true
git remote add hf "https://DerekRoberts:${HF_TOKEN}@huggingface.co/spaces/${SPACE_NAME}"

COMMIT_MSG=$(git log -1 --format='%s')

# Store current branch
CURRENT_BRANCH=$(git branch --show-current)

# Create an orphaned branch for the snapshot (fails if branch already exists, so delete it first)
git branch -D hf-snapshot 2>/dev/null || true
git checkout --orphan hf-snapshot

# Remove cache files from index
git rm --cached -r pdf_cache/ 2>/dev/null || true

# Commit the code-only snapshot
git commit -m "deploy: $COMMIT_MSG"

# Force push to Hugging Face
git push hf hf-snapshot:main --force

# Cleanup
if [ -n "$CURRENT_BRANCH" ]; then
    git checkout "$CURRENT_BRANCH"
else
    git checkout -
fi
git branch -D hf-snapshot 2>/dev/null || true
git remote remove hf 2>/dev/null || true

echo "Deployment to ${SPACE_NAME} complete!"
