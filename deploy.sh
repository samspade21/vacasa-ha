#!/bin/bash

# Vacasa Home Assistant Integration - Automated Release Deployment
#
# This script fully automates the release process:
# 1. Validates environment and version consistency
# 2. Pushes development branch changes
# 3. Creates and merges PR to main branch
# 4. Triggers GitHub release workflow
# 5. Monitors release completion
# 6. Updates main branch automatically
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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_step() {
    echo -e "\n${BOLD}${CYAN}🚀 $1${NC}"
}

check_prerequisites() {
    log_step "Checking Prerequisites"

    # Check if gh CLI is installed
    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh) is not installed. Please install it first."
        exit 1
    fi

    # Check if gh is authenticated
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

get_version_info() {
    log_step "Reading Version Information"

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

run_tests() {
    log_step "Running Tests"

    # Run pre-commit hooks
    log_info "Running pre-commit hooks..."
    if ! pre-commit run --all-files; then
        log_error "Pre-commit hooks failed"
        exit 1
    fi

    # Run pytest if available
    if [ -f "pytest.ini" ] && command -v pytest &> /dev/null; then
        log_info "Running pytest..."
        if ! pytest; then
            log_error "Tests failed"
            exit 1
        fi
    fi

    log_success "All tests passed"
}

push_development_branch() {
    log_step "Pushing Development Branch"

    # Ensure we have latest changes
    git fetch origin

    # Check if there are any commits to push
    if [ -z "$(git log origin/$REQUIRED_BRANCH..$REQUIRED_BRANCH --oneline)" ]; then
        log_info "No new commits to push on $REQUIRED_BRANCH branch"
    else
        log_info "Pushing commits to origin/$REQUIRED_BRANCH..."
        git push origin $REQUIRED_BRANCH
        log_success "Development branch pushed successfully"
    fi
}

wait_for_ci() {
    log_step "Waiting for CI/CD Validation"

    log_info "Checking GitHub Actions status..."

    # Wait for workflows to complete
    local max_wait=300  # 5 minutes
    local wait_time=0
    local check_interval=10

    while [ $wait_time -lt $max_wait ]; do
        # Check if there are any pending/running workflows
        local status=$(gh run list --branch $REQUIRED_BRANCH --limit 1 --json status --jq '.[0].status')

        if [ "$status" = "completed" ]; then
            local conclusion=$(gh run list --branch $REQUIRED_BRANCH --limit 1 --json conclusion --jq '.[0].conclusion')
            if [ "$conclusion" = "success" ]; then
                log_success "All CI/CD workflows passed"
                return 0
            else
                log_error "CI/CD workflows failed with conclusion: $conclusion"
                gh run list --branch $REQUIRED_BRANCH --limit 3
                exit 1
            fi
        elif [ "$status" = "in_progress" ] || [ "$status" = "queued" ]; then
            log_info "CI/CD workflows still running... (${wait_time}s elapsed)"
            sleep $check_interval
            wait_time=$((wait_time + check_interval))
        else
            log_error "Unexpected workflow status: $status"
            exit 1
        fi
    done

    log_error "CI/CD validation timed out after ${max_wait}s"
    exit 1
}

create_and_merge_pr() {
    log_step "Creating and Merging Pull Request"

    # Create PR title and body
    local pr_title="Release v$VERSION"
    local pr_body="## 🚀 Automated Release v$VERSION

This is an automated release deployment from the development branch.

### 📋 Release Checklist
- ✅ Version updated in VERSION file: \`$VERSION\`
- ✅ Version updated in manifest.json: \`$VERSION\`
- ✅ CHANGELOG.md updated with release notes
- ✅ All tests passing on development branch
- ✅ CI/CD workflows validated

### 📝 Release Notes
$(grep -A 20 "## \[$VERSION\]" CHANGELOG.md | head -20)

### 🔧 Deployment Process
This PR was created and will be merged automatically by the deployment script.
The GitHub release will be triggered immediately after merge."

    # Check if PR already exists
    local existing_pr=$(gh pr list --base $TARGET_BRANCH --head $REQUIRED_BRANCH --json number --jq '.[0].number' 2>/dev/null || echo "")

    if [ -n "$existing_pr" ] && [ "$existing_pr" != "null" ]; then
        log_info "Using existing PR #$existing_pr"
        local pr_number=$existing_pr
    else
        log_info "Creating pull request..."
        local pr_number=$(gh pr create \
            --base $TARGET_BRANCH \
            --head $REQUIRED_BRANCH \
            --title "$pr_title" \
            --body "$pr_body" \
            --json number --jq '.number')

        log_success "Created PR #$pr_number"
    fi

    # Wait for PR checks
    log_info "Waiting for PR checks to complete..."
    local max_wait=300
    local wait_time=0
    local check_interval=10

    while [ $wait_time -lt $max_wait ]; do
        local pr_status=$(gh pr view $pr_number --json statusCheckRollup --jq '.statusCheckRollup[] | select(.state != "SUCCESS") | .state' | head -1)

        if [ -z "$pr_status" ]; then
            log_success "All PR checks passed"
            break
        elif echo "$pr_status" | grep -q "PENDING\|IN_PROGRESS"; then
            log_info "PR checks still running... (${wait_time}s elapsed)"
            sleep $check_interval
            wait_time=$((wait_time + check_interval))
        else
            log_error "PR checks failed with status: $pr_status"
            gh pr view $pr_number --json statusCheckRollup
            exit 1
        fi
    done

    if [ $wait_time -ge $max_wait ]; then
        log_error "PR checks timed out after ${max_wait}s"
        exit 1
    fi

    # Merge the PR
    log_info "Merging pull request..."
    if gh pr merge $pr_number --merge --delete-branch false; then
        log_success "Pull request merged successfully"
    else
        log_error "Failed to merge pull request"
        exit 1
    fi
}

trigger_release() {
    log_step "Triggering GitHub Release"

    # Switch to main branch to trigger release
    git fetch origin
    git checkout $TARGET_BRANCH
    git pull origin $TARGET_BRANCH

    log_info "Triggering release workflow for v$VERSION..."
    if gh workflow run release.yml --field version="v$VERSION"; then
        log_success "Release workflow triggered successfully"
    else
        log_error "Failed to trigger release workflow"
        exit 1
    fi

    # Wait for release workflow to start
    sleep 5

    # Monitor release progress
    log_info "Monitoring release workflow..."
    local max_wait=600  # 10 minutes
    local wait_time=0
    local check_interval=15

    while [ $wait_time -lt $max_wait ]; do
        local release_run=$(gh run list --workflow=release.yml --limit 1 --json status,conclusion --jq '.[0]')
        local status=$(echo "$release_run" | jq -r '.status')
        local conclusion=$(echo "$release_run" | jq -r '.conclusion')

        if [ "$status" = "completed" ]; then
            if [ "$conclusion" = "success" ]; then
                log_success "Release workflow completed successfully"
                break
            else
                log_error "Release workflow failed with conclusion: $conclusion"
                gh run list --workflow=release.yml --limit 1
                exit 1
            fi
        elif [ "$status" = "in_progress" ] || [ "$status" = "queued" ]; then
            log_info "Release workflow running... (${wait_time}s elapsed)"
            sleep $check_interval
            wait_time=$((wait_time + check_interval))
        else
            log_error "Unexpected release workflow status: $status"
            exit 1
        fi
    done

    if [ $wait_time -ge $max_wait ]; then
        log_error "Release workflow timed out after ${max_wait}s"
        exit 1
    fi
}

verify_release() {
    log_step "Verifying Release"

    # Check if GitHub release was created
    if gh release view "v$VERSION" > /dev/null 2>&1; then
        log_success "GitHub release v$VERSION created successfully"

        # Show release details
        echo -e "\n${BOLD}📦 Release Details:${NC}"
        gh release view "v$VERSION" --json tagName,name,createdAt,assets --template '
🏷️  Tag: {{.tagName}}
📝 Name: {{.name}}
📅 Created: {{.createdAt}}
📎 Assets: {{len .assets}} files
'
    else
        log_error "GitHub release v$VERSION not found"
        exit 1
    fi

    # Verify main branch is updated
    git fetch origin
    local main_version=$(git show origin/$TARGET_BRANCH:VERSION 2>/dev/null || echo "")
    if [ "$main_version" = "$VERSION" ]; then
        log_success "Main branch updated with version v$VERSION"
    else
        log_warning "Main branch version ($main_version) doesn't match expected ($VERSION)"
    fi
}

cleanup_and_switch_back() {
    log_step "Final Cleanup"

    # Switch back to development branch
    git checkout $REQUIRED_BRANCH
    git pull origin $REQUIRED_BRANCH

    log_success "Switched back to development branch"
}

# Main execution flow
main() {
    echo -e "${BOLD}${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║               Vacasa Integration Release Deployment          ║"
    echo "║                     Automated Release Process                ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"

    # Execute deployment steps
    check_prerequisites
    get_version_info
    run_tests
    push_development_branch
    wait_for_ci
    create_and_merge_pr
    trigger_release
    verify_release
    cleanup_and_switch_back

    # Final success message
    echo -e "\n${BOLD}${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                   🎉 DEPLOYMENT SUCCESSFUL! 🎉               ║"
    echo "║                                                              ║"
    echo "║   ✅ Version v$VERSION has been released successfully        ║"
    echo "║   ✅ GitHub release created with assets                      ║"
    echo "║   ✅ Main branch updated automatically                       ║"
    echo "║   ✅ Ready for HACS distribution                             ║"
    echo "║                                                              ║"
    echo "║   🔗 View release: https://github.com/samspade21/vacasa-ha   ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"

    log_info "Next steps:"
    echo "  • Monitor HACS integration for automatic updates"
    echo "  • Check community feedback and issues"
    echo "  • Continue development on the development branch"
}

# Run main function
main "$@"
