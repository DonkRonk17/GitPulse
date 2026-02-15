# GitPulse - Integration Plan

## 🎯 INTEGRATION GOALS

This document outlines how GitPulse integrates with:
1. Team Brain agents (Forge, Atlas, Clio, Nexus, Bolt, Iris, Porter)
2. Existing Team Brain tools (15+ integration patterns)
3. BCH (Beacon Command Hub) - monitoring endpoint
4. Logan's workflows - daily health checks, weekly reports

---

## 📦 BCH INTEGRATION

### Overview

GitPulse can serve as a backend health data source for BCH. While not directly embedded as a BCH command, it provides health data that BCH can query and display.

### BCH API Pattern

```python
# BCH can call GitPulse as a subprocess or import
from gitpulse import GitPulse

pulse = GitPulse()
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

# Expose via BCH API endpoint
@app.route("/api/repo-health")
def repo_health():
    return jsonify(result.to_dict())
```

### BCH Dashboard Widget

GitPulse data can feed a BCH dashboard widget showing:
- Total repo count with health distribution
- Dirty repo alert count
- Average health score trend over time
- Repos needing attention (sorted by urgency)

### Implementation Steps

1. Add GitPulse import to BCH backend
2. Create `/api/repo-health` endpoint
3. Cache scan results (refresh every 5 minutes)
4. Create frontend widget with health indicators
5. Add alert rules for critical repos
6. Test end-to-end data flow

---

## 🤖 AI AGENT INTEGRATION

### Integration Matrix

| Agent | Use Case | Integration Method | Priority |
|-------|----------|-------------------|----------|
| **Forge** | Pre-session repo health audit, review quality gate verification | Python API | HIGH |
| **Atlas** | Pre-build health check, post-build verification, session metrics | Python API + CLI | HIGH |
| **Clio** | Linux repo monitoring, scheduled health checks, ABIOS integration | CLI | HIGH |
| **Iris** | Desktop widget data source, VitalHeart correlation | Python API | MEDIUM |
| **Nexus** | Cross-platform repo sync verification | CLI + Python API | MEDIUM |
| **Porter** | Mobile project repo health dashboard | Python API (JSON) | MEDIUM |
| **Bolt** | Bulk repo maintenance, automated cleanup scripts | CLI | LOW |

### Agent-Specific Workflows

#### Forge (Orchestrator / Reviewer)

**Primary Use Case:** Pre-session audit and quality gate verification

**Integration Steps:**
1. Import GitPulse at session start
2. Scan AutoProjects for health overview
3. Flag repos needing attention in session plan
4. Verify repo health before approving deployments

**Example Workflow:**
```python
# Forge pre-session audit
from gitpulse import GitPulse

pulse = GitPulse()
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

# Check if any repos are in critical state
critical = [r for r in result.repos if r.health_score < 60]
if critical:
    print(f"[!] {len(critical)} repos need attention before proceeding:")
    for r in critical:
        print(f"  {r.name}: {r.health_grade} ({r.health_score}/100)")
        for issue in r.issues:
            print(f"    - {issue}")
else:
    print(f"[OK] All {result.total_repos} repos healthy (avg: "
          f"{sum(r.health_score for r in result.repos)/len(result.repos):.0f}/100)")
```

**Review Quality Gate:**
```python
# After agent completes a build, verify repo health
def verify_build_health(repo_path: str) -> bool:
    """Verify repo health after build."""
    pulse = GitPulse()
    status = pulse.get_status(repo_path)

    if status.health_score < 80:
        print(f"[X] Repo health below threshold: {status.health_score}/100")
        return False

    if not status.has_remote:
        print("[X] No remote configured - upload required")
        return False

    if status.ahead > 0:
        print(f"[!] {status.ahead} unpushed commits")
        return False

    print(f"[OK] Repo health verified: {status.health_grade} ({status.health_score}/100)")
    return True
```

#### Atlas (Executor / Builder)

**Primary Use Case:** Pre-build health check, post-build verification

**Integration Steps:**
1. Check repo health before starting any build
2. Verify git status is clean before committing
3. Post-build: confirm push succeeded and health is good
4. Log health metrics in session bookmark

**Example Workflow:**
```python
# Atlas ToolForge session
from gitpulse import GitPulse

pulse = GitPulse()

# Pre-build: Check for broken git states
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")
dirty = [r for r in result.repos if r.conflict_count > 0]
if dirty:
    print(f"[X] {len(dirty)} repos have merge conflicts - fix first!")

# Post-build: Verify new tool
new_tool_path = "C:/Users/logan/OneDrive/Documents/AutoProjects/NewTool"
status = pulse.get_status(new_tool_path)
print(f"[OK] New tool health: {status.health_grade} ({status.health_score}/100)")
```

