#!/bin/bash

# Vacasa Home Assistant Integration - Simple Release Deployment
#
# This script creates a pull request from development to main.
# GitHub Actions handle the rest of the automation automatically.
#
# Usage: ./deploy.sh
# Prerequisites:
#   - Must be on development branch
#   - VERSION file and manifest.json must be updated
#   - CHANGELOG.md must be updated
#   - GitHub CLI (gh) must be authenticated

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
REQUIRED_BRANCH="development"
TARGET_BRANCH="main"

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_step() {
    echo -e "\n${BOLD}${CYAN}🚀 $1${NC}"
}

check_prerequisites() {
    log_step "Checking Prerequisites"

    # Check if gh CLI is installed and authenticated
    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh) is not installed. Please install it first."
        exit 1
    fi

    if ! gh auth status &> /dev/null; then
        log_error "GitHub CLI is not authenticated. Please run 'gh auth login' first."
        exit 1
    fi

    # Check if we're on the correct branch
    current_branch=$(git branch --show-current)
    if [ "$current_branch" != "$REQUIRED_BRANCH" ]; then
        log_error "Must be on $REQUIRED_BRANCH branch. Currently on: $current_branch"
        exit 1
    fi

    # Check if working directory is clean
    if [ -n "$(git status --porcelain)" ]; then
        log_error "Working directory is not clean. Please commit or stash changes first."
        git status --short
        exit 1
    fi

    log_success "Prerequisites validated"
}

validate_version_info() {
    log_step "Validating Version Information"

    # Read version from VERSION file
    if [ ! -f "VERSION" ]; then
        log_error "VERSION file not found"
        exit 1
    fi

    VERSION=$(cat VERSION | tr -d '[:space:]')
    if [ -z "$VERSION" ]; then
        log_error "VERSION file is empty"
        exit 1
    fi

    # Read version from manifest.json
    if [ ! -f "custom_components/vacasa/manifest.json" ]; then
        log_error "manifest.json not found"
        exit 1
    fi

    MANIFEST_VERSION=$(python3 -c "import json; print(json.load(open('custom_components/vacasa/manifest.json'))['version'])")

    # Validate version consistency
    if [ "$VERSION" != "$MANIFEST_VERSION" ]; then
        log_error "Version mismatch: VERSION file ($VERSION) != manifest.json ($MANIFEST_VERSION)"
        exit 1
    fi

    # Check if CHANGELOG.md contains the version
    if ! grep -q "## \[$VERSION\]" CHANGELOG.md; then
        log_error "CHANGELOG.md does not contain entry for version $VERSION"
        log_info "Please add a changelog entry starting with: ## [$VERSION] - $(date +%Y-%m-%d)"
        exit 1
    fi

    log_success "Version information validated: v$VERSION"
    echo "  📁 VERSION file: $VERSION"
    echo "  📋 manifest.json: $MANIFEST_VERSION"
    echo "  📝 CHANGELOG.md: Entry found"
}

push_and_create_pr() {
    log_step "Creating Release Pull Request"

    # Push development branch
    git push origin $REQUIRED_BRANCH
    log_success "Pushed $REQUIRED_BRANCH branch to GitHub"

    # Create PR title and body
    local pr_title="Release v$VERSION"
    local pr_body="## 🚀 Release v$VERSION

This PR contains the release preparations for version $VERSION.

### 📋 Release Checklist
- ✅ Version updated in VERSION file: \`$VERSION\`
- ✅ Version updated in manifest.json: \`$VERSION\`
- ✅ CHANGELOG.md updated with release notes

### 📝 Release Notes
$(grep -A 20 "## \[$VERSION\]" CHANGELOG.md | head -20)

### 🤖 Automated Process
- ✅ Upon merge, GitHub Actions will automatically create tag \`v$VERSION\`
- ✅ Tag creation will trigger the release workflow
- ✅ GitHub release will be created with changelog and assets
- ✅ HACS will be notified for distribution

**No manual steps required after merge - everything is automated!** 🎉"

    # Check if PR already exists
    local existing_pr=$(gh pr list --base $TARGET_BRANCH --head $REQUIRED_BRANCH --json number --jq '.[0].number' 2>/dev/null || echo "")

    if [ -n "$existing_pr" ] && [ "$existing_pr" != "null" ]; then
        log_success "Existing PR #$existing_pr found"
        local pr_number=$existing_pr

        # Update PR body
        gh pr edit $pr_number --body "$pr_body"
        log_success "Updated PR #$pr_number with latest information"
    else
        # Create new PR
        local pr_number=$(gh pr create \
            --base $TARGET_BRANCH \
            --head $REQUIRED_BRANCH \
            --title "$pr_title" \
            --body "$pr_body" \
            --json number --jq '.number')

        log_success "Created PR #$pr_number"
    fi

    # Display PR information
    echo -e "\n${BOLD}📋 Pull Request Created:${NC}"
    echo "  🔗 URL: $(gh pr view $pr_number --json url --jq '.url')"
    echo "  📝 Title: $pr_title"
    echo "  🎯 Version: v$VERSION"
}

# Main execution flow
main() {
    echo -e "${BOLD}${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║               Vacasa Integration Release Deployment          ║"
    echo "║                  Create Release Pull Request                 ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"

    # Execute deployment steps
    check_prerequisites
    validate_version_info
    push_and_create_pr

    # Success message with next steps
    echo -e "\n${BOLD}${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                 🎉 PR CREATED SUCCESSFULLY! 🎉               ║"
    echo "║                                                              ║"
    echo "║  ✅ Release PR ready for review and merge                    ║"
    echo "║  🤖 GitHub Actions will handle everything after merge       ║"
    echo "║  🏷️ Auto-tagging → Release workflow → HACS distribution    ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"

    log_info "Next steps:"
    echo "  1. Review the PR and ensure all checks pass"
    echo "  2. Merge the PR when ready"
    echo "  3. GitHub Actions will automatically:"
    echo "     • Create git tag v$VERSION"
    echo "     • Trigger release workflow"
    echo "     • Create GitHub release with assets"
    echo "     • Notify HACS for distribution"
    echo ""
    echo "  🔗 Monitor progress: https://github.com/samspade21/vacasa-ha/actions"
}

# Run main function
main "$@"
