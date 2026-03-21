#!/bin/bash

# Vacasa Home Assistant Integration - Release Deployment
#
# Creates a versioned release branch, bumps VERSION + manifest.json,
# validates CHANGELOG.md has an entry, then opens a PR to main.
# GitHub Actions auto-tag and auto-release on merge.
#
# Usage:   ./new-prod-release.sh <version>
# Example: ./new-prod-release.sh 1.8.0
#
# Prerequisites:
#   - Must be on main branch (clean working directory)
#   - CHANGELOG.md must have a ## [<version>] entry
#   - GitHub CLI (gh) must be authenticated

set -e

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
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
    echo "  Example: $0 1.8.0"
    exit 1
fi

VERSION="$1"
TAG="v$VERSION"
RELEASE_BRANCH="release/$TAG"

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

    # Allow only release-related files to be modified
    local unexpected
    unexpected=$(git status --porcelain | grep -v '^ M CHANGELOG.md' | grep -v '^ M new-prod-release.sh' | grep -v '^??' || true)
    if [ -n "$unexpected" ]; then
        log_error "Unexpected uncommitted changes. Commit or stash non-release changes first."
        echo "$unexpected"
        exit 1
    fi

    # Pull latest main
    git pull origin main --quiet
    log_success "Prerequisites validated (on main, up to date)"
}

# ── Validate CHANGELOG ─────────────────────────────────────────────────────────
validate_changelog() {
    log_step "Validating CHANGELOG.md"

    if ! grep -q "## \[$VERSION\]" CHANGELOG.md; then
        log_error "CHANGELOG.md has no entry for [$VERSION]."
        log_info  "Add an entry starting with: ## [$VERSION] - $(date +%Y-%m-%d)"
        exit 1
    fi

    # Warn if tag already exists
    if git tag -l | grep -q "^$TAG$"; then
        log_error "Tag $TAG already exists. Has this version already been released?"
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

# ── Create release branch, commit, push, open PR ──────────────────────────────
create_release_pr() {
    log_step "Creating Release PR"

    git checkout -b "$RELEASE_BRANCH"
    git add VERSION custom_components/vacasa/manifest.json CHANGELOG.md new-prod-release.sh
    git commit -m "chore: bump version to $VERSION"

    git push -u origin "$RELEASE_BRANCH"
    log_success "Pushed $RELEASE_BRANCH"

    # Extract changelog section for PR body
    local notes
    notes=$(python3 - <<PYEOF
import re, sys
with open("CHANGELOG.md") as f:
    content = f.read()
m = re.search(r'## \[$VERSION\][^\n]*\n(.*?)(?=\n## \[|\Z)', content, re.DOTALL)
print(m.group(1).strip() if m else "See CHANGELOG.md")
PYEOF
)

    gh pr create \
        --base main \
        --head "$RELEASE_BRANCH" \
        --title "Release $TAG" \
        --body "$(cat <<EOF
## Release $TAG

### Changes
$notes

### Automated steps on merge
- GitHub Actions creates tag \`$TAG\`
- Release workflow builds archive and publishes GitHub Release
- HACS notified for distribution

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"

    local pr_url
    pr_url=$(gh pr list --base main --head "$RELEASE_BRANCH" --json url -q '.[0].url')
    log_success "PR created: $pr_url"
}

# ── Main ───────────────────────────────────────────────────────────────────────
main() {
    echo -e "${BOLD}${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║           Vacasa Integration — Create Release PR             ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    check_prerequisites
    validate_changelog
    bump_versions
    create_release_pr

    echo -e "\n${BOLD}${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              🎉 Release PR Ready! 🎉                        ║"
    echo "║                                                              ║"
    echo "║  Review the PR, confirm all checks pass, then merge.        ║"
    echo "║  GitHub Actions will tag, build, and publish automatically. ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo "  Monitor: https://github.com/samspade21/vacasa-ha/actions"
    echo ""
}

main "$@"