#### Clio (Linux / Ubuntu Agent)

**Primary Use Case:** Scheduled health monitoring, system integration

**Platform Considerations:**
- Paths use forward slashes on Linux
- Can be added to cron for scheduled checks
- ABIOS integration for startup monitoring

**Example:**
```bash
# Cron job: Daily health check at 6 AM
0 6 * * * python3 /opt/tools/gitpulse.py report ~/projects --format md --output /var/log/repo_health_$(date +\%Y\%m\%d).md

# Quick check from CLI
python3 gitpulse.py dirty ~/projects
python3 gitpulse.py stale ~/projects --days 14
```

**ABIOS Integration:**
```bash
# Add to ABIOS startup sequence
echo "[GitPulse] Checking repo health..." >> /var/log/abios_startup.log
python3 gitpulse.py scan ~/projects --format json >> /var/log/repo_health.json
```

#### Iris (Desktop Development Specialist)

**Primary Use Case:** VitalHeart data source, desktop widget integration

**Integration Pattern:**
```python
# Iris: Feed GitPulse data to desktop widgets
from gitpulse import GitPulse

pulse = GitPulse()
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

# Format for desktop widget
widget_data = {
    "total": result.total_repos,
    "healthy": result.healthy_count,
    "warning": result.warning_count,
    "critical": result.critical_count,
    "avg_score": sum(r.health_score for r in result.repos) / max(len(result.repos), 1),
    "dirty_count": sum(1 for r in result.repos if r.is_dirty),
}
```

#### Nexus (Multi-Platform Agent)

**Primary Use Case:** Cross-platform repo sync verification

**Cross-Platform Notes:**
- GitPulse uses pathlib for cross-platform path handling
- Works on Windows, Linux, and macOS
- Git commands are platform-agnostic

**Example:**
```python
import platform
from gitpulse import GitPulse

pulse = GitPulse()

# Platform-adaptive paths
if platform.system() == "Windows":
    projects_dir = "C:/Users/logan/OneDrive/Documents/AutoProjects"
elif platform.system() == "Darwin":
    projects_dir = "/Users/logan/projects"
else:
    projects_dir = "/home/logan/projects"

result = pulse.scan(projects_dir)
```

#### Bolt (Free Executor)

**Primary Use Case:** Bulk repo maintenance, automated cleanup

**Cost Considerations:**
- GitPulse is zero-cost (no API calls)
- Perfect for Bolt's free execution model
- Batch processing of repo maintenance

**Example:**
```bash
# Bolt: Bulk cleanup script
python gitpulse.py dirty /projects --format json | python -c "
import json, sys
data = json.load(sys.stdin)
for repo in data:
    print(f'cd {repo[\"path\"]} && git add . && git stash')
"
```

---

## 🔗 INTEGRATION WITH OTHER TEAM BRAIN TOOLS

### With AgentHealth

**Correlation Use Case:** Track repo health as a dimension of agent health

**Integration Pattern:**
```python
from agenthealth import AgentHealth
from gitpulse import GitPulse

health = AgentHealth()
pulse = GitPulse()

# Start session
session_id = "atlas_build_2026-02-15"
health.start_session("ATLAS", session_id=session_id)

# Check repo health
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

# Log repo health as agent metric
health.log_metric("ATLAS", "repo_count", result.total_repos)
health.log_metric("ATLAS", "repo_avg_health", 
    sum(r.health_score for r in result.repos) / max(len(result.repos), 1))
health.log_metric("ATLAS", "dirty_repos", 
    sum(1 for r in result.repos if r.is_dirty))

health.end_session("ATLAS", session_id=session_id)
```

### With SynapseLink

**Notification Use Case:** Alert team about repo health issues

**Integration Pattern:**
```python
from synapselink import quick_send
from gitpulse import GitPulse

pulse = GitPulse()
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

# Alert on critical repos
critical = [r for r in result.repos if r.health_score < 60]
if critical:
    message = f"CRITICAL: {len(critical)} repos below 60/100\n"
    for r in critical:
        message += f"  {r.name}: {r.health_grade} ({r.health_score}/100)\n"
    quick_send("FORGE,LOGAN", "GitPulse Health Alert", message, priority="HIGH")
elif result.warning_count > 5:
    quick_send("TEAM", "GitPulse Weekly Report",
        f"Total: {result.total_repos} | Healthy: {result.healthy_count} | "
        f"Warning: {result.warning_count}", priority="NORMAL")
```

