---
name: Bug report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Home Assistant (please complete the following information):**
 - Version: [e.g. 2023.5.0]
 - Installation type: [e.g. Home Assistant OS, Container, Core]
 - Integration version: [e.g. 0.1.0]

**Debug Logs** (Required for bug reports)
To help us diagnose the issue, please provide debug logs:

1. **Enable Debug Logging:**
   - Go to Settings > System > Logs in Home Assistant
   - Click "Configure" next to the log level
   - Add the following to enable debug logging for Vacasa:
     ```yaml
     custom_components.vacasa: debug
     ```
   - Click "Save"

2. **Force Integration Reload:**
   - Go to Settings > Devices & Services
   - Find the Vacasa integration
   - Click the three dots menu and select "Reload"
   - Wait for the integration to fully reload

3. **Reproduce the Issue:**
   - Perform the steps that trigger the bug
   - Wait a few minutes for the integration to update

4. **Download Logs:**
   - Go back to Settings > System > Logs
   - Click "Download full log"
   - Extract the relevant Vacasa logs (search for "vacasa" in the file)

5. **Attach Logs:**
   - Copy the relevant log entries below
   - **Important:** Remove any sensitive information like:
     - Your username/email
     - Guest names
     - Property addresses
     - API tokens (these appear as long strings starting with "eyJ")

```
Paste the relevant debug logs here (with sensitive info removed)
```

**Additional context**
Add any other context about the problem here.
