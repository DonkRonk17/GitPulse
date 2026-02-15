# GitPulse - Usage Examples

Quick navigation:
- [Example 1: Basic Scan](#example-1-basic-scan)
- [Example 2: Verbose Scan with Issues](#example-2-verbose-scan-with-issues)
- [Example 3: Single Repo Status](#example-3-single-repo-status)
- [Example 4: Finding Dirty Repos](#example-4-finding-dirty-repos)
- [Example 5: Finding Stale Repos](#example-5-finding-stale-repos)
- [Example 6: Sync Status Check](#example-6-sync-status-check)
- [Example 7: Branch Analysis](#example-7-branch-analysis)
- [Example 8: JSON Output for Automation](#example-8-json-output-for-automation)
- [Example 9: Markdown Report Generation](#example-9-markdown-report-generation)
- [Example 10: Python API - Basic Usage](#example-10-python-api---basic-usage)
- [Example 11: Python API - Filtering and Analysis](#example-11-python-api---filtering-and-analysis)
- [Example 12: Daily Health Check Script](#example-12-daily-health-check-script)
- [Example 13: Error Handling](#example-13-error-handling)
- [Example 14: Integration with Team Brain Tools](#example-14-integration-with-team-brain-tools)

---

## Example 1: Basic Scan

**Scenario:** First time using GitPulse, want to see all repos in a directory.

**Steps:**
```bash
# Check version
python gitpulse.py --version

# Scan your projects directory
python gitpulse.py scan ~/projects
```

**Expected Output:**
```
========================================================================
GITPULSE - Multi-Repository Health Monitor
========================================================================
  Scanned:   /home/user/projects
  Time:      2026-02-15 12:00:00
  Duration:  3200ms
  Repos:     15

  [OK]  Healthy:   12
  [!]   Warning:   2
  [X]   Critical:  1

------------------------------------------------------------------------
  REPO                           BRANCH          GRADE  SCORE  STATUS
------------------------------------------------------------------------
  abandoned-project              master              F     45  dirty, no-remote
  old-experiment                 main                D     65  dirty
  legacy-lib                     master              D     68  dirty
  my-webapp                      develop             A     90  dirty
  api-server                     main                A     95  clean
  ...
------------------------------------------------------------------------

  Average Health Score: 82/100
  Repos with uncommitted changes: 5
  Repos without remote: 1
```

**What You Learned:**
- How to run a basic scan
- GitPulse sorts by health score (worst first)
- You can see dirty repos, grades, and scores at a glance

---

## Example 2: Verbose Scan with Issues

**Scenario:** You want to see exactly what's wrong with each repo.

**Steps:**
```bash
python gitpulse.py scan ~/projects --verbose
```

**Expected Output:**
```
========================================================================
GITPULSE - Multi-Repository Health Monitor
========================================================================
  Scanned:   /home/user/projects
  ...
------------------------------------------------------------------------
  REPO                           BRANCH          GRADE  SCORE  STATUS
------------------------------------------------------------------------
  abandoned-project              master              F     45  dirty, no-remote
    -> No remote configured
    -> 5 uncommitted change(s)
    -> 3 untracked file(s)
    -> Very stale: 120 days since last commit
  old-experiment                 main                D     65  dirty
    -> 2 uncommitted change(s)
    -> Stale: 45 days since last commit
    -> 1 stash(es) pending
  ...
------------------------------------------------------------------------
```

**What You Learned:**
- `--verbose` flag shows specific issues per repo
- Each issue explains why the health score was deducted

---

## Example 3: Single Repo Status

**Scenario:** You want detailed info about one specific repository.

**Steps:**
```bash
python gitpulse.py status ./my-webapp
```

**Expected Output:**
```
============================================================
  Repository: my-webapp
============================================================
  Path:           /home/user/projects/my-webapp
  Branch:         develop
  Health:         A (90/100)

  --- Working Tree ---
  Staged:         0
  Modified:       2
  Untracked:      1
  Deleted:        0
  Conflicts:      0
  Dirty:          Yes

  --- Remote ---
  Has Remote:     Yes
  Remote URL:     https://github.com/user/my-webapp.git
  Ahead:          0
  Behind:         0

  --- History ---
  Total Commits:  234
  Last Commit:    2026-02-14T18:30:00-08:00
  Commit Age:     1 day(s)
  Message:        Update dashboard styles

  --- Stats ---
  Branches:       4
  Tags:           12
  Stashes:        0

  --- Issues ---
  [!] 2 uncommitted change(s)
  [!] 1 untracked file(s)
```

**What You Learned:**
- `status` gives you a complete picture of one repo
- Working tree, remote, history, and stats sections
- Issues listed at the bottom

---

## Example 4: Finding Dirty Repos

**Scenario:** Before end of day, check which repos have uncommitted work.

**Steps:**
```bash
python gitpulse.py dirty ~/projects
```

**Expected Output:**
```
[!] Found 3 dirty repo(s):

  my-webapp                           (2 modified, 1 untracked)
  api-server                          (1 staged)
  config-tool                         (3 modified, 2 untracked)
```

**If all repos are clean:**
```
[OK] All repositories are clean!
```

**What You Learned:**
- `dirty` is a quick filter for repos needing commits
- Shows exactly what type of changes exist

---

## Example 5: Finding Stale Repos

**Scenario:** Identify projects that haven't been touched in a while.

**Steps:**
```bash
# Default: 30 days
python gitpulse.py stale ~/projects

# Custom threshold: 60 days
python gitpulse.py stale ~/projects --days 60

# Very stale: 90+ days
python gitpulse.py stale ~/projects --days 90
```

**Expected Output:**
```
[!] Found 2 stale repo(s) (>30 days):

  legacy-lib                          120 days ago
  old-experiment                      45 days ago
```

**What You Learned:**
- Easily identify abandoned or neglected projects
- Customizable threshold with `--days`

---

## Example 6: Sync Status Check

**Scenario:** Before starting work, check if any repos need pulling or pushing.

**Steps:**
```bash
python gitpulse.py sync ~/projects
```

**Expected Output:**
```
[!] 2 repo(s) out of sync:

  my-webapp                           +3 ahead
  shared-lib                          -2 behind

[!] 1 repo(s) have no remote:

  local-experiment
```

**If all repos are synced:**
```
[OK] All repositories are in sync!
```

**What You Learned:**
- `+3 ahead` means 3 commits need pushing
- `-2 behind` means 2 commits need pulling
- Repos without remotes are flagged separately

---

## Example 7: Branch Analysis

**Scenario:** Check branch status for a specific project.

**Steps:**
```bash
python gitpulse.py branches ./my-webapp
```

**Expected Output:**
```
============================================================
  Branches: my-webapp
============================================================
  BRANCH                    TRACKING                  AGE       SYNC
------------------------------------------------------------
  * develop                 origin/develop             1d        synced
    main                    origin/main                3d        synced
    feature/dark-mode       (none)                    15d
    hotfix/login-bug        origin/hotfix/login-bug    0d        +1
------------------------------------------------------------
  Total branches: 4
```

**What You Learned:**
- `*` marks the current branch
- Tracking shows the upstream branch
- Age shows days since last commit on that branch
- Sync shows ahead/behind status per branch

---

## Example 8: JSON Output for Automation

**Scenario:** Feed GitPulse data into another tool or script.

**Steps:**
```bash
# Full scan as JSON
python gitpulse.py scan ~/projects --format json

# Pipe to jq (if installed) to filter
python gitpulse.py scan ~/projects --format json | jq '.repos[] | select(.is_dirty) | .name'

# Save to file
python gitpulse.py scan ~/projects --format json > health_data.json
```

**Expected Output (truncated):**
```json
{
  "root_dir": "/home/user/projects",
  "scan_time": "2026-02-15 12:00:00",
  "total_repos": 15,
  "healthy_count": 12,
  "warning_count": 2,
  "critical_count": 1,
  "repos": [
    {
      "name": "my-webapp",
      "path": "/home/user/projects/my-webapp",
      "current_branch": "develop",
      "health_score": 90,
      "health_grade": "A",
      "is_dirty": true,
      "staged_count": 0,
      "modified_count": 2,
      "untracked_count": 1,
      ...
    }
  ]
}
```

**What You Learned:**
- JSON output gives full structured data
- Easy to parse with jq, Python, or any JSON tool

---

## Example 9: Markdown Report Generation

**Scenario:** Generate a weekly health report for documentation.

**Steps:**
```bash
# Print to terminal
python gitpulse.py report ~/projects --format md

# Save to file
python gitpulse.py report ~/projects --format md --output weekly_report.md
```

**Expected Output:**
```markdown
# GitPulse Health Report

**Scanned:** `/home/user/projects`
**Time:** 2026-02-15 12:00:00
**Duration:** 3200ms
**Total Repos:** 15

## Summary

| Status | Count |
|--------|-------|
| Healthy (80+) | 12 |
| Warning (60-79) | 2 |
| Critical (<60) | 1 |

**Average Health Score:** 82/100

## Repository Details

| Repo | Branch | Grade | Score | Status |
|------|--------|-------|-------|--------|
| abandoned-project | master | F | 45 | dirty, no-remote |
| old-experiment | main | D | 65 | dirty |
| ...

## Issues Requiring Attention

### abandoned-project (F - 45/100)
- No remote configured
- 5 uncommitted change(s)
- Very stale: 120 days since last commit
```

**What You Learned:**
- Markdown reports are great for sharing with teams
- `--output` saves to file instead of printing

---

## Example 10: Python API - Basic Usage

**Scenario:** Use GitPulse from Python code for automation.

**Steps:**
```python
from gitpulse import GitPulse

# Initialize with custom settings
pulse = GitPulse(max_depth=2, timeout=15)

# Scan directory
result = pulse.scan("/home/user/projects")

# Print summary
print(f"Total repos: {result.total_repos}")
print(f"Healthy: {result.healthy_count}")
print(f"Warning: {result.warning_count}")
print(f"Critical: {result.critical_count}")
print(f"Scan took: {result.scan_duration_ms}ms")

# Iterate over repos
for repo in result.repos:
    grade_marker = "[OK]" if repo.health_score >= 80 else "[!]"
    print(f"  {grade_marker} {repo.name}: {repo.health_grade} ({repo.health_score}/100)")
```

**Expected Output:**
```
Total repos: 15
Healthy: 12
Warning: 2
Critical: 1
Scan took: 3200ms
  [!] abandoned-project: F (45/100)
  [!] old-experiment: D (65/100)
  [!] legacy-lib: D (68/100)
  [OK] my-webapp: A (90/100)
  [OK] api-server: A (95/100)
  ...
```

**What You Learned:**
- Import and use GitPulse as a Python library
- Access all data as structured objects
- Perfect for automation scripts

---

## Example 11: Python API - Filtering and Analysis

**Scenario:** Programmatically find repos that need attention.

**Steps:**
```python
from gitpulse import GitPulse

pulse = GitPulse()

# Find dirty repos
dirty = pulse.find_dirty("/home/user/projects")
print(f"Dirty repos: {len(dirty)}")
for r in dirty:
    print(f"  {r.name}: {r.modified_count} modified, {r.untracked_count} untracked")

# Find stale repos (custom threshold)
stale = pulse.find_stale("/home/user/projects", days=60)
print(f"\nStale repos (>60 days): {len(stale)}")
for r in stale:
    print(f"  {r.name}: {r.last_commit_age_days} days old")

# Find repos without remotes
no_remote = pulse.find_no_remote("/home/user/projects")
print(f"\nRepos without remote: {len(no_remote)}")
for r in no_remote:
    print(f"  {r.name}")

# Find unsynced repos
unsynced = pulse.find_unsynced("/home/user/projects")
print(f"\nUnsynced repos: {len(unsynced)}")
for r in unsynced:
    print(f"  {r.name}: +{r.ahead}/-{r.behind}")
```

**What You Learned:**
- Four filter methods for common queries
- Each returns a list of RepoStatus objects
- Combine filters for custom analysis

---

## Example 12: Daily Health Check Script

**Scenario:** Create an automated daily health check.

**Steps:**
```python
#!/usr/bin/env python3
"""Daily repository health check script."""

import sys
from datetime import datetime
from gitpulse import GitPulse, format_markdown

def daily_check(projects_dir: str):
    """Run daily health check and generate report."""
    pulse = GitPulse()
    result = pulse.scan(projects_dir)

    # Print summary
    print(f"[GitPulse] Daily Health Check - {datetime.now().strftime('%Y-%m-%d')}")
    print(f"  Repos: {result.total_repos}")
    print(f"  Healthy: {result.healthy_count}")
    print(f"  Warnings: {result.warning_count}")
    print(f"  Critical: {result.critical_count}")
    print()

    # Alert on critical repos
    critical = [r for r in result.repos if r.health_score < 60]
    if critical:
        print("[X] CRITICAL REPOS:")
        for r in critical:
            print(f"  {r.name}: {r.health_grade} ({r.health_score}/100)")
            for issue in r.issues:
                print(f"    - {issue}")
        print()

    # Save markdown report
    report = format_markdown(result)
    filename = f"health_{datetime.now().strftime('%Y%m%d')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[OK] Report saved to {filename}")

    return 0 if not critical else 1

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    sys.exit(daily_check(path))
```

**What You Learned:**
- Build custom health check scripts using the API
- Combine scanning with alerting and reporting
- Perfect for scheduled tasks or CI pipelines

---

## Example 13: Error Handling

**Scenario:** Understand how GitPulse handles errors gracefully.

**Steps:**
```python
from gitpulse import GitPulse

pulse = GitPulse()

# Nonexistent directory
try:
    result = pulse.scan("/path/that/does/not/exist")
except FileNotFoundError as e:
    print(f"[X] {e}")
# Output: [X] Directory not found: /path/that/does/not/exist

# Empty path
try:
    result = pulse.scan("")
except ValueError as e:
    print(f"[X] {e}")
# Output: [X] root_dir cannot be empty

# File instead of directory
try:
    result = pulse.scan("/tmp/somefile.txt")
except ValueError as e:
    print(f"[X] {e}")
# Output: [X] Not a directory: /tmp/somefile.txt

# Invalid stale days
try:
    stale = pulse.find_stale("/tmp", days=0)
except ValueError as e:
    print(f"[X] {e}")
# Output: [X] days must be >= 1
```

**What You Learned:**
- GitPulse raises clear, descriptive errors
- FileNotFoundError for missing paths
- ValueError for invalid arguments
- All errors include helpful context

---

## Example 14: Integration with Team Brain Tools

**Scenario:** Use GitPulse with SynapseLink to notify the team.

**Steps:**
```python
from gitpulse import GitPulse

# Check repo health
pulse = GitPulse()
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

# Find repos needing attention
critical = [r for r in result.repos if r.health_score < 70]

if critical:
    # Format message for Team Brain
    message = f"GitPulse Alert: {len(critical)} repo(s) need attention\n\n"
    for r in critical:
        message += f"  {r.name}: {r.health_grade} ({r.health_score}/100)\n"
        for issue in r.issues[:3]:
            message += f"    - {issue}\n"

    # Send via SynapseLink (if available)
    try:
        from synapselink import quick_send
        quick_send("TEAM", "GitPulse Health Alert", message, priority="HIGH")
    except ImportError:
        print(message)
else:
    print(f"[OK] All {result.total_repos} repos healthy! Average: "
          f"{sum(r.health_score for r in result.repos) / len(result.repos):.0f}/100")
```

**What You Learned:**
- GitPulse integrates naturally with other Team Brain tools
- Can be used for automated health monitoring and alerting
- See INTEGRATION_EXAMPLES.md for more integration patterns

---

*Generated by ATLAS (Team Brain) - February 15, 2026*
