#!/usr/bin/env bash
set -euo pipefail

# Deployment script for Hugging Face Spaces
# Usage: ./scripts/deploy.sh [--stub <IMAGE_TAG>] <space_name>

# Tag formatting and stub logic
STUB_IMAGE=""
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --stub) STUB_IMAGE="$2"; shift ;;
        *) SPACE_NAME="$1" ;;
    esac
    shift
done

if [ -z "${SPACE_NAME:-}" ]; then
    echo "Usage: $0 [--stub <IMAGE_TAG>] <space_name>"
    exit 1
fi

if [ -z "${HF_TOKEN:-}" ]; then
    echo "Error: HF_TOKEN environment variable must be set."
    exit 1
fi

# Ensure working directory is clean (skipped if --stub is used since we are making an orphan)
if [ -z "${STUB_IMAGE}" ] && [ -z "${GITHUB_ACTIONS:-}" ] && ! git diff --quiet; then
    echo "Error: Working directory must be clean before deploying locally. Please commit or stash your changes."
    exit 1
fi

if [ -n "${GITHUB_ACTIONS:-}" ]; then
    git config user.email "github-actions@github.com"
    git config user.name "GitHub Actions"
fi

# Make sure we are at the root of the repo
cd "$(dirname "$0")/.."

# Store original ref for cleanup
ORIGINAL_REF=$(git symbolic-ref -q --short HEAD || git rev-parse HEAD)
function cleanup() {
  if [[ "$(git branch --show-current)" == "hf-snapshot" ]]; then
    git checkout "$ORIGINAL_REF" 2>/dev/null || true
  fi
  git branch -D hf-snapshot 2>/dev/null || true
  git config --local --unset credential.https://huggingface.co.helper 2>/dev/null || true
  git remote remove hf 2>/dev/null || true
}
trap cleanup EXIT

# Setup remote
git remote remove hf 2>/dev/null || true
git remote add hf "https://huggingface.co/spaces/${SPACE_NAME}"
git config --local credential.https://huggingface.co.helper '!f() { echo "username=api"; echo "password=${HF_TOKEN}"; }; f'

# Create the deployment snapshot
git branch -D hf-snapshot 2>/dev/null || true
git checkout --orphan hf-snapshot

if [ -n "${STUB_IMAGE}" ]; then
    echo "Creating stub deployment for image: ${STUB_IMAGE}"
    git rm -rf . 2>/dev/null || true
    echo "FROM ${STUB_IMAGE}" > Containerfile
    git add Containerfile
    COMMIT_MSG="deploy: image ${STUB_IMAGE}"
else
    COMMIT_MSG="deploy: $(git log -1 --format='%s')"
    # Remove cache files from index and working tree so they aren't committed to HF
    git rm -rf --ignore-unmatch pdf_cache/ 2>/dev/null || true
fi

# Commit the snapshot
git commit -m "$COMMIT_MSG"

# Force push to Hugging Face
git push hf hf-snapshot:main --force --no-verify

echo "Deployment to ${SPACE_NAME} complete!"
