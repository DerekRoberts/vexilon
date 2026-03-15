# Usage: ./scripts/deploy.sh <image_tag> [--prod] [--dry-run]
# Default: Targets "DerekRoberts/landru" (TEST).
# Use --prod as second argument to target "DerekRoberts/vexilon".

# Strict mode + Trace
set -euo pipefail
set -x

IMAGE_TAG="${1:-}"
MODE="${2:-}"
DRY_RUN=false

if [ -z "$IMAGE_TAG" ]; then
    echo "Error: Image tag (e.g. 'latest' or 'sha-123') must be provided."
    exit 1
fi

SPACE_NAME="DerekRoberts/landru"
if [[ "$MODE" == "--prod" ]]; then
    echo "[safety] Production mode enabled."
    SPACE_NAME="DerekRoberts/vexilon"
fi

# Detect --dry-run in any position
for arg in "$@"; do
    [[ "$arg" == "--dry-run" ]] && DRY_RUN=true
done

if [ -z "${HF_TOKEN:-}" ] && [ "$DRY_RUN" == "false" ]; then
    echo "Error: HF_TOKEN environment variable must be set."
    exit 1
fi

# Ensure working directory is clean before proceeding locally
if [ -z "${GITHUB_ACTIONS:-}" ] && [ "$DRY_RUN" == "false" ] && ! git diff --quiet; then
    echo "Error: Working directory must be clean before deploying locally."
    exit 1
fi

# Make sure we are at the root of the repo
cd "$(dirname "$0")/.."
ORIGINAL_REF=$(git symbolic-ref -q --short HEAD || git rev-parse HEAD)

function cleanup() {
  git checkout "$ORIGINAL_REF" 2>/dev/null || true
  git branch -D hf-snapshot 2>/dev/null || true
  git remote remove hf 2>/dev/null || true
}
trap cleanup EXIT

# Create an orphaned branch and clear it
git branch -D hf-snapshot 2>/dev/null || true
git checkout --orphan hf-snapshot
git reset # Clears the index, but files remain on disk

# We only want README.md and Dockerfile in the commit
# We use a temp backup to avoid losing README if we were to git checkout elsewhere
TMP_README=$(mktemp)
cp README.md "$TMP_README"

# Create the Stub Dockerfile
cat <<EOF > Dockerfile
FROM ghcr.io/derekroberts/vexilon:$IMAGE_TAG
EOF

if [ "$DRY_RUN" == "true" ]; then
    echo "--- DRY RUN MODE ---"
    echo "Target: $SPACE_NAME"
    echo "Image:  $IMAGE_TAG"
    echo "Dockerfile content:"
    cat Dockerfile
    echo "--- DRY RUN COMPLETE ---"
    exit 0
fi

if [ -n "${GITHUB_ACTIONS:-}" ]; then
    git config user.email "github-actions@github.com"
    git config user.name "GitHub Actions"
fi

# Re-add only what we need
git add Dockerfile
cp "$TMP_README" README.md && git add README.md
rm "$TMP_README"

git commit -m "promote: $IMAGE_TAG from $ORIGINAL_REF"

# Auth and Push
git remote add hf "https://huggingface.co/spaces/${SPACE_NAME}" 2>/dev/null || true
git config --local credential.https://huggingface.co.helper '!f() { echo "username=api"; echo "password=${HF_TOKEN}"; }; f'
git push hf hf-snapshot:main --force --no-verify

echo "Deployment to ${SPACE_NAME} complete!"
