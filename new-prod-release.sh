#!/bin/bash

# Vacasa Home Assistant Integration - Release Deployment
#
# Bumps VERSION + manifest.json, opens a short-lived PR to main,
# and merges it. GitHub Actions detects the VERSION change, creates
# the git tag, builds the release archive, and publishes to GitHub
# Releases. The temporary PR branch is deleted after merge.
#
# Usage:   ./new-prod-release.sh <version>
# Example: ./new-prod-release.sh 1.9.0
#
# Prerequisites:
#   - Must be on main branch (clean, up to date)
#   - CHANGELOG.md must have a ## [<version>] entry
#   - GitHub CLI (gh) must be authenticated

set -e

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_error()   { echo -e "${RED}❌ $1${NC}"; }
log_step()    { echo -e "\n${BOLD}${CYAN}🚀 $1${NC}"; }

# ── Argument validation ────────────────────────────────────────────────────────
if [ -z "$1" ]; then
    log_error "Version argument required."
    echo "  Usage:   $0 <version>"
    echo "  Example: $0 1.9.0"
    exit 1
fi

VERSION="$1"
TAG="v$VERSION"
BUMP_BRANCH="bump/version-$VERSION"

# ── Prerequisites ──────────────────────────────────────────────────────────────
check_prerequisites() {
    log_step "Checking Prerequisites"

    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh) is not installed."
        exit 1
    fi

    if ! gh auth status &> /dev/null; then
        log_error "GitHub CLI is not authenticated. Run 'gh auth login' first."
        exit 1
    fi

    local current_branch
    current_branch=$(git branch --show-current)
    if [ "$current_branch" != "main" ]; then
        log_error "Must be on main branch. Currently on: $current_branch"
        exit 1
    fi

    # Allow only release-related files to be pre-modified
    local unexpected
    unexpected=$(git status --porcelain | grep -v '^ M CHANGELOG.md' | grep -v '^ M new-prod-release.sh' | grep -v '^??' || true)
    if [ -n "$unexpected" ]; then
        log_error "Unexpected uncommitted changes. Commit or stash them first."
        echo "$unexpected"
        exit 1
    fi

    git pull origin main --quiet
    log_success "On main, clean, up to date"

    if git tag -l | grep -q "^$TAG$"; then
        log_error "Tag $TAG already exists — already released?"
        exit 1
    fi
}

# ── Validate CHANGELOG ─────────────────────────────────────────────────────────
validate_changelog() {
    log_step "Validating CHANGELOG.md"

    if ! grep -q "## \[$VERSION\]" CHANGELOG.md; then
        log_error "CHANGELOG.md has no entry for [$VERSION]."
        log_info  "Add an entry starting with: ## [$VERSION] - $(date +%Y-%m-%d)"
        exit 1
    fi

    log_success "CHANGELOG.md entry found for $VERSION"
}

# ── Bump version files ─────────────────────────────────────────────────────────
bump_versions() {
    log_step "Bumping Version Files to $VERSION"

    echo "$VERSION" > VERSION
    log_success "VERSION → $VERSION"

    python3 - <<PYEOF
import json
path = "custom_components/vacasa/manifest.json"
with open(path) as f:
    data = json.load(f)
data["version"] = "$VERSION"
with open(path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PYEOF
    log_success "manifest.json → $VERSION"
}

# ── PR, wait for checks, merge, delete branch ─────────────────────────────────
create_and_merge_pr() {
    log_step "Creating Version Bump PR"

    git checkout -b "$BUMP_BRANCH"
    git add VERSION custom_components/vacasa/manifest.json CHANGELOG.md new-prod-release.sh
    git commit -m "chore: release $TAG"
    git push -u origin "$BUMP_BRANCH"
    log_success "Pushed $BUMP_BRANCH"

    # Extract changelog section for PR body
    local notes
    notes=$(python3 - <<PYEOF
import re
with open("CHANGELOG.md") as f:
    content = f.read()
m = re.search(r'## \[$VERSION\][^\n]*\n(.*?)(?=\n## \[|\Z)', content, re.DOTALL)
print(m.group(1).strip() if m else "See CHANGELOG.md")
PYEOF
)

    local pr_url
    pr_url=$(gh pr create \
        --base main \
        --head "$BUMP_BRANCH" \
        --title "chore: release $TAG" \
        --body "$(cat <<EOF
## Release $TAG

$notes

---
*On merge: GitHub Actions creates tag \`$TAG\`, builds archive, and publishes the GitHub Release.*
EOF
)" | tail -1)

    log_success "PR: $pr_url"
    log_info "Waiting for CI checks..."

    # Wait for all checks to pass (up to 10 min)
    local pr_number
    pr_number=$(gh pr list --base main --head "$BUMP_BRANCH" --json number -q '.[0].number')
    gh pr checks "$pr_number" --watch --fail-fast

    log_step "Merging PR and Deleting Branch"
    gh pr merge "$pr_number" --squash --delete-branch
    log_success "Merged and branch deleted"

    # Update local main
    git checkout main
    git pull origin main --quiet
    log_success "Local main updated"
}

# ── Main ───────────────────────────────────────────────────────────────────────
main() {
    echo -e "${BOLD}${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║             Vacasa Integration — Release $TAG               ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    check_prerequisites
    validate_changelog
    bump_versions
    create_and_merge_pr

    echo -e "\n${BOLD}${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              🎉 Release Triggered! 🎉                       ║"
    echo "║                                                              ║"
    echo "║  GitHub Actions will tag, build, and publish automatically. ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo "  Monitor: https://github.com/samspade21/vacasa-ha/actions"
    echo "  Release: https://github.com/samspade21/vacasa-ha/releases/tag/$TAG"
    echo ""
}

main "$@"
