#!/usr/bin/env python3
"""
GitPulse - Multi-Repository Health Monitor

Monitor the health of multiple git repositories simultaneously. Scan a
directory tree for git repos and get instant visibility into uncommitted
changes, remote sync status, stale branches, and overall repository health.

Designed for developers and AI agents managing large collections of
repositories (10-100+), such as Logan Smith's 77+ tool ecosystem in
AutoProjects. Replaces 15-30 minutes of manual checking with a single
3-second command.

Author: ATLAS (Team Brain)
For: Logan Smith / Metaphy LLC
Version: 1.0.0
Date: February 15, 2026
License: MIT
"""

# Standard library imports (alphabetical)
import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

__version__ = "1.0.0"
__author__ = "ATLAS (Team Brain)"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class BranchInfo:
    """Information about a single git branch."""
    name: str
    is_current: bool = False
    last_commit_date: str = ""
    last_commit_age_days: int = 0
    ahead: int = 0
    behind: int = 0
    tracking: str = ""


@dataclass
class RepoStatus:
    """Detailed status of a single git repository."""
    name: str
    path: str
    current_branch: str = ""
    staged_count: int = 0
    modified_count: int = 0
    untracked_count: int = 0
    deleted_count: int = 0
    conflict_count: int = 0
    stash_count: int = 0
    ahead: int = 0
    behind: int = 0
    has_remote: bool = False
    remote_url: str = ""
    last_commit_date: str = ""
    last_commit_age_days: int = 0
    last_commit_message: str = ""
    total_commits: int = 0
    branch_count: int = 0
    tag_count: int = 0
    is_dirty: bool = False
    is_detached: bool = False
    health_score: int = 100
    health_grade: str = "A"
    issues: List[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class ScanResult:
    """Result of scanning a directory for git repositories."""
    root_dir: str
    scan_time: str
    total_repos: int = 0
    healthy_count: int = 0
    warning_count: int = 0
    critical_count: int = 0
    error_count: int = 0
    repos: List[RepoStatus] = field(default_factory=list)
    scan_duration_ms: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        return result


# ---------------------------------------------------------------------------
# Core GitPulse Class
# ---------------------------------------------------------------------------

class GitPulse:
    """
    Multi-Repository Health Monitor.

    Scans a directory tree for git repositories and provides health
    reports, status summaries, and actionable insights.

    Example:
        >>> pulse = GitPulse()
        >>> result = pulse.scan("/path/to/projects")
        >>> print(f"Found {result.total_repos} repos")
        >>> for repo in result.repos:
        ...     print(f"  {repo.name}: {repo.health_grade}")
    """

    def __init__(self, max_depth: int = 3, timeout: int = 10):
        """
        Initialize GitPulse.

        Args:
            max_depth: Maximum directory depth to search for repos
            timeout: Timeout in seconds for git commands
        """
        if max_depth < 1:
            raise ValueError("max_depth must be >= 1")
        if timeout < 1:
            raise ValueError("timeout must be >= 1")
        self.max_depth = max_depth
        self.timeout = timeout

    # -------------------------------------------------------------------
    # Git Command Helpers
    # -------------------------------------------------------------------

    def _run_git(self, repo_path: Path, *args: str) -> Tuple[str, str, int]:
        """
        Run a git command in the given repository.

        Args:
            repo_path: Path to the git repository
            *args: Git command arguments

        Returns:
            Tuple of (stdout, stderr, returncode)
        """
        cmd = ["git", "-C", str(repo_path)] + list(args)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace",
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "", "Command timed out", 1
        except FileNotFoundError:
            return "", "git not found in PATH", 127
        except Exception as e:
            return "", str(e), 1

    def _find_repos(self, root: Path, depth: int = 0) -> List[Path]:
        """
        Recursively find git repositories under root.

        Args:
            root: Root directory to search
            depth: Current search depth

        Returns:
            List of paths to git repositories
        """
        repos = []
        if depth > self.max_depth:
            return repos

        try:
            git_dir = root / ".git"
            if git_dir.exists() and git_dir.is_dir():
                repos.append(root)
                return repos  # Don't recurse into git repos (submodules aside)

            for entry in sorted(root.iterdir()):
                if entry.is_dir() and not entry.name.startswith("."):
                    # Skip known non-project directories
                    if entry.name in ("node_modules", "__pycache__", "venv",
                                      ".venv", "env", ".env", "vendor",
                                      "build", "dist", "target"):
                        continue
                    repos.extend(self._find_repos(entry, depth + 1))
        except PermissionError:
            pass
        except OSError:
            pass

        return repos

    # -------------------------------------------------------------------
    # Repository Analysis
    # -------------------------------------------------------------------

    def _get_repo_status(self, repo_path: Path) -> RepoStatus:
        """
        Get comprehensive status of a single repository.

        Args:
            repo_path: Path to the git repository

        Returns:
            RepoStatus with all details filled in
        """
        status = RepoStatus(
            name=repo_path.name,
            path=str(repo_path),
        )

        # Check git is working in this repo
        stdout, stderr, rc = self._run_git(repo_path, "rev-parse", "--git-dir")
        if rc != 0:
            status.error = f"Not a valid git repo: {stderr}"
            status.health_score = 0
            status.health_grade = "F"
            return status

        # Current branch
        stdout, _, rc = self._run_git(repo_path, "branch", "--show-current")
        if rc == 0 and stdout:
            status.current_branch = stdout
        else:
            # Check for detached HEAD
            stdout2, _, rc2 = self._run_git(repo_path, "rev-parse", "--short", "HEAD")
            if rc2 == 0:
                status.current_branch = f"(detached at {stdout2})"
                status.is_detached = True
            else:
                status.current_branch = "(unknown)"

        # Porcelain status for file counts
        stdout, _, rc = self._run_git(repo_path, "status", "--porcelain=v1")
        if rc == 0 and stdout:
            for line in stdout.split("\n"):
                if len(line) >= 2:
                    x, y = line[0], line[1]
                    if x == "?" and y == "?":
                        status.untracked_count += 1
                    elif x == "U" or y == "U" or (x == "A" and y == "A") or (x == "D" and y == "D"):
                        status.conflict_count += 1
                    else:
                        if x in ("A", "M", "R", "C"):
                            status.staged_count += 1
                        if x == "D":
                            status.deleted_count += 1
                        if y == "M":
                            status.modified_count += 1
                        if y == "D":
                            status.deleted_count += 1

        status.is_dirty = (
            status.staged_count > 0
            or status.modified_count > 0
            or status.untracked_count > 0
            or status.deleted_count > 0
            or status.conflict_count > 0
        )

        # Remote info
        stdout, _, rc = self._run_git(repo_path, "remote", "-v")
        if rc == 0 and stdout:
            status.has_remote = True
            lines = stdout.split("\n")
            if lines:
                parts = lines[0].split()
                if len(parts) >= 2:
                    status.remote_url = parts[1]
        else:
            status.has_remote = False

        # Ahead/behind
        if status.has_remote and not status.is_detached:
            stdout, _, rc = self._run_git(
                repo_path, "rev-list", "--left-right", "--count",
                f"{status.current_branch}@{{upstream}}...HEAD"
            )
            if rc == 0 and stdout:
                parts = stdout.split()
                if len(parts) == 2:
                    try:
                        status.behind = int(parts[0])
                        status.ahead = int(parts[1])
                    except ValueError:
                        pass

        # Last commit info
        stdout, _, rc = self._run_git(
            repo_path, "log", "-1", "--format=%aI|||%s"
        )
        if rc == 0 and stdout:
            parts = stdout.split("|||", 1)
            if len(parts) == 2:
                status.last_commit_date = parts[0]
                status.last_commit_message = parts[1][:120]
                try:
                    commit_dt = datetime.fromisoformat(parts[0])
                    now = datetime.now(timezone.utc)
                    if commit_dt.tzinfo is None:
                        commit_dt = commit_dt.replace(tzinfo=timezone.utc)
                    delta = now - commit_dt
                    status.last_commit_age_days = delta.days
                except (ValueError, TypeError):
                    pass

        # Total commits
        stdout, _, rc = self._run_git(repo_path, "rev-list", "--count", "HEAD")
        if rc == 0 and stdout:
            try:
                status.total_commits = int(stdout)
            except ValueError:
                pass

        # Branch count
        stdout, _, rc = self._run_git(repo_path, "branch", "--list")
        if rc == 0 and stdout:
            status.branch_count = len([
                b for b in stdout.split("\n") if b.strip()
            ])

        # Tag count
        stdout, _, rc = self._run_git(repo_path, "tag", "--list")
        if rc == 0 and stdout:
            status.tag_count = len([
                t for t in stdout.split("\n") if t.strip()
            ])

        # Stash count
        stdout, _, rc = self._run_git(repo_path, "stash", "list")
        if rc == 0 and stdout:
            status.stash_count = len([
                s for s in stdout.split("\n") if s.strip()
            ])

        # Calculate health
        status.health_score, status.health_grade, status.issues = (
            self._calculate_health(status)
        )

        return status

    def _calculate_health(self, status: RepoStatus) -> Tuple[int, str, List[str]]:
        """
        Calculate health score and grade for a repository.

        Scoring:
            Start at 100, deduct for issues:
            - No remote: -15
            - Uncommitted changes: -10
            - Untracked files: -5
            - Behind remote: -10
            - Stale (>30 days): -10
            - Very stale (>90 days): -10 more
            - Detached HEAD: -5
            - Merge conflicts: -20
            - No commits: -30
            - Stashes: -3

        Args:
            status: RepoStatus to evaluate

        Returns:
            Tuple of (score, grade, list of issues)
        """
        score = 100
        issues = []

        if not status.has_remote:
            score -= 15
            issues.append("No remote configured")

        if status.staged_count > 0 or status.modified_count > 0:
            score -= 10
            changes = status.staged_count + status.modified_count
            issues.append(f"{changes} uncommitted change(s)")

        if status.untracked_count > 0:
            score -= 5
            issues.append(f"{status.untracked_count} untracked file(s)")

        if status.deleted_count > 0:
            score -= 5
            issues.append(f"{status.deleted_count} deleted file(s)")

        if status.behind > 0:
            score -= 10
            issues.append(f"{status.behind} commit(s) behind remote")

        if status.ahead > 0 and status.ahead > 5:
            score -= 5
            issues.append(f"{status.ahead} unpushed commit(s)")

        if status.last_commit_age_days > 90:
            score -= 20
            issues.append(f"Very stale: {status.last_commit_age_days} days since last commit")
        elif status.last_commit_age_days > 30:
            score -= 10
            issues.append(f"Stale: {status.last_commit_age_days} days since last commit")

        if status.is_detached:
            score -= 5
            issues.append("Detached HEAD state")

        if status.conflict_count > 0:
            score -= 20
            issues.append(f"{status.conflict_count} merge conflict(s)")

        if status.total_commits == 0:
            score -= 30
            issues.append("No commits yet")

        if status.stash_count > 0:
            score -= 3
            issues.append(f"{status.stash_count} stash(es) pending")

        score = max(0, score)

        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"

        return score, grade, issues

    # -------------------------------------------------------------------
    # Public API Methods
    # -------------------------------------------------------------------

    def scan(self, root_dir: str) -> ScanResult:
        """
        Scan a directory tree for git repositories and analyze health.

        Args:
            root_dir: Path to the root directory to scan

        Returns:
            ScanResult with all repository statuses

        Raises:
            ValueError: If root_dir is empty
            FileNotFoundError: If root_dir doesn't exist
        """
        if not root_dir:
            raise ValueError("root_dir cannot be empty")

        root = Path(root_dir).resolve()
        if not root.exists():
            raise FileNotFoundError(f"Directory not found: {root}")
        if not root.is_dir():
            raise ValueError(f"Not a directory: {root}")

        start_time = time.time()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        result = ScanResult(
            root_dir=str(root),
            scan_time=now_str,
        )

        repo_paths = self._find_repos(root)
        result.total_repos = len(repo_paths)

        for rp in repo_paths:
            repo_status = self._get_repo_status(rp)
            result.repos.append(repo_status)

            if repo_status.error:
                result.error_count += 1
            elif repo_status.health_score >= 80:
                result.healthy_count += 1
            elif repo_status.health_score >= 60:
                result.warning_count += 1
            else:
                result.critical_count += 1

        elapsed = time.time() - start_time
        result.scan_duration_ms = int(elapsed * 1000)

        # Sort by health score (worst first for attention)
        result.repos.sort(key=lambda r: (r.health_score, r.name))

        return result

    def get_status(self, repo_path: str) -> RepoStatus:
        """
        Get detailed status of a single repository.

        Args:
            repo_path: Path to the git repository

        Returns:
            RepoStatus with all details

        Raises:
            ValueError: If repo_path is empty
            FileNotFoundError: If repo_path doesn't exist
        """
        if not repo_path:
            raise ValueError("repo_path cannot be empty")

        path = Path(repo_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Repository not found: {path}")

        return self._get_repo_status(path)

    def find_dirty(self, root_dir: str) -> List[RepoStatus]:
        """
        Find repositories with uncommitted changes.

        Args:
            root_dir: Path to scan

        Returns:
            List of RepoStatus for dirty repos
        """
        result = self.scan(root_dir)
        return [r for r in result.repos if r.is_dirty]

    def find_stale(self, root_dir: str, days: int = 30) -> List[RepoStatus]:
        """
        Find repositories with no recent commits.

        Args:
            root_dir: Path to scan
            days: Number of days to consider stale

        Returns:
            List of RepoStatus for stale repos
        """
        if days < 1:
            raise ValueError("days must be >= 1")
        result = self.scan(root_dir)
        return [r for r in result.repos if r.last_commit_age_days > days]

    def find_unsynced(self, root_dir: str) -> List[RepoStatus]:
        """
        Find repositories that are ahead or behind remote.

        Args:
            root_dir: Path to scan

        Returns:
            List of RepoStatus for unsynced repos
        """
        result = self.scan(root_dir)
        return [r for r in result.repos if r.ahead > 0 or r.behind > 0]

    def find_no_remote(self, root_dir: str) -> List[RepoStatus]:
        """
        Find repositories with no remote configured.

        Args:
            root_dir: Path to scan

        Returns:
            List of RepoStatus for repos without remotes
        """
        result = self.scan(root_dir)
        return [r for r in result.repos if not r.has_remote]

    def get_branches(self, repo_path: str) -> List[BranchInfo]:
        """
        Get detailed branch information for a repository.

        Args:
            repo_path: Path to the git repository

        Returns:
            List of BranchInfo objects
        """
        if not repo_path:
            raise ValueError("repo_path cannot be empty")

        path = Path(repo_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Repository not found: {path}")

        branches = []
        stdout, _, rc = self._run_git(
            path, "branch", "-vv", "--format",
            "%(HEAD)|||%(refname:short)|||%(upstream:short)|||%(upstream:track)"
        )
        if rc != 0 or not stdout:
            return branches

        for line in stdout.split("\n"):
            parts = line.split("|||")
            if len(parts) >= 2:
                is_current = parts[0].strip() == "*"
                name = parts[1].strip()
                tracking = parts[2].strip() if len(parts) > 2 else ""
                track_info = parts[3].strip() if len(parts) > 3 else ""

                branch = BranchInfo(
                    name=name,
                    is_current=is_current,
                    tracking=tracking,
                )

                # Parse ahead/behind from track info
                if track_info:
                    import re
                    ahead_match = re.search(r"ahead (\d+)", track_info)
                    behind_match = re.search(r"behind (\d+)", track_info)
                    if ahead_match:
                        branch.ahead = int(ahead_match.group(1))
                    if behind_match:
                        branch.behind = int(behind_match.group(1))

                # Get last commit date for branch
                stdout2, _, rc2 = self._run_git(
                    path, "log", "-1", "--format=%aI", name
                )
                if rc2 == 0 and stdout2:
                    branch.last_commit_date = stdout2
                    try:
                        commit_dt = datetime.fromisoformat(stdout2)
                        now = datetime.now(timezone.utc)
                        if commit_dt.tzinfo is None:
                            commit_dt = commit_dt.replace(tzinfo=timezone.utc)
                        delta = now - commit_dt
                        branch.last_commit_age_days = delta.days
                    except (ValueError, TypeError):
                        pass

                branches.append(branch)

        return branches


# ---------------------------------------------------------------------------
# Output Formatters
# ---------------------------------------------------------------------------

def format_text(result: ScanResult, verbose: bool = False) -> str:
    """Format scan result as plain text for terminal output."""
    lines = []
    lines.append("=" * 72)
    lines.append("GITPULSE - Multi-Repository Health Monitor")
    lines.append("=" * 72)
    lines.append(f"  Scanned:   {result.root_dir}")
    lines.append(f"  Time:      {result.scan_time}")
    lines.append(f"  Duration:  {result.scan_duration_ms}ms")
    lines.append(f"  Repos:     {result.total_repos}")
    lines.append("")
    lines.append(f"  [OK]  Healthy:   {result.healthy_count}")
    lines.append(f"  [!]   Warning:   {result.warning_count}")
    lines.append(f"  [X]   Critical:  {result.critical_count}")
    if result.error_count > 0:
        lines.append(f"  [ERR] Errors:    {result.error_count}")
    lines.append("")
    lines.append("-" * 72)

    if not result.repos:
        lines.append("  No git repositories found.")
        lines.append("")
        return "\n".join(lines)

    # Header
    lines.append(f"  {'REPO':<30} {'BRANCH':<15} {'GRADE':>5}  {'SCORE':>5}  STATUS")
    lines.append("-" * 72)

    for repo in result.repos:
        if repo.error:
            grade_str = "ERR"
        else:
            grade_str = repo.health_grade

        branch_str = repo.current_branch[:14] if repo.current_branch else "n/a"

        # Status indicators
        status_parts = []
        if repo.is_dirty:
            status_parts.append("dirty")
        if repo.ahead > 0:
            status_parts.append(f"+{repo.ahead}")
        if repo.behind > 0:
            status_parts.append(f"-{repo.behind}")
        if not repo.has_remote:
            status_parts.append("no-remote")
        if repo.conflict_count > 0:
            status_parts.append("CONFLICT")
        if repo.error:
            status_parts.append("ERROR")

        status_str = ", ".join(status_parts) if status_parts else "clean"

        lines.append(
            f"  {repo.name:<30} {branch_str:<15} "
            f"{grade_str:>5}  {repo.health_score:>5}  {status_str}"
        )

        if verbose and repo.issues:
            for issue in repo.issues:
                lines.append(f"    -> {issue}")

    lines.append("-" * 72)
    lines.append("")

    # Summary stats
    if result.repos:
        avg_score = sum(r.health_score for r in result.repos) / len(result.repos)
        lines.append(f"  Average Health Score: {avg_score:.0f}/100")
        dirty_count = sum(1 for r in result.repos if r.is_dirty)
        no_remote_count = sum(1 for r in result.repos if not r.has_remote)
        if dirty_count > 0:
            lines.append(f"  Repos with uncommitted changes: {dirty_count}")
        if no_remote_count > 0:
            lines.append(f"  Repos without remote: {no_remote_count}")
        lines.append("")

    return "\n".join(lines)


def format_repo_text(status: RepoStatus) -> str:
    """Format a single repo status as detailed text."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"  Repository: {status.name}")
    lines.append("=" * 60)
    lines.append(f"  Path:           {status.path}")
    lines.append(f"  Branch:         {status.current_branch}")
    lines.append(f"  Health:         {status.health_grade} ({status.health_score}/100)")
    lines.append("")

    lines.append("  --- Working Tree ---")
    lines.append(f"  Staged:         {status.staged_count}")
    lines.append(f"  Modified:       {status.modified_count}")
    lines.append(f"  Untracked:      {status.untracked_count}")
    lines.append(f"  Deleted:        {status.deleted_count}")
    lines.append(f"  Conflicts:      {status.conflict_count}")
    lines.append(f"  Dirty:          {'Yes' if status.is_dirty else 'No'}")
    lines.append("")

    lines.append("  --- Remote ---")
    lines.append(f"  Has Remote:     {'Yes' if status.has_remote else 'No'}")
    if status.remote_url:
        lines.append(f"  Remote URL:     {status.remote_url}")
    lines.append(f"  Ahead:          {status.ahead}")
    lines.append(f"  Behind:         {status.behind}")
    lines.append("")

    lines.append("  --- History ---")
    lines.append(f"  Total Commits:  {status.total_commits}")
    lines.append(f"  Last Commit:    {status.last_commit_date}")
    if status.last_commit_age_days > 0:
        lines.append(f"  Commit Age:     {status.last_commit_age_days} day(s)")
    if status.last_commit_message:
        lines.append(f"  Message:        {status.last_commit_message}")
    lines.append("")

    lines.append("  --- Stats ---")
    lines.append(f"  Branches:       {status.branch_count}")
    lines.append(f"  Tags:           {status.tag_count}")
    lines.append(f"  Stashes:        {status.stash_count}")
    lines.append("")

    if status.issues:
        lines.append("  --- Issues ---")
        for issue in status.issues:
            lines.append(f"  [!] {issue}")
        lines.append("")

    if status.error:
        lines.append(f"  [X] ERROR: {status.error}")
        lines.append("")

    return "\n".join(lines)


def format_json(result: ScanResult) -> str:
    """Format scan result as JSON."""
    return json.dumps(result.to_dict(), indent=2, default=str)


def format_markdown(result: ScanResult) -> str:
    """Format scan result as Markdown."""
    lines = []
    lines.append("# GitPulse Health Report")
    lines.append("")
    lines.append(f"**Scanned:** `{result.root_dir}`  ")
    lines.append(f"**Time:** {result.scan_time}  ")
    lines.append(f"**Duration:** {result.scan_duration_ms}ms  ")
    lines.append(f"**Total Repos:** {result.total_repos}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Status | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Healthy (80+) | {result.healthy_count} |")
    lines.append(f"| Warning (60-79) | {result.warning_count} |")
    lines.append(f"| Critical (<60) | {result.critical_count} |")
    if result.error_count > 0:
        lines.append(f"| Errors | {result.error_count} |")
    lines.append("")

    if result.repos:
        avg_score = sum(r.health_score for r in result.repos) / len(result.repos)
        lines.append(f"**Average Health Score:** {avg_score:.0f}/100")
        lines.append("")

    lines.append("## Repository Details")
    lines.append("")
    lines.append("| Repo | Branch | Grade | Score | Status |")
    lines.append("|------|--------|-------|-------|--------|")

    for repo in result.repos:
        status_parts = []
        if repo.is_dirty:
            status_parts.append("dirty")
        if repo.ahead > 0:
            status_parts.append(f"+{repo.ahead}")
        if repo.behind > 0:
            status_parts.append(f"-{repo.behind}")
        if not repo.has_remote:
            status_parts.append("no-remote")
        if repo.error:
            status_parts.append("ERROR")
        status_str = ", ".join(status_parts) if status_parts else "clean"

        branch = repo.current_branch if repo.current_branch else "n/a"
        lines.append(
            f"| {repo.name} | {branch} | {repo.health_grade} | "
            f"{repo.health_score} | {status_str} |"
        )

    lines.append("")

    # Issues section
    repos_with_issues = [r for r in result.repos if r.issues]
    if repos_with_issues:
        lines.append("## Issues Requiring Attention")
        lines.append("")
        for repo in repos_with_issues:
            lines.append(f"### {repo.name} ({repo.health_grade} - {repo.health_score}/100)")
            for issue in repo.issues:
                lines.append(f"- {issue}")
            lines.append("")

    lines.append("---")
    lines.append(f"*Generated by GitPulse v{__version__}*")
    lines.append("")

    return "\n".join(lines)


def format_branches_text(branches: List[BranchInfo], repo_name: str) -> str:
    """Format branch information as text."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"  Branches: {repo_name}")
    lines.append("=" * 60)
    lines.append(f"  {'BRANCH':<25} {'TRACKING':<25} {'AGE':>8}  SYNC")
    lines.append("-" * 60)

    for b in branches:
        marker = "* " if b.is_current else "  "
        tracking = b.tracking if b.tracking else "(none)"
        age_str = f"{b.last_commit_age_days}d" if b.last_commit_age_days > 0 else "today"

        sync_parts = []
        if b.ahead > 0:
            sync_parts.append(f"+{b.ahead}")
        if b.behind > 0:
            sync_parts.append(f"-{b.behind}")
        sync_str = ", ".join(sync_parts) if sync_parts else "synced"

        lines.append(
            f"  {marker}{b.name:<23} {tracking:<25} {age_str:>8}  {sync_str}"
        )

    lines.append("-" * 60)
    lines.append(f"  Total branches: {len(branches)}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------

def main():
    """CLI entry point for GitPulse."""
    # Fix Windows console encoding
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    parser = argparse.ArgumentParser(
        prog="gitpulse",
        description="GitPulse - Multi-Repository Health Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s scan .                     Scan current directory for repos
  %(prog)s scan ~/projects --verbose  Scan with detailed issues
  %(prog)s status ./MyRepo            Detailed status for one repo
  %(prog)s dirty .                    Find repos with uncommitted changes
  %(prog)s stale . --days 60          Find repos inactive for 60+ days
  %(prog)s sync .                     Find repos ahead/behind remote
  %(prog)s branches ./MyRepo          Show branch details for a repo
  %(prog)s report . --format md       Generate Markdown health report

For more information: https://github.com/DonkRonk17/GitPulse
        """,
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # scan
    scan_parser = subparsers.add_parser(
        "scan", help="Scan directory for repos and show health summary"
    )
    scan_parser.add_argument("path", help="Directory to scan")
    scan_parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detailed issues per repo"
    )
    scan_parser.add_argument(
        "--format", "-f", choices=["text", "json", "md"],
        default="text", help="Output format (default: text)"
    )
    scan_parser.add_argument(
        "--depth", "-d", type=int, default=3,
        help="Max directory depth to search (default: 3)"
    )
    scan_parser.add_argument(
        "--sort", "-s", choices=["name", "score", "age"],
        default="score", help="Sort repos by (default: score)"
    )

    # status
    status_parser = subparsers.add_parser(
        "status", help="Detailed status for a specific repo"
    )
    status_parser.add_argument("path", help="Path to git repository")
    status_parser.add_argument(
        "--format", "-f", choices=["text", "json"],
        default="text", help="Output format"
    )

    # dirty
    dirty_parser = subparsers.add_parser(
        "dirty", help="Find repos with uncommitted changes"
    )
    dirty_parser.add_argument("path", help="Directory to scan")
    dirty_parser.add_argument(
        "--format", "-f", choices=["text", "json"],
        default="text", help="Output format"
    )
    dirty_parser.add_argument(
        "--depth", "-d", type=int, default=3,
        help="Max directory depth to search"
    )

    # stale
    stale_parser = subparsers.add_parser(
        "stale", help="Find repos with no recent commits"
    )
    stale_parser.add_argument("path", help="Directory to scan")
    stale_parser.add_argument(
        "--days", type=int, default=30,
        help="Days threshold (default: 30)"
    )
    stale_parser.add_argument(
        "--format", "-f", choices=["text", "json"],
        default="text", help="Output format"
    )
    stale_parser.add_argument(
        "--depth", "-d", type=int, default=3,
        help="Max directory depth to search"
    )

    # sync
    sync_parser = subparsers.add_parser(
        "sync", help="Find repos ahead/behind remote"
    )
    sync_parser.add_argument("path", help="Directory to scan")
    sync_parser.add_argument(
        "--format", "-f", choices=["text", "json"],
        default="text", help="Output format"
    )
    sync_parser.add_argument(
        "--depth", "-d", type=int, default=3,
        help="Max directory depth to search"
    )

    # branches
    branches_parser = subparsers.add_parser(
        "branches", help="Show branch details for a repo"
    )
    branches_parser.add_argument("path", help="Path to git repository")
    branches_parser.add_argument(
        "--format", "-f", choices=["text", "json"],
        default="text", help="Output format"
    )

    # report
    report_parser = subparsers.add_parser(
        "report", help="Generate comprehensive health report"
    )
    report_parser.add_argument("path", help="Directory to scan")
    report_parser.add_argument(
        "--format", "-f", choices=["text", "json", "md"],
        default="text", help="Output format (default: text)"
    )
    report_parser.add_argument(
        "--output", "-o", help="Save report to file"
    )
    report_parser.add_argument(
        "--depth", "-d", type=int, default=3,
        help="Max directory depth to search"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        return _handle_command(args)
    except FileNotFoundError as e:
        print(f"[X] Error: {e}")
        return 1
    except ValueError as e:
        print(f"[X] Error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n[!] Interrupted.")
        return 130
    except Exception as e:
        print(f"[X] Unexpected error: {e}")
        return 1


def _handle_command(args) -> int:
    """Handle CLI commands."""
    depth = getattr(args, "depth", 3)
    pulse = GitPulse(max_depth=depth)
    fmt = getattr(args, "format", "text")

    if args.command == "scan":
        result = pulse.scan(args.path)
        if args.sort == "name":
            result.repos.sort(key=lambda r: r.name.lower())
        elif args.sort == "age":
            result.repos.sort(key=lambda r: -r.last_commit_age_days)
        # default sort by score is already done

        if fmt == "json":
            print(format_json(result))
        elif fmt == "md":
            print(format_markdown(result))
        else:
            print(format_text(result, verbose=args.verbose))

    elif args.command == "status":
        status = pulse.get_status(args.path)
        if fmt == "json":
            print(json.dumps(status.to_dict(), indent=2, default=str))
        else:
            print(format_repo_text(status))

    elif args.command == "dirty":
        result = pulse.scan(args.path)
        dirty_repos = [r for r in result.repos if r.is_dirty]
        if fmt == "json":
            print(json.dumps(
                [r.to_dict() for r in dirty_repos], indent=2, default=str
            ))
        else:
            if not dirty_repos:
                print("[OK] All repositories are clean!")
            else:
                print(f"[!] Found {len(dirty_repos)} dirty repo(s):")
                print("")
                for r in dirty_repos:
                    parts = []
                    if r.staged_count:
                        parts.append(f"{r.staged_count} staged")
                    if r.modified_count:
                        parts.append(f"{r.modified_count} modified")
                    if r.untracked_count:
                        parts.append(f"{r.untracked_count} untracked")
                    if r.deleted_count:
                        parts.append(f"{r.deleted_count} deleted")
                    detail = ", ".join(parts)
                    print(f"  {r.name:<35} ({detail})")
                print("")

    elif args.command == "stale":
        days = args.days
        result = pulse.scan(args.path)
        stale_repos = [r for r in result.repos if r.last_commit_age_days > days]
        stale_repos.sort(key=lambda r: -r.last_commit_age_days)
        if fmt == "json":
            print(json.dumps(
                [r.to_dict() for r in stale_repos], indent=2, default=str
            ))
        else:
            if not stale_repos:
                print(f"[OK] No repos stale (>{days} days).")
            else:
                print(f"[!] Found {len(stale_repos)} stale repo(s) (>{days} days):")
                print("")
                for r in stale_repos:
                    print(
                        f"  {r.name:<35} "
                        f"{r.last_commit_age_days} days ago"
                    )
                print("")

    elif args.command == "sync":
        result = pulse.scan(args.path)
        unsynced = [r for r in result.repos if r.ahead > 0 or r.behind > 0]
        no_remote = [r for r in result.repos if not r.has_remote]
        if fmt == "json":
            data = {
                "unsynced": [r.to_dict() for r in unsynced],
                "no_remote": [r.to_dict() for r in no_remote],
            }
            print(json.dumps(data, indent=2, default=str))
        else:
            if not unsynced and not no_remote:
                print("[OK] All repositories are in sync!")
            else:
                if unsynced:
                    print(f"[!] {len(unsynced)} repo(s) out of sync:")
                    print("")
                    for r in unsynced:
                        sync_parts = []
                        if r.ahead > 0:
                            sync_parts.append(f"+{r.ahead} ahead")
                        if r.behind > 0:
                            sync_parts.append(f"-{r.behind} behind")
                        sync_str = ", ".join(sync_parts)
                        print(f"  {r.name:<35} {sync_str}")
                    print("")
                if no_remote:
                    print(f"[!] {len(no_remote)} repo(s) have no remote:")
                    print("")
                    for r in no_remote:
                        print(f"  {r.name}")
                    print("")

    elif args.command == "branches":
        branches = pulse.get_branches(args.path)
        repo_name = Path(args.path).resolve().name
        if fmt == "json":
            print(json.dumps(
                [asdict(b) for b in branches], indent=2, default=str
            ))
        else:
            print(format_branches_text(branches, repo_name))

    elif args.command == "report":
        result = pulse.scan(args.path)
        if fmt == "json":
            output = format_json(result)
        elif fmt == "md":
            output = format_markdown(result)
        else:
            output = format_text(result, verbose=True)

        if args.output:
            output_path = Path(args.output)
            output_path.write_text(output, encoding="utf-8")
            print(f"[OK] Report saved to: {output_path}")
        else:
            print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
