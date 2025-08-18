# Deployment Guide - Automated Release Process

## Overview

The Vacasa Home Assistant Integration uses a fully automated deployment process that handles the entire release workflow from development branch to production release on GitHub and HACS distribution.

## 🚀 Quick Start

```bash
# 1. Update version and changelog on development branch
# 2. Commit all changes
# 3. Run the automated deployment
./deploy.sh
```

That's it! The script handles everything automatically.

---

## 📋 Prerequisites

### Required Tools
- **Git** - Version control
- **GitHub CLI (gh)** - GitHub API access
- **Python 3.9+** - For version validation scripts
- **Pre-commit** - Code quality hooks (optional but recommended)

### Setup Instructions

1. **Install GitHub CLI**:
   ```bash
   # macOS
   brew install gh

   # Ubuntu/Debian
   sudo apt install gh

   # Windows
   winget install GitHub.CLI
   ```

2. **Authenticate with GitHub**:
   ```bash
   gh auth login
   ```

3. **Verify Prerequisites**:
   ```bash
   gh auth status
   git status
   ```

---

## 📦 Release Process

### Step 1: Prepare Release on Development Branch

1. **Update Version Information**:
   ```bash
   # Update VERSION file
   echo "1.4.0" > VERSION

   # Update manifest.json version
   # Edit custom_components/vacasa/manifest.json
   ```

2. **Update CHANGELOG.md**:
   ```markdown
   ## [1.4.0] - 2025-XX-XX

   ### Added
   - New feature descriptions

   ### Fixed
   - Bug fix descriptions

   ### Changed
   - Change descriptions
   ```

3. **Commit Changes**:
   ```bash
   git add VERSION custom_components/vacasa/manifest.json CHANGELOG.md
   git commit -m "chore: prepare release v1.4.0"
   ```

### Step 2: Execute Automated Deployment

```bash
./deploy.sh
```

The script will automatically:
- ✅ Validate prerequisites and environment
- ✅ Check version consistency across files
- ✅ Run tests and pre-commit hooks
- ✅ Push development branch to GitHub
- ✅ Wait for CI/CD validation to complete
- ✅ Create pull request from development to main
- ✅ Wait for PR checks and merge automatically
- ✅ Trigger GitHub release workflow
- ✅ Monitor release completion
- ✅ Verify release creation and main branch update
- ✅ Switch back to development branch

---

## 🔍 What the Script Does

### Phase 1: Validation
- Checks if GitHub CLI is installed and authenticated
- Verifies you're on the development branch
- Ensures working directory is clean
- Validates version consistency between VERSION file and manifest.json
- Confirms CHANGELOG.md has entry for the new version

### Phase 2: Testing
- Runs pre-commit hooks for code quality
- Executes pytest if available
- Ensures all tests pass before proceeding

### Phase 3: Development Branch Deployment
- Pushes latest development branch changes to GitHub
- Waits for CI/CD workflows to complete successfully
- Validates all GitHub Actions pass (linting, testing, HACS validation)

### Phase 4: Main Branch Integration
- Creates pull request from development to main branch
- Waits for PR status checks to complete
- Automatically merges the PR when all checks pass

### Phase 5: Release Creation
- Switches to main branch and pulls latest changes
- Triggers GitHub release workflow via `gh workflow run`
- Monitors release workflow progress
- Waits for successful completion

### Phase 6: Verification & Cleanup
- Verifies GitHub release was created successfully
- Checks that main branch version matches release version
- Switches back to development branch
- Displays success summary with release links

---

## 🛠️ Manual Steps (If Needed)

### Emergency Manual Release

If the automated script fails, you can manually execute the process:

```bash
# 1. Push development branch
git push origin development

# 2. Create PR manually
gh pr create --base main --head development --title "Release vX.X.X"

# 3. Merge PR after checks pass
gh pr merge --merge

# 4. Trigger release workflow
git checkout main && git pull
gh workflow run release.yml --field version="vX.X.X"

# 5. Monitor release
gh run list --workflow=release.yml
```

### Rollback Process

If a release needs to be rolled back:

```bash
# 1. Delete the GitHub release
gh release delete vX.X.X

# 2. Delete the git tag
git tag -d vX.X.X
git push origin :refs/tags/vX.X.X

# 3. Revert main branch if needed
git checkout main
git revert <commit-hash>
git push origin main
```

---

## 📊 Monitoring and Validation

### GitHub Actions Workflows

The deployment process triggers several workflows:
- **CI Workflow**: Linting, testing across Python versions, security scans
- **Dependencies Workflow**: Dependency monitoring and updates
- **Release Workflow**: Version validation, HACS validation, release creation

### Release Artifacts

Successful releases create:
- GitHub release with changelog and downloadable assets
- Git tag (vX.X.X format)
- Release archive (vacasa-X.X.X.zip)
- Updated main branch with version bump

### HACS Integration

After release:
- HACS automatically detects new releases
- Users receive update notifications
- Integration becomes available for easy installation

---

## 🚨 Troubleshooting

### Common Issues

#### "GitHub CLI not authenticated"
```bash
gh auth login
gh auth status
```

#### "Working directory not clean"
```bash
git status
git add . && git commit -m "cleanup"
# or
git stash
```

#### "Version mismatch between files"
- Ensure VERSION file and manifest.json have the same version
- Check CHANGELOG.md has an entry for the new version

#### "CI/CD workflows failed"
- Check GitHub Actions tab for specific error details
- Fix failing tests or linting issues
- Re-run the deployment script

#### "PR merge failed due to branch protection"
- Ensure branch protection rules allow the merge
- Check that all required status checks pass
- May need admin privileges for protected main branch

### Debug Mode

For verbose output during deployment:
```bash
# Enable bash debug mode
bash -x ./deploy.sh
```

### Logs and Monitoring

Monitor deployment progress:
```bash
# Watch GitHub Actions
gh run list --limit 10

# View specific workflow run
gh run view <run-id>

# Check releases
gh release list
```

---

## 🔧 Customization

### Script Configuration

Edit `deploy.sh` to modify:
- Branch names (REQUIRED_BRANCH, TARGET_BRANCH)
- Timeout values for CI/CD waiting
- PR template and release notes format
- Validation requirements

### Workflow Integration

The script integrates with GitHub Actions workflows:
- `.github/workflows/ci.yml` - Main CI/CD pipeline
- `.github/workflows/release.yml` - Release automation
- `.github/workflows/dependencies.yml` - Dependency monitoring

---

## 📈 Best Practices

### Version Management
- Use semantic versioning (MAJOR.MINOR.PATCH)
- Update CHANGELOG.md for every release
- Keep VERSION file and manifest.json in sync

### Development Workflow
- Always work on development branch
- Test thoroughly before releasing
- Use meaningful commit messages
- Follow conventional commit format

### Release Schedule
- Release regularly with small, focused changes
- Test releases in staging environment first
- Monitor community feedback after releases
- Keep release notes comprehensive and user-friendly

---

## 📚 Additional Resources

- [GitHub CLI Documentation](https://cli.github.com/manual/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [HACS Documentation](https://hacs.xyz/)
- [Home Assistant Integration Development](https://developers.home-assistant.io/)
- [Semantic Versioning](https://semver.org/)

---

## 🤝 Contributing

When contributing to the deployment process:
1. Test changes thoroughly in a fork first
2. Update this documentation for any process changes
3. Ensure backward compatibility with existing workflows
4. Follow the established patterns and conventions

For questions or issues with the deployment process, please open a GitHub issue with the `deployment` label.
