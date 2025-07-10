#!/usr/bin/env python3
"""
HACS Compliance Validation Script for Vacasa Integration
"""

import json
import os
import sys


def check_file_exists(file_path, description):
    """Check if a required file exists."""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} - MISSING")
        return False


def validate_json_file(file_path, required_fields=None):
    """Validate JSON file structure."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        if required_fields:
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                print(f"❌ {file_path}: Missing required fields: {missing_fields}")
                return False

        print(f"✅ {file_path}: Valid JSON structure")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ {file_path}: Invalid JSON - {e}")
        return False
    except FileNotFoundError:
        print(f"❌ {file_path}: File not found")
        return False


def validate_manifest():
    """Validate manifest.json compliance."""
    print("\n🔍 Validating manifest.json...")

    required_fields = [
        'domain', 'name', 'codeowners', 'config_flow',
        'documentation', 'iot_class', 'issue_tracker',
        'requirements', 'version'
    ]

    if not validate_json_file('custom_components/vacasa/manifest.json', required_fields):
        return False

    # Additional validation
    with open('custom_components/vacasa/manifest.json', 'r') as f:
        manifest = json.load(f)

    # Check version format
    version = manifest.get('version', '')
    if not version or version.count('.') < 2:
        print(f"❌ Invalid version format: {version}")
        return False

    # Check codeowners format
    codeowners = manifest.get('codeowners', [])
    if not codeowners or not all(owner.startswith('@') for owner in codeowners):
        print(f"❌ Invalid codeowners format: {codeowners}")
        return False

    print("✅ manifest.json: All validations passed")
    return True


def validate_hacs_json():
    """Validate hacs.json compliance."""
    print("\n🔍 Validating hacs.json...")

    required_fields = ['name', 'content_in_root', 'render_readme']

    if not validate_json_file('hacs.json', required_fields):
        return False

    with open('hacs.json', 'r') as f:
        hacs_config = json.load(f)

    # Check recommended fields
    recommended_fields = ['homeassistant', 'hacs', 'iot_class']
    missing_recommended = [field for field in recommended_fields if field not in hacs_config]

    if missing_recommended:
        print(f"⚠️  Missing recommended fields: {missing_recommended}")

    print("✅ hacs.json: All validations passed")
    return True


def validate_repository_structure():
    """Validate required repository structure."""
    print("\n🔍 Validating repository structure...")

    required_files = [
        ('README.md', 'README file'),
        ('LICENSE', 'License file'),
        ('hacs.json', 'HACS configuration'),
        ('custom_components/vacasa/__init__.py', 'Integration init file'),
        ('custom_components/vacasa/manifest.json', 'Integration manifest'),
        ('custom_components/vacasa/config_flow.py', 'Configuration flow'),
        ('.github/ISSUE_TEMPLATE/bug_report.yml', 'Bug report template'),
        ('.github/ISSUE_TEMPLATE/feature_request.yml', 'Feature request template'),
        ('.github/pull_request_template.md', 'Pull request template'),
        ('.github/workflows/validate.yml', 'Validation workflow'),
    ]

    all_present = True
    for file_path, description in required_files:
        if not check_file_exists(file_path, description):
            all_present = False

    return all_present


def validate_documentation():
    """Validate documentation completeness."""
    print("\n🔍 Validating documentation...")

    try:
        with open('README.md', 'r') as f:
            readme_content = f.read()

        required_sections = [
            'Installation',
            'Configuration',
            'Troubleshooting',
            'Contributing'
        ]

        missing_sections = [section for section in required_sections
                           if section not in readme_content]

        if missing_sections:
            print(f"❌ README.md missing sections: {missing_sections}")
            return False

        # Check for HACS badge
        if 'hacs_badge' not in readme_content:
            print("❌ README.md missing HACS badge")
            return False

        print("✅ Documentation: All required sections present")
        return True

    except FileNotFoundError:
        print("❌ README.md not found")
        return False


def validate_github_templates():
    """Validate GitHub templates."""
    print("\n🔍 Validating GitHub templates...")

    templates = [
        '.github/ISSUE_TEMPLATE/bug_report.yml',
        '.github/ISSUE_TEMPLATE/feature_request.yml',
        '.github/pull_request_template.md'
    ]

    all_valid = True
    for template in templates:
        if not check_file_exists(template, "GitHub template"):
            all_valid = False

    return all_valid


def validate_workflows():
    """Validate GitHub workflows."""
    print("\n🔍 Validating GitHub workflows...")

    workflows = [
        '.github/workflows/validate.yml',
        '.github/workflows/dependencies.yml',
        '.github/workflows/release.yml'
    ]

    all_valid = True
    for workflow in workflows:
        if not check_file_exists(workflow, "GitHub workflow"):
            all_valid = False

    return all_valid


def calculate_compliance_score():
    """Calculate overall HACS compliance score."""
    print("\n📊 HACS Compliance Assessment")
    print("=" * 50)

    validations = [
        ("Repository Structure", validate_repository_structure()),
        ("Manifest Validation", validate_manifest()),
        ("HACS Configuration", validate_hacs_json()),
        ("Documentation", validate_documentation()),
        ("GitHub Templates", validate_github_templates()),
        ("GitHub Workflows", validate_workflows())
    ]

    passed = sum(1 for _, result in validations if result)
    total = len(validations)
    score = (passed / total) * 100

    print(f"\nValidation Results:")
    for category, result in validations:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {category}: {status}")

    print(f"\nOverall Score: {score:.1f}% ({passed}/{total})")

    if score >= 95:
        grade = "A+"
        print("🏆 HACS Compliance Grade: A+ (Excellent)")
    elif score >= 90:
        grade = "A"
        print("🥇 HACS Compliance Grade: A (Very Good)")
    elif score >= 80:
        grade = "B+"
        print("🥈 HACS Compliance Grade: B+ (Good)")
    elif score >= 70:
        grade = "B"
        print("🥉 HACS Compliance Grade: B (Satisfactory)")
    else:
        grade = "C"
        print("⚠️  HACS Compliance Grade: C (Needs Improvement)")

    return score, grade


def main():
    """Main validation function."""
    print("🔍 HACS Compliance Validation for Vacasa Integration")
    print("=" * 60)

    score, grade = calculate_compliance_score()

    print(f"\n📋 Summary:")
    print(f"  - Compliance Score: {score:.1f}%")
    print(f"  - Grade: {grade}")

    if score >= 95:
        print(f"  - Status: Ready for HACS submission! 🎉")
        return 0
    else:
        print(f"  - Status: Address failing items before submission")
        return 1


if __name__ == "__main__":
    sys.exit(main())