### With TaskQueuePro

**Task Creation Use Case:** Auto-create tasks for repos needing attention

**Integration Pattern:**
```python
from taskqueuepro import TaskQueuePro
from gitpulse import GitPulse

queue = TaskQueuePro()
pulse = GitPulse()

result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

# Create tasks for repos needing attention
for repo in result.repos:
    if repo.health_score < 70:
        priority = 1 if repo.health_score < 50 else 2
        queue.create_task(
            title=f"Fix repo health: {repo.name} ({repo.health_grade})",
            agent="ATLAS",
            priority=priority,
            metadata={
                "tool": "GitPulse",
                "repo": repo.name,
                "score": repo.health_score,
                "issues": repo.issues,
            }
        )
```

### With MemoryBridge

**Context Persistence Use Case:** Track repo health trends over time

**Integration Pattern:**
```python
from memorybridge import MemoryBridge
from gitpulse import GitPulse
from datetime import datetime

memory = MemoryBridge()
pulse = GitPulse()

# Scan and record
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

# Load history
history = memory.get("gitpulse_history", default=[])

# Append today's snapshot
history.append({
    "date": datetime.now().isoformat(),
    "total_repos": result.total_repos,
    "healthy": result.healthy_count,
    "warning": result.warning_count,
    "critical": result.critical_count,
    "avg_score": sum(r.health_score for r in result.repos) / max(len(result.repos), 1),
})

# Keep last 90 days
history = history[-90:]
memory.set("gitpulse_history", history)
memory.sync()
```

### With SessionReplay

**Debugging Use Case:** Log repo health checks in session recordings

**Integration Pattern:**
```python
from sessionreplay import SessionReplay
from gitpulse import GitPulse

replay = SessionReplay()
pulse = GitPulse()

session_id = replay.start_session("ATLAS", task="ToolForge Build")

# Log health check
replay.log_input(session_id, "GitPulse scan: AutoProjects")
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")
replay.log_output(session_id, 
    f"GitPulse: {result.total_repos} repos, {result.healthy_count} healthy")

# Continue with session...
replay.end_session(session_id, status="COMPLETED")
```

### With ContextCompressor

**Token Optimization Use Case:** Compress GitPulse reports before sharing

**Integration Pattern:**
```python
from contextcompressor import ContextCompressor
from gitpulse import GitPulse, format_text

compressor = ContextCompressor()
pulse = GitPulse()

result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")
full_report = format_text(result, verbose=True)

# Compress for sharing
compressed = compressor.compress_text(
    full_report,
    query="which repos need attention",
    method="summary"
)

print(f"Original: ~{len(full_report) // 4} tokens")
print(f"Compressed: ~{len(compressed.compressed_text) // 4} tokens")
```

### With ConfigManager

**Configuration Use Case:** Centralize GitPulse settings

**Integration Pattern:**
```python
from configmanager import ConfigManager
from gitpulse import GitPulse

config = ConfigManager()

gitpulse_config = config.get("gitpulse", {
    "default_path": "C:/Users/logan/OneDrive/Documents/AutoProjects",
    "max_depth": 3,
    "timeout": 15,
    "stale_threshold_days": 30,
    "alert_threshold_score": 60,
})

pulse = GitPulse(
    max_depth=gitpulse_config["max_depth"],
    timeout=gitpulse_config["timeout"],
)

result = pulse.scan(gitpulse_config["default_path"])
```

### With HashGuard

**Integrity Verification Use Case:** Cross-reference file integrity with repo health

**Integration Pattern:**
```python
from gitpulse import GitPulse

pulse = GitPulse()
dirty = pulse.find_dirty("C:/Users/logan/OneDrive/Documents/AutoProjects")

# For dirty repos, check if changes match expected modifications
for repo in dirty:
    print(f"Dirty repo: {repo.name}")
    print(f"  Modified: {repo.modified_count}")
    print(f"  Untracked: {repo.untracked_count}")
    # Could cross-reference with HashGuard manifest
```

### With CodeMetrics

**Quality Correlation Use Case:** Correlate code quality with repo health

**Integration Pattern:**
```python
from gitpulse import GitPulse

pulse = GitPulse()
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

# For each repo, could also run CodeMetrics analysis
for repo in result.repos:
    print(f"{repo.name}: Health={repo.health_grade}, Commits={repo.total_commits}")
    # Could add: CodeMetrics.analyze(repo.path) for code quality score
```

---

## 🚀 ADOPTION ROADMAP

### Phase 1: Core Adoption (Week 1)

