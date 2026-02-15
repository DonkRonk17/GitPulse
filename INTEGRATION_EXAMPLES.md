# GitPulse - Integration Examples

## 🎯 INTEGRATION PHILOSOPHY

GitPulse is designed to work seamlessly with other Team Brain tools. This document provides **copy-paste-ready code examples** for common integration patterns.

---

## 📚 TABLE OF CONTENTS

1. [Pattern 1: GitPulse + AgentHealth](#pattern-1-gitpulse--agenthealth)
2. [Pattern 2: GitPulse + SynapseLink](#pattern-2-gitpulse--synapselink)
3. [Pattern 3: GitPulse + TaskQueuePro](#pattern-3-gitpulse--taskqueuepro)
4. [Pattern 4: GitPulse + MemoryBridge](#pattern-4-gitpulse--memorybridge)
5. [Pattern 5: GitPulse + SessionReplay](#pattern-5-gitpulse--sessionreplay)
6. [Pattern 6: GitPulse + ContextCompressor](#pattern-6-gitpulse--contextcompressor)
7. [Pattern 7: GitPulse + ConfigManager](#pattern-7-gitpulse--configmanager)
8. [Pattern 8: GitPulse + CodeMetrics](#pattern-8-gitpulse--codemetrics)
9. [Pattern 9: Multi-Tool Workflow](#pattern-9-multi-tool-workflow)
10. [Pattern 10: Full Team Brain Health Stack](#pattern-10-full-team-brain-health-stack)

---

## Pattern 1: GitPulse + AgentHealth

**Use Case:** Correlate repository health with agent health monitoring

**Why:** Understand how repo maintenance affects agent productivity

**Code:**

```python
from agenthealth import AgentHealth
from gitpulse import GitPulse

# Initialize both tools
health = AgentHealth()
pulse = GitPulse()

# Start session with shared ID
session_id = "atlas_toolforge_2026-02-15"
health.start_session("ATLAS", session_id=session_id)

# Check repo health
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")
avg_score = sum(r.health_score for r in result.repos) / max(len(result.repos), 1)

# Log repo health as agent metric
health.log_metric("ATLAS", "repo_total", result.total_repos)
health.log_metric("ATLAS", "repo_healthy", result.healthy_count)
health.log_metric("ATLAS", "repo_avg_score", round(avg_score))
health.log_metric("ATLAS", "repo_dirty_count",
    sum(1 for r in result.repos if r.is_dirty))

# Report health status
health.heartbeat("ATLAS", status="active")
health.end_session("ATLAS", session_id=session_id)
```

**Result:** Repo health metrics tracked alongside agent health for correlation analysis

---

## Pattern 2: GitPulse + SynapseLink

**Use Case:** Notify Team Brain when repository health issues are detected

**Why:** Keep team informed of repo health changes automatically

**Code:**

```python
from synapselink import quick_send
from gitpulse import GitPulse

pulse = GitPulse()
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

# Calculate summary
avg_score = sum(r.health_score for r in result.repos) / max(len(result.repos), 1)
dirty_count = sum(1 for r in result.repos if r.is_dirty)
critical = [r for r in result.repos if r.health_score < 60]

# Alert on critical issues
if critical:
    message = f"CRITICAL REPOS DETECTED\n\n"
    message += f"Total Repos: {result.total_repos}\n"
    message += f"Critical: {len(critical)}\n\n"
    for r in critical:
        message += f"  {r.name}: {r.health_grade} ({r.health_score}/100)\n"
        for issue in r.issues[:3]:
            message += f"    - {issue}\n"

    quick_send(
        "FORGE,LOGAN",
        "GitPulse CRITICAL Alert",
        message,
        priority="HIGH"
    )

# Regular daily report
elif dirty_count > 5:
    quick_send(
        "TEAM",
        "GitPulse Daily Report",
        f"Repos: {result.total_repos} | "
        f"Healthy: {result.healthy_count} | "
        f"Dirty: {dirty_count} | "
        f"Avg Score: {avg_score:.0f}/100",
        priority="NORMAL"
    )
```

**Result:** Team stays informed about repo health without manual checks

---

## Pattern 3: GitPulse + TaskQueuePro

**Use Case:** Auto-create maintenance tasks for repos needing attention

**Why:** Track repo cleanup alongside other agent tasks

**Code:**

```python
from taskqueuepro import TaskQueuePro
from gitpulse import GitPulse

queue = TaskQueuePro()
pulse = GitPulse()

result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

# Create tasks for repos below threshold
for repo in result.repos:
    if repo.health_score < 70:
        # Determine priority based on severity
        if repo.health_score < 50:
            priority = 1  # Urgent
        elif repo.health_score < 60:
            priority = 2  # High
        else:
            priority = 3  # Medium

        # Create task with detailed context
        task_id = queue.create_task(
            title=f"Repo maintenance: {repo.name} ({repo.health_grade})",
            agent="ATLAS",
            priority=priority,
            metadata={
                "tool": "GitPulse",
                "repo_name": repo.name,
                "repo_path": repo.path,
                "health_score": repo.health_score,
                "health_grade": repo.health_grade,
                "issues": repo.issues,
                "is_dirty": repo.is_dirty,
                "has_remote": repo.has_remote,
            }
        )
        print(f"[OK] Created task {task_id} for {repo.name}")
```

**Result:** Centralized task tracking for repo maintenance across all tools

---

## Pattern 4: GitPulse + MemoryBridge

**Use Case:** Track repo health trends over time

**Why:** Maintain long-term history of repo health for trend analysis

**Code:**

```python
from memorybridge import MemoryBridge
from gitpulse import GitPulse
from datetime import datetime

memory = MemoryBridge()
pulse = GitPulse()

# Scan repos
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

# Load historical data
history = memory.get("gitpulse_history", default=[])

# Calculate today's snapshot
avg_score = sum(r.health_score for r in result.repos) / max(len(result.repos), 1)
snapshot = {
    "date": datetime.now().isoformat(),
    "total_repos": result.total_repos,
    "healthy_count": result.healthy_count,
    "warning_count": result.warning_count,
    "critical_count": result.critical_count,
    "avg_health_score": round(avg_score, 1),
    "dirty_count": sum(1 for r in result.repos if r.is_dirty),
    "no_remote_count": sum(1 for r in result.repos if not r.has_remote),
}

# Append and trim to 90 days
history.append(snapshot)
history = history[-90:]

# Save back
memory.set("gitpulse_history", history)
memory.sync()

# Show trend
if len(history) >= 2:
    prev = history[-2]["avg_health_score"]
    curr = snapshot["avg_health_score"]
    trend = "up" if curr > prev else "down" if curr < prev else "stable"
    print(f"Health trend: {prev:.0f} -> {curr:.0f} ({trend})")
```

**Result:** Historical health data persisted in memory core for trend analysis

---

## Pattern 5: GitPulse + SessionReplay

**Use Case:** Record repo health checks in session recordings

**Why:** Full audit trail of when health was checked and what was found

**Code:**

```python
from sessionreplay import SessionReplay
from gitpulse import GitPulse

replay = SessionReplay()
pulse = GitPulse()

# Start recording
session_id = replay.start_session("ATLAS", task="ToolForge Pre-Flight")

# Log health check
replay.log_input(session_id, "GitPulse: Scanning AutoProjects")

result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

# Log results
avg = sum(r.health_score for r in result.repos) / max(len(result.repos), 1)
replay.log_output(session_id,
    f"GitPulse: {result.total_repos} repos scanned, "
    f"{result.healthy_count} healthy, avg score {avg:.0f}/100")

# Log any critical findings
critical = [r for r in result.repos if r.health_score < 60]
if critical:
    replay.log_output(session_id,
        f"CRITICAL: {len(critical)} repos below threshold")
    for r in critical:
        replay.log_output(session_id, f"  {r.name}: {r.health_grade}")

replay.end_session(session_id, status="COMPLETED")
```

**Result:** Full session replay available showing repo health at time of check

---

## Pattern 6: GitPulse + ContextCompressor

**Use Case:** Compress GitPulse reports before sharing in conversations

**Why:** Save tokens when sharing large repo health reports

**Code:**

```python
from contextcompressor import ContextCompressor
from gitpulse import GitPulse, format_text

compressor = ContextCompressor()
pulse = GitPulse()

# Generate full report
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")
full_report = format_text(result, verbose=True)

# Compress for sharing
compressed = compressor.compress_text(
    full_report,
    query="which repos need attention and why",
    method="summary"
)

print(f"Original: ~{len(full_report) // 4} tokens")
print(f"Compressed: ~{len(compressed.compressed_text) // 4} tokens")
print(f"Savings: ~{compressed.estimated_token_savings} tokens")

# Share compressed version
print("\nCompressed Report:")
print(compressed.compressed_text)
```

**Result:** 70-90% token savings on large health reports

---

## Pattern 7: GitPulse + ConfigManager

**Use Case:** Centralize GitPulse configuration across agents

**Why:** Consistent settings for all agents using GitPulse

**Code:**

```python
from configmanager import ConfigManager
from gitpulse import GitPulse

config = ConfigManager()

# Load or create default GitPulse config
gitpulse_config = config.get("gitpulse", {
    "default_path": "C:/Users/logan/OneDrive/Documents/AutoProjects",
    "max_depth": 3,
    "timeout": 15,
    "stale_threshold_days": 30,
    "alert_threshold_score": 60,
    "scan_schedule": "daily",
})

# Initialize with config
pulse = GitPulse(
    max_depth=gitpulse_config["max_depth"],
    timeout=gitpulse_config["timeout"],
)

# Use configured defaults
result = pulse.scan(gitpulse_config["default_path"])

# Check against configured thresholds
alerts = [r for r in result.repos
          if r.health_score < gitpulse_config["alert_threshold_score"]]
if alerts:
    print(f"[!] {len(alerts)} repos below alert threshold "
          f"({gitpulse_config['alert_threshold_score']})")
```

**Result:** Centralized, consistent configuration management

---

## Pattern 8: GitPulse + CodeMetrics

**Use Case:** Combine repo health with code quality metrics

**Why:** Comprehensive project health = git health + code quality

**Code:**

```python
from gitpulse import GitPulse

pulse = GitPulse()
result = pulse.scan("C:/Users/logan/OneDrive/Documents/AutoProjects")

# Combine GitPulse health with code analysis
# (CodeMetrics would be imported similarly)
print(f"{'REPO':<30} {'GIT':>6} {'STATUS':<10}")
print("-" * 50)

for repo in result.repos[:20]:  # Top 20 repos
    status = "clean" if not repo.is_dirty else "dirty"
    print(f"  {repo.name:<28} {repo.health_score:>5}  {status:<10}")

    # Could add: code_health = CodeMetrics().analyze(repo.path)
    # Combined score = (git_health * 0.4) + (code_health * 0.6)
```

**Result:** Holistic project health combining repo status and code quality

---

## Pattern 9: Multi-Tool Workflow

**Use Case:** Complete ToolForge pre-flight using multiple tools

**Why:** Demonstrate production-grade agent startup workflow

**Code:**

```python
from gitpulse import GitPulse
# Other imports (when available):
# from agenthealth import AgentHealth
# from sessionreplay import SessionReplay
# from synapselink import quick_send

PROJECTS = "C:/Users/logan/OneDrive/Documents/AutoProjects"

def toolforge_preflight(agent_name: str = "ATLAS"):
    """Complete ToolForge pre-flight check using multiple tools."""

    print("=" * 60)
    print(f"  ToolForge Pre-Flight - {agent_name}")
    print("=" * 60)

    # Step 1: Repo Health
    print("\n[1/3] Checking repository health...")
    pulse = GitPulse()
    result = pulse.scan(PROJECTS)

    avg = sum(r.health_score for r in result.repos) / max(len(result.repos), 1)
    print(f"  Repos: {result.total_repos}")
    print(f"  Avg Health: {avg:.0f}/100")
    print(f"  Dirty: {sum(1 for r in result.repos if r.is_dirty)}")

    # Step 2: Check for blockers
    print("\n[2/3] Checking for blockers...")
    conflicts = [r for r in result.repos if r.conflict_count > 0]
    no_remote = [r for r in result.repos if not r.has_remote and r.total_commits > 0]

    blockers = []
    if conflicts:
        blockers.append(f"{len(conflicts)} repo(s) with merge conflicts")
    if no_remote:
        blockers.append(f"{len(no_remote)} repo(s) without remote")

    if blockers:
        print(f"  [!] Found {len(blockers)} blocker(s):")
        for b in blockers:
            print(f"    - {b}")
    else:
        print("  [OK] No blockers found")

    # Step 3: Summary
    print("\n[3/3] Pre-flight summary:")
    if not blockers:
        print("  [OK] All clear - ready for ToolForge build!")
    else:
        print("  [!] Address blockers before proceeding")

    print("=" * 60)
    return len(blockers) == 0

# Run
if toolforge_preflight():
    print("\nProceeding to tool build...")
```

**Result:** Fully instrumented pre-flight check before ToolForge sessions

---

## Pattern 10: Full Team Brain Health Stack

**Use Case:** Ultimate integration - all tools working together for repo monitoring

**Why:** Production-grade automated repo health management

**Code:**

```python
"""
Full Team Brain Health Stack with GitPulse
"""
from gitpulse import GitPulse, format_markdown
from datetime import datetime

PROJECTS = "C:/Users/logan/OneDrive/Documents/AutoProjects"

def full_health_stack():
    """Run complete health stack."""

    # 1. Scan repos
    pulse = GitPulse()
    result = pulse.scan(PROJECTS)

    avg = sum(r.health_score for r in result.repos) / max(len(result.repos), 1)

    # 2. Categorize findings
    critical = [r for r in result.repos if r.health_score < 60]
    warning = [r for r in result.repos if 60 <= r.health_score < 80]
    dirty = [r for r in result.repos if r.is_dirty]

    # 3. Generate report
    report = format_markdown(result)
    filename = f"health_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)

    # 4. Summary
    print(f"Health Stack Report:")
    print(f"  Total: {result.total_repos} repos")
    print(f"  Average: {avg:.0f}/100")
    print(f"  Critical: {len(critical)}")
    print(f"  Warning: {len(warning)}")
    print(f"  Dirty: {len(dirty)}")
    print(f"  Report: {filename}")

    # 5. Would integrate with:
    # - SynapseLink: quick_send() for team alerts
    # - AgentHealth: log_metric() for health tracking
    # - TaskQueuePro: create_task() for maintenance items
    # - MemoryBridge: set() for historical tracking
    # - SessionReplay: log_output() for audit trail

    return result

full_health_stack()
```

**Result:** Complete automated health monitoring with Team Brain integration

---

## 📊 RECOMMENDED INTEGRATION PRIORITY

**Week 1 (Essential):**
1. AgentHealth - Health correlation
2. SynapseLink - Team notifications
3. SessionReplay - Audit trail

**Week 2 (Productivity):**
4. TaskQueuePro - Task management
5. MemoryBridge - Trend tracking
6. ConfigManager - Centralized config

**Week 3 (Advanced):**
7. ContextCompressor - Token optimization
8. CodeMetrics - Combined health scoring
9. Full stack integration

---

## 🔧 TROUBLESHOOTING INTEGRATIONS

**Import Errors:**
```python
# Ensure all tools are in Python path
import sys
from pathlib import Path
sys.path.append(str(Path.home() / "OneDrive/Documents/AutoProjects"))

# Then import
from gitpulse import GitPulse
```

**Version Conflicts:**
```bash
# Check versions
python gitpulse.py --version

# Update if needed
cd AutoProjects/GitPulse
git pull origin main
```

**Performance Tips:**
```python
# For faster scans, limit depth
pulse = GitPulse(max_depth=1)

# For large repos, increase timeout
pulse = GitPulse(timeout=30)
```

---

**Last Updated:** February 15, 2026
**Maintained By:** ATLAS (Team Brain)
