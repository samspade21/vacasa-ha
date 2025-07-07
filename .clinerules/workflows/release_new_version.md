# Release Process for Vacasa Home Assistant Integration

This document outlines the step-by-step process for creating a new release of the Vacasa Home Assistant integration.

## Pre-Release Checklist

### 1. Ensure Development Branch is Ready
- [ ] All features and fixes are complete
- [ ] Code has been tested on a real Home Assistant instance
- [ ] All GitHub Actions are passing on the development branch
- [ ] Pre-commit hooks are passing locally

### 2. Version Planning
- [ ] Determine the version number based on changes:
  - **Patch** (x.x.X): Bug fixes and minor improvements
  - **Minor** (x.X.x): New features, backward compatible
  - **Major** (X.x.x): Breaking changes

## Release Steps

### Step 1: Update Version Numbers

Update the version in these files:
- [ ] `custom_components/vacasa/manifest.json` - Update the "version" field
- [ ] `VERSION` - Update the version number

**Example Commands:**
```bash
# Update manifest.json (replace X.X.X with new version)
sed -i 's/"version": "1.1.1"/"version": "1.1.2"/' custom_components/vacasa/manifest.json

# Update VERSION file
echo "1.1.2" > VERSION
```

### Step 2: Update Documentation

#### Update CHANGELOG.md
Add a new entry at the top of the changelog with:
- [ ] Version number and release date
- [ ] **Added** section for new features
- [ ] **Improved** section for enhancements
- [ ] **Fixed** section for bug fixes
- [ ] **Changed** section for modifications
- [ ] Focus on user-facing changes and code improvements

**Example Format:**
```markdown
## [1.1.2] - 2025-01-07

### Added
- **Enhanced Options Flow**: Users can now update credentials directly

### Improved
- **User Experience**: Better validation and error handling

### Fixed
- **Configuration Persistence**: Resolved reload requirement issue
```

#### Check README.md
- [ ] Review README.md for any updates needed
- [ ] Ensure version references are current
- [ ] Verify installation instructions are accurate

### Step 3: Git Workflow

#### Commit Changes
```bash
# Check current branch
git branch

# Add all changes
git add .

# Commit with descriptive message
git commit -m "Release v1.1.2: Enhanced credential management and automatic reload"
```

#### Run Pre-commit Validation
```bash
# Run pre-commit hooks to ensure code quality
pre-commit run --all-files

# Fix any issues that arise and commit again if needed
```

#### Merge to Main Branch
```bash
# Switch to main branch
git checkout main

# Merge development branch
git merge development

# Push to remote
git push origin main
```

### Step 4: Create Release Tag

```bash
# Create annotated tag
git tag -a v1.1.2 -m "Release v1.1.2: Enhanced credential management"

# Push tag to remote
git push origin v1.1.2
```

### Step 5: Create GitHub Release

1. [ ] Go to GitHub repository
2. [ ] Click "Releases" → "Create a new release"
3. [ ] Select the tag `v1.1.2`
4. [ ] Set release title: `v1.1.2 - Enhanced Credential Management`
5. [ ] Copy release notes from CHANGELOG.md
6. [ ] Mark as latest release
7. [ ] Publish release

**Sample Release Notes Template:**
```markdown
## What's New in v1.1.2

### 🚀 Enhanced Credential Management
- Users can now update Vacasa credentials directly in integration settings
- No more need to delete and recreate the integration for credential changes

### ⚡ Automatic Configuration Reload
- All configuration changes now take effect immediately
- Improved user experience with instant feedback

### 🛠️ Improvements
- Enhanced validation and error handling
- Better user guidance and translations
- Streamlined configuration flow logic

## Installation
Install via HACS or manually download the latest release files.

## Upgrade Notes
This release is fully backward compatible. Existing integrations will continue to work without changes.
```

## Post-Release Checklist

### Validation
- [ ] Verify GitHub Actions pass on main branch
- [ ] Check that the release appears in GitHub releases
- [ ] Confirm HACS validation (if applicable)
- [ ] Test installation from released version

### Documentation
- [ ] Update any external documentation if needed
- [ ] Announce release in relevant communities if appropriate

### Next Development Cycle
- [ ] Switch back to development branch for future work
- [ ] Create or update issue tracking for next release features

```bash
# Switch back to development
git checkout development

# Merge main to keep development up to date
git merge main
```

## Troubleshooting

### Pre-commit Failures
If pre-commit hooks fail:
1. Fix the reported issues (formatting, linting, etc.)
2. Run `pre-commit run --all-files` again
3. Commit the fixes

### GitHub Actions Failures
If GitHub Actions fail after push:
1. Check the Actions tab for error details
2. Fix the issues locally
3. Push the fixes

### Common Issues
- **Version conflicts**: Ensure all version numbers match
- **Changelog format**: Follow the established format exactly
- **Tag already exists**: Use `git tag -d v1.1.2` to delete locally and `git push origin :refs/tags/v1.1.2` to delete remotely before recreating

## Release Cadence

- **Patch releases**: As needed for bug fixes (every few weeks)
- **Minor releases**: For new features (monthly or quarterly)
- **Major releases**: For breaking changes (yearly or as needed)

## Files That Need Version Updates

Always update these files for each release:
1. `custom_components/vacasa/manifest.json`
2. `VERSION`
3. `CHANGELOG.md`

## Quality Gates

Before any release:
- [ ] All GitHub Actions must pass
- [ ] Pre-commit hooks must pass
- [ ] Manual testing on real Home Assistant instance
- [ ] No open critical bugs
- [ ] Documentation is up to date
