# GitPulse - Quick Start Guides

## 📖 ABOUT THESE GUIDES

Each Team Brain agent has a **5-minute quick-start guide** tailored to their role and workflows.

**Choose your guide:**
- [Forge (Orchestrator)](#-forge-quick-start)
- [Atlas (Executor)](#-atlas-quick-start)
- [Clio (Linux Agent)](#-clio-quick-start)
- [Iris (Desktop Specialist)](#-iris-quick-start)
- [Nexus (Multi-Platform)](#-nexus-quick-start)
- [Bolt (Free Executor)](#-bolt-quick-start)

---

## 🔥 FORGE QUICK START

**Role:** Orchestrator / Reviewer
**Time:** 5 minutes
**Goal:** Use GitPulse for pre-session repo auditing and quality gate verification

### Step 1: Installation Check

```bash
# Verify GitPulse is available
python gitpulse.py --version
# Expected: gitpulse 1.0.0
```

### Step 2: First Use - Pre-Session Audit

```python
# In your Forge session start
from gitpulse import GitPulse

pulse = GitPulse()
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

# Quick overview
print(f"Repos: {result.total_repos} | Healthy: {result.healthy_count} | "
      f"Warning: {result.warning_count} | Critical: {result.critical_count}")
```

### Step 3: Integration with Forge Workflows

**Use Case 1: Verify Repo Before Approving Deployment**
```python
def forge_verify_repo(repo_path: str) -> bool:
    """Forge quality gate: verify repo health before deployment."""
    pulse = GitPulse()
    status = pulse.get_status(repo_path)

    if status.health_score < 80:
        print(f"[X] Health below threshold: {status.health_score}/100")
        for issue in status.issues:
            print(f"  - {issue}")
        return False

    if status.ahead > 0:
        print(f"[!] {status.ahead} unpushed commits - push first")
        return False

    print(f"[OK] Repo verified: {status.health_grade} ({status.health_score}/100)")
    return True
```

**Use Case 2: Find Repos Needing Review**
```python
# Forge: Check what needs attention
pulse = GitPulse()
dirty = pulse.find_dirty("C:/Users/logan/OneDrive/Documents/AutoProjects")
print(f"[!] {len(dirty)} repos have uncommitted changes:")
for r in dirty:
    print(f"  {r.name}: {r.modified_count} modified, {r.untracked_count} untracked")
```

### Step 4: Common Forge Commands

```bash
# Morning audit
python gitpulse.py scan "C:\Users\logan\OneDrive\Documents\AutoProjects" --verbose

# Check specific repo health after agent build
python gitpulse.py status "C:\Users\logan\OneDrive\Documents\AutoProjects\NewTool"

# Weekly health report
python gitpulse.py report "C:\Users\logan\OneDrive\Documents\AutoProjects" --format md --output weekly_health.md
```

### Next Steps for Forge
1. Read [INTEGRATION_PLAN.md](INTEGRATION_PLAN.md) - Forge section
2. Add pre-session audit to your session start routine
3. Use as quality gate for deployment approvals

---

## ⚡ ATLAS QUICK START

**Role:** Executor / Builder / ToolForge
**Time:** 5 minutes
**Goal:** Use GitPulse for pre-build health checks and post-build verification

### Step 1: Installation Check

```bash
python -c "from gitpulse import GitPulse; print('[OK] GitPulse ready')"
```

### Step 2: First Use - ToolForge Pre-Flight

```python
# Atlas ToolForge session start
from gitpulse import GitPulse

pulse = GitPulse()

# Check for broken git states
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

conflicts = [r for r in result.repos if r.conflict_count > 0]
if conflicts:
    print(f"[X] BLOCKING: {len(conflicts)} repos have merge conflicts!")
    for r in conflicts:
        print(f"  {r.name}: {r.conflict_count} conflicts")
else:
    print(f"[OK] No git conflicts. {result.total_repos} repos scanned.")
```

### Step 3: Integration with Build Workflows

**During ToolForge Session:**
```python
# Pre-build: Check that target directory is clean
from gitpulse import GitPulse

pulse = GitPulse()

# Check for repos without remotes (Priority 2 check)
no_remote = pulse.find_no_remote("C:/Users/logan/OneDrive/Documents/AutoProjects")
if no_remote:
    print(f"[!] Priority 2: {len(no_remote)} repos without remotes:")
    for r in no_remote:
        print(f"  {r.name}")
```

**Post-Build Verification:**
```python
# After building and uploading a new tool
new_tool = "C:/Users/logan/OneDrive/Documents/AutoProjects/GitPulse"
status = pulse.get_status(new_tool)
print(f"Post-build health: {status.health_grade} ({status.health_score}/100)")
print(f"  Remote: {'Yes' if status.has_remote else 'No'}")
print(f"  Dirty: {'Yes' if status.is_dirty else 'No'}")
print(f"  Commits: {status.total_commits}")
```

### Step 4: Common Atlas Commands

```bash
# Quick pre-build scan
python gitpulse.py scan "C:\Users\logan\OneDrive\Documents\AutoProjects" --depth 1

# Check specific tool repo
python gitpulse.py status "C:\Users\logan\OneDrive\Documents\AutoProjects\GitPulse"

# Find repos needing upload
python gitpulse.py sync "C:\Users\logan\OneDrive\Documents\AutoProjects"
```

### Next Steps for Atlas
1. Add GitPulse pre-flight to ToolForge Phase 0
2. Use post-build verification in Phase 9
3. Include health score in session bookmarks

---

## 🐧 CLIO QUICK START

**Role:** Linux / Ubuntu Agent
**Time:** 5 minutes
**Goal:** Use GitPulse for Linux repo monitoring and scheduled health checks

### Step 1: Linux Installation

```bash
# Clone from GitHub
git clone https://github.com/DonkRonk17/GitPulse.git
cd GitPulse

# Verify
python3 gitpulse.py --version
```

### Step 2: First Use - Scan Repos

```bash
# Scan all projects
python3 gitpulse.py scan ~/projects

# Find dirty repos
python3 gitpulse.py dirty ~/projects

# Check stale repos
python3 gitpulse.py stale ~/projects --days 14
```

### Step 3: Scheduled Health Checks

**Cron Job Setup:**
```bash
# Edit crontab
crontab -e

# Add daily health check at 6 AM
0 6 * * * python3 /opt/tools/GitPulse/gitpulse.py report ~/projects --format md --output /var/log/repo_health_$(date +\%Y\%m\%d).md

# Add weekly JSON report for analysis
0 0 * * 1 python3 /opt/tools/GitPulse/gitpulse.py scan ~/projects --format json > /var/log/weekly_health.json
```

**ABIOS Integration:**
```bash
# Add to ABIOS startup
python3 gitpulse.py scan ~/projects --format json | tee /var/log/startup_health.json
```

### Step 4: Common Clio Commands

```bash
# Quick overview
python3 gitpulse.py scan ~/projects --depth 1

# Find what needs attention
python3 gitpulse.py dirty ~/projects
python3 gitpulse.py stale ~/projects --days 7

# Sync check
python3 gitpulse.py sync ~/projects

# Generate report
python3 gitpulse.py report ~/projects --format md --output health.md
```

### Next Steps for Clio
1. Set up cron job for daily health checks
2. Add to ABIOS startup sequence
3. Monitor Linux-specific repo health

---

## 🖥️ IRIS QUICK START

**Role:** Desktop Development Specialist
**Time:** 5 minutes
**Goal:** Use GitPulse as data source for desktop widgets and VitalHeart integration

### Step 1: Installation Check

```python
from gitpulse import GitPulse
print("[OK] GitPulse available for desktop integration")
```

### Step 2: First Use - Data for Widgets

```python
from gitpulse import GitPulse

pulse = GitPulse()
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

# Format for desktop widget display
widget_data = {
    "total": result.total_repos,
    "healthy": result.healthy_count,
    "warning": result.warning_count,
    "critical": result.critical_count,
    "avg_score": round(
        sum(r.health_score for r in result.repos) / max(len(result.repos), 1)
    ),
    "dirty_count": sum(1 for r in result.repos if r.is_dirty),
    "last_scan": result.scan_time,
}

print(f"Widget data: {widget_data}")
```

### Step 3: VitalHeart Correlation

```python
# Correlate repo health with VitalHeart metrics
from gitpulse import GitPulse

pulse = GitPulse()
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

# Health mood mapping
avg = sum(r.health_score for r in result.repos) / max(len(result.repos), 1)
if avg >= 90:
    mood = "happy"     # Green heart
elif avg >= 70:
    mood = "neutral"   # Blue heart
else:
    mood = "concerned" # Amber heart
```

### Step 4: Common Iris Commands

```bash
# Quick JSON data for widgets
python gitpulse.py scan "C:\Users\logan\OneDrive\Documents\AutoProjects" --format json

# Status for specific VitalHeart project
python gitpulse.py status "C:\Users\logan\OneDrive\Documents\AutoProjects\VitalHeart"
```

### Next Steps for Iris
1. Create desktop widget showing repo health summary
2. Integrate with VitalHeart mood system
3. Build health trend visualization

---

## 🌐 NEXUS QUICK START

**Role:** Multi-Platform Agent
**Time:** 5 minutes
**Goal:** Use GitPulse for cross-platform repo sync verification

### Step 1: Platform Detection

```python
import platform
from gitpulse import GitPulse

pulse = GitPulse()
print(f"Platform: {platform.system()}")
print(f"GitPulse ready for {platform.system()} repo monitoring")
```

### Step 2: Cross-Platform Usage

```python
import platform
from pathlib import Path
from gitpulse import GitPulse

pulse = GitPulse()

# Platform-adaptive project paths
if platform.system() == "Windows":
    projects = "C:/Users/logan/OneDrive/Documents/AutoProjects"
elif platform.system() == "Darwin":
    projects = str(Path.home() / "projects")
else:
    projects = str(Path.home() / "projects")

result = pulse.scan(projects)
print(f"Scanned {result.total_repos} repos on {platform.system()}")
```

### Step 3: Platform-Specific Considerations

**Windows:**
- Paths use backslash or forward slash (both work)
- Git may need to be added to PATH manually
- OneDrive sync may create lock files (gitpulse handles gracefully)

**Linux:**
- Use `python3` instead of `python`
- Cron integration for scheduled checks
- Standard `/home/user/projects` layout

**macOS:**
- Homebrew git: `brew install git`
- Standard `~/projects` layout

### Step 4: Common Nexus Commands

```bash
# Cross-platform sync check
python gitpulse.py sync /projects

# Platform-adaptive depth
python gitpulse.py scan /projects --depth 2
```

### Next Steps for Nexus
1. Test on all 3 platforms
2. Report platform-specific issues
3. Create cross-platform health comparison

---

## 🆓 BOLT QUICK START

**Role:** Free Executor (Cline + Grok)
**Time:** 5 minutes
**Goal:** Use GitPulse for bulk repo maintenance without API costs

### Step 1: Verify Free Access

```bash
# No API key required!
python gitpulse.py --version
# GitPulse is 100% local - zero API costs
```

### Step 2: First Use - Bulk Health Check

```bash
# Scan all repos
python gitpulse.py scan /path/to/projects

# Find repos needing cleanup
python gitpulse.py dirty /path/to/projects
python gitpulse.py stale /path/to/projects --days 90
```

### Step 3: Bulk Maintenance Workflows

**Find and List Dirty Repos:**
```bash
python gitpulse.py dirty /projects --format json
```

**Generate Cleanup Report:**
```bash
python gitpulse.py report /projects --format md --output cleanup_needed.md
```

### Step 4: Common Bolt Commands

```bash
# Quick bulk check (free, no API costs!)
python gitpulse.py scan /projects --depth 1

# Find what needs cleaning
python gitpulse.py dirty /projects

# Stale repo cleanup candidates
python gitpulse.py stale /projects --days 90
```

### Next Steps for Bolt
1. Add to Cline workflows for repo maintenance
2. Use for repetitive health checks
3. Generate reports for team review

---

## 📚 ADDITIONAL RESOURCES

**For All Agents:**
- Full Documentation: [README.md](README.md)
- Examples: [EXAMPLES.md](EXAMPLES.md)
- Integration Plan: [INTEGRATION_PLAN.md](INTEGRATION_PLAN.md)
- Integration Examples: [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md)
- Cheat Sheet: [CHEAT_SHEET.txt](CHEAT_SHEET.txt)

**Support:**
- GitHub Issues: https://github.com/DonkRonk17/GitPulse/issues
- Synapse: Post in THE_SYNAPSE/active/
- Direct: Message ATLAS

---

**Last Updated:** February 15, 2026
**Maintained By:** ATLAS (Team Brain)