**Goal:** All agents aware and can use basic features

**Steps:**
1. [x] Tool deployed to GitHub
2. [ ] Quick-start guides sent via Synapse
3. [ ] Each agent tests basic scan workflow
4. [ ] Feedback collected

**Success Criteria:**
- All 7 agents have used tool at least once
- No blocking issues reported

### Phase 2: Integration (Week 2-3)

**Goal:** Integrated into daily workflows

**Steps:**
1. [ ] Add to ToolForge pre-flight check (ATLAS)
2. [ ] Add to Forge session start audit
3. [ ] Create scheduled health check (CLIO cron)
4. [ ] Integrate with AgentHealth metrics
5. [ ] Monitor usage patterns

**Success Criteria:**
- Used daily by at least 3 agents
- Integration examples tested
- Health trends being tracked

### Phase 3: Optimization (Week 4+)

**Goal:** Optimized and fully adopted

**Steps:**
1. [ ] Collect efficiency metrics
2. [ ] Implement v1.1 improvements (caching, incremental scans)
3. [ ] Create advanced workflow examples
4. [ ] BCH dashboard widget
5. [ ] Full Team Brain ecosystem integration

**Success Criteria:**
- Measurable time savings (15-30 min → <1 min per check)
- Positive feedback from all agents
- v1.1 improvements identified and planned

---

## 📊 SUCCESS METRICS

**Adoption Metrics:**
- Number of agents using tool: Target 7/7
- Daily usage count: Target 3+ scans/day
- Integration with other tools: Target 5+ active integrations

**Efficiency Metrics:**
- Time saved per health check: 15-30 min → <1 min (97% reduction)
- Manual checks eliminated: Target 100%
- Issues caught early: Track per week

**Quality Metrics:**
- Bug reports: Target <2 per month
- Feature requests: Track and prioritize
- User satisfaction: Qualitative feedback

---

## 🛠️ TECHNICAL INTEGRATION DETAILS

### Import Paths

```python
# Standard import
from gitpulse import GitPulse

# Specific imports
from gitpulse import GitPulse, RepoStatus, ScanResult, BranchInfo

# Formatter imports
from gitpulse import format_text, format_json, format_markdown
```

### Configuration Integration

**Default Config:**
```json
{
  "gitpulse": {
    "default_path": "C:/Users/logan/OneDrive/Documents/AutoProjects",
    "max_depth": 3,
    "timeout": 15,
    "stale_threshold_days": 30,
    "alert_threshold_score": 60
  }
}
```

### Error Handling Integration

**Standardized Error Codes (CLI):**
- 0: Success
- 1: General error (ValueError, FileNotFoundError)
- 130: Interrupted (Ctrl+C)

**Exception Types (Python API):**
- `ValueError`: Invalid arguments (empty paths, bad depth)
- `FileNotFoundError`: Path doesn't exist
- Standard Python exceptions for system errors

### Logging Integration

GitPulse outputs to stdout/stderr. For logging integration:
```python
import logging
from gitpulse import GitPulse

logger = logging.getLogger("gitpulse")
pulse = GitPulse()
result = pulse.scan("/projects")
logger.info(f"GitPulse scan: {result.total_repos} repos, "
            f"{result.healthy_count} healthy")
```

---

## 🔧 MAINTENANCE & SUPPORT

### Update Strategy
- Minor updates (v1.x): Monthly
- Major updates (v2.0+): Quarterly
- Security patches: Immediate

### Support Channels
- GitHub Issues: Bug reports and feature requests
- Synapse: Team Brain discussions
- Direct to ATLAS: Complex issues

### Known Limitations
- Scan performance scales linearly with repo count (~0.5s per repo)
- Requires `git` to be installed and in PATH
- Does not analyze code content (use CodeMetrics for that)
- Does not modify any repositories (read-only tool)

### Planned Improvements (v1.1)
- Incremental scanning (only re-check changed repos)
- Scan result caching with TTL
- Watch mode (continuous monitoring)
- Custom scoring rules configuration
- Parallel git command execution

---

## 📚 ADDITIONAL RESOURCES

- Main Documentation: [README.md](README.md)
- Examples: [EXAMPLES.md](EXAMPLES.md)
- Quick Start Guides: [QUICK_START_GUIDES.md](QUICK_START_GUIDES.md)
- Integration Examples: [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md)
- Cheat Sheet: [CHEAT_SHEET.txt](CHEAT_SHEET.txt)
- GitHub: https://github.com/DonkRonk17/GitPulse

---

**Last Updated:** February 15, 2026
**Maintained By:** ATLAS (Team Brain)
