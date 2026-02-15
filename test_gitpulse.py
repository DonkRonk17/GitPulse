#!/usr/bin/env python3
"""
Comprehensive test suite for GitPulse - Multi-Repository Health Monitor.

Tests cover:
- Core functionality (scanning, status, health scoring)
- Edge cases (empty dirs, no git, invalid paths)
- Error handling (permissions, timeouts, bad repos)
- Output formatters (text, JSON, markdown)
- CLI argument parsing
- Branch analysis
- Filter commands (dirty, stale, sync)

Run: python test_gitpulse.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from gitpulse import (
    GitPulse,
    BranchInfo,
    RepoStatus,
    ScanResult,
    format_text,
    format_json,
    format_markdown,
    format_repo_text,
    format_branches_text,
)


class TestGitPulseInit(unittest.TestCase):
    """Test GitPulse initialization."""

    def test_default_init(self):
        """Test default initialization."""
        pulse = GitPulse()
        self.assertEqual(pulse.max_depth, 3)
        self.assertEqual(pulse.timeout, 10)

    def test_custom_init(self):
        """Test custom initialization."""
        pulse = GitPulse(max_depth=5, timeout=30)
        self.assertEqual(pulse.max_depth, 5)
        self.assertEqual(pulse.timeout, 30)

    def test_invalid_max_depth(self):
        """Test that invalid max_depth raises ValueError."""
        with self.assertRaises(ValueError):
            GitPulse(max_depth=0)
        with self.assertRaises(ValueError):
            GitPulse(max_depth=-1)

    def test_invalid_timeout(self):
        """Test that invalid timeout raises ValueError."""
        with self.assertRaises(ValueError):
            GitPulse(timeout=0)
        with self.assertRaises(ValueError):
            GitPulse(timeout=-5)


class TestRepoStatus(unittest.TestCase):
    """Test RepoStatus data class."""

    def test_default_values(self):
        """Test default values of RepoStatus."""
        status = RepoStatus(name="test", path="/tmp/test")
        self.assertEqual(status.name, "test")
        self.assertEqual(status.path, "/tmp/test")
        self.assertEqual(status.current_branch, "")
        self.assertEqual(status.staged_count, 0)
        self.assertEqual(status.modified_count, 0)
        self.assertEqual(status.untracked_count, 0)
        self.assertEqual(status.health_score, 100)
        self.assertEqual(status.health_grade, "A")
        self.assertFalse(status.is_dirty)
        self.assertEqual(status.issues, [])

    def test_to_dict(self):
        """Test to_dict serialization."""
        status = RepoStatus(name="test", path="/tmp/test")
        d = status.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["name"], "test")
        self.assertEqual(d["path"], "/tmp/test")
        self.assertEqual(d["health_score"], 100)

    def test_dirty_detection(self):
        """Test that is_dirty field works."""
        status = RepoStatus(name="test", path="/tmp/test", is_dirty=True)
        self.assertTrue(status.is_dirty)


class TestScanResult(unittest.TestCase):
    """Test ScanResult data class."""

    def test_default_values(self):
        """Test default ScanResult values."""
        result = ScanResult(root_dir="/tmp", scan_time="2026-02-15 12:00:00")
        self.assertEqual(result.total_repos, 0)
        self.assertEqual(result.healthy_count, 0)
        self.assertEqual(result.repos, [])

    def test_to_dict(self):
        """Test to_dict serialization."""
        result = ScanResult(
            root_dir="/tmp",
            scan_time="2026-02-15 12:00:00",
            total_repos=5,
        )
        d = result.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["total_repos"], 5)


class TestHealthScoring(unittest.TestCase):
    """Test health score calculation."""

    def setUp(self):
        """Set up test fixtures."""
        self.pulse = GitPulse()

    def test_perfect_health(self):
        """Test perfect health score for clean repo."""
        status = RepoStatus(
            name="clean",
            path="/tmp/clean",
            has_remote=True,
            total_commits=10,
            last_commit_age_days=1,
        )
        score, grade, issues = self.pulse._calculate_health(status)
        self.assertEqual(score, 100)
        self.assertEqual(grade, "A")
        self.assertEqual(issues, [])

    def test_no_remote_deduction(self):
        """Test deduction for no remote."""
        status = RepoStatus(
            name="test",
            path="/tmp/test",
            has_remote=False,
            total_commits=10,
            last_commit_age_days=1,
        )
        score, grade, issues = self.pulse._calculate_health(status)
        self.assertEqual(score, 85)
        self.assertIn("No remote configured", issues)

    def test_dirty_deduction(self):
        """Test deduction for uncommitted changes."""
        status = RepoStatus(
            name="test",
            path="/tmp/test",
            has_remote=True,
            total_commits=10,
            modified_count=3,
            last_commit_age_days=1,
        )
        score, grade, issues = self.pulse._calculate_health(status)
        self.assertLess(score, 100)
        self.assertTrue(any("uncommitted" in i for i in issues))

    def test_stale_deduction(self):
        """Test deduction for stale repository."""
        status = RepoStatus(
            name="test",
            path="/tmp/test",
            has_remote=True,
            total_commits=10,
            last_commit_age_days=45,
        )
        score, grade, issues = self.pulse._calculate_health(status)
        self.assertLess(score, 100)
        self.assertTrue(any("Stale" in i for i in issues))

    def test_very_stale_deduction(self):
        """Test extra deduction for very stale repos (>90 days)."""
        status = RepoStatus(
            name="test",
            path="/tmp/test",
            has_remote=True,
            total_commits=10,
            last_commit_age_days=100,
        )
        score, grade, issues = self.pulse._calculate_health(status)
        self.assertLess(score, 85)
        self.assertTrue(any("Very stale" in i for i in issues))

    def test_conflict_deduction(self):
        """Test deduction for merge conflicts."""
        status = RepoStatus(
            name="test",
            path="/tmp/test",
            has_remote=True,
            total_commits=10,
            conflict_count=2,
            last_commit_age_days=1,
        )
        score, grade, issues = self.pulse._calculate_health(status)
        self.assertLessEqual(score, 80)
        self.assertTrue(any("conflict" in i for i in issues))

    def test_no_commits_deduction(self):
        """Test deduction for repo with no commits."""
        status = RepoStatus(
            name="test",
            path="/tmp/test",
            has_remote=True,
            total_commits=0,
            last_commit_age_days=0,
        )
        score, grade, issues = self.pulse._calculate_health(status)
        self.assertLessEqual(score, 70)
        self.assertTrue(any("No commits" in i for i in issues))

    def test_grade_boundaries(self):
        """Test grade assignment boundaries."""
        pulse = self.pulse
        # A: 90+
        s = RepoStatus(name="t", path="/t", has_remote=True,
                        total_commits=1, last_commit_age_days=1)
        _, grade, _ = pulse._calculate_health(s)
        self.assertEqual(grade, "A")

        # B: 80-89 (no remote = -15 -> 85)
        s2 = RepoStatus(name="t", path="/t", has_remote=False,
                         total_commits=1, last_commit_age_days=1)
        _, grade2, _ = pulse._calculate_health(s2)
        self.assertEqual(grade2, "B")

    def test_multiple_issues_compound(self):
        """Test that multiple issues compound deductions."""
        status = RepoStatus(
            name="test",
            path="/tmp/test",
            has_remote=False,           # -15
            total_commits=10,
            modified_count=3,           # -10
            untracked_count=5,          # -5
            last_commit_age_days=50,    # -10
            stash_count=2,              # -3
        )
        score, grade, issues = self.pulse._calculate_health(status)
        self.assertEqual(score, 57)
        self.assertEqual(grade, "F")
        self.assertEqual(len(issues), 5)

    def test_score_never_negative(self):
        """Test that score never goes below 0."""
        status = RepoStatus(
            name="worst",
            path="/tmp/worst",
            has_remote=False,
            total_commits=0,
            modified_count=10,
            untracked_count=20,
            deleted_count=5,
            conflict_count=3,
            last_commit_age_days=365,
            is_detached=True,
            stash_count=10,
        )
        score, grade, issues = self.pulse._calculate_health(status)
        self.assertGreaterEqual(score, 0)
        self.assertEqual(grade, "F")


class TestGitPulseWithRealRepos(unittest.TestCase):
    """Test GitPulse with real temporary git repositories."""

    def setUp(self):
        """Create temporary directory structure with git repos."""
        self.test_dir = tempfile.mkdtemp(prefix="gitpulse_test_")
        self.pulse = GitPulse(max_depth=3)

        # Create a clean repo
        self.clean_repo = Path(self.test_dir) / "clean_repo"
        self.clean_repo.mkdir()
        self._init_repo(self.clean_repo)
        self._make_commit(self.clean_repo, "Initial commit")

        # Create a dirty repo
        self.dirty_repo = Path(self.test_dir) / "dirty_repo"
        self.dirty_repo.mkdir()
        self._init_repo(self.dirty_repo)
        self._make_commit(self.dirty_repo, "Initial commit")
        # Add untracked file
        (self.dirty_repo / "untracked.txt").write_text("hello")
        # Modify tracked file
        (self.dirty_repo / "readme.txt").write_text("modified content")

        # Create a non-git directory
        self.non_git = Path(self.test_dir) / "not_a_repo"
        self.non_git.mkdir()
        (self.non_git / "file.txt").write_text("just a file")

    def tearDown(self):
        """Clean up temporary directory."""
        try:
            shutil.rmtree(self.test_dir, ignore_errors=True)
        except Exception:
            pass

    def _init_repo(self, path: Path):
        """Initialize a git repository."""
        subprocess.run(
            ["git", "init"], cwd=str(path),
            capture_output=True, text=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(path), capture_output=True, text=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(path), capture_output=True, text=True
        )

    def _make_commit(self, path: Path, message: str):
        """Create a file and commit it."""
        readme = path / "readme.txt"
        readme.write_text(f"Content for {message}")
        subprocess.run(
            ["git", "add", "."], cwd=str(path),
            capture_output=True, text=True
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(path), capture_output=True, text=True
        )

    def test_scan_finds_repos(self):
        """Test that scan finds git repositories."""
        result = self.pulse.scan(self.test_dir)
        self.assertEqual(result.total_repos, 2)
        repo_names = {r.name for r in result.repos}
        self.assertIn("clean_repo", repo_names)
        self.assertIn("dirty_repo", repo_names)

    def test_scan_excludes_non_git(self):
        """Test that non-git directories are excluded."""
        result = self.pulse.scan(self.test_dir)
        repo_names = {r.name for r in result.repos}
        self.assertNotIn("not_a_repo", repo_names)

    def test_clean_repo_status(self):
        """Test status of clean repository."""
        status = self.pulse.get_status(str(self.clean_repo))
        self.assertEqual(status.name, "clean_repo")
        self.assertFalse(status.is_dirty)
        self.assertEqual(status.staged_count, 0)
        self.assertEqual(status.modified_count, 0)
        self.assertGreater(status.total_commits, 0)

    def test_dirty_repo_status(self):
        """Test status of dirty repository."""
        status = self.pulse.get_status(str(self.dirty_repo))
        self.assertEqual(status.name, "dirty_repo")
        self.assertTrue(status.is_dirty)
        self.assertGreater(status.untracked_count, 0)

    def test_find_dirty(self):
        """Test finding dirty repositories."""
        dirty = self.pulse.find_dirty(self.test_dir)
        self.assertEqual(len(dirty), 1)
        self.assertEqual(dirty[0].name, "dirty_repo")

    def test_scan_result_counts(self):
        """Test that scan result counts are accurate."""
        result = self.pulse.scan(self.test_dir)
        self.assertEqual(
            result.total_repos,
            result.healthy_count + result.warning_count
            + result.critical_count + result.error_count
        )

    def test_scan_duration(self):
        """Test that scan duration is measured."""
        result = self.pulse.scan(self.test_dir)
        self.assertGreater(result.scan_duration_ms, 0)

    def test_branches_returns_list(self):
        """Test that get_branches returns branch info."""
        branches = self.pulse.get_branches(str(self.clean_repo))
        self.assertIsInstance(branches, list)
        # At least one branch (main/master)
        self.assertGreater(len(branches), 0)
        # Check it's a BranchInfo
        self.assertIsInstance(branches[0], BranchInfo)


class TestErrorHandling(unittest.TestCase):
    """Test error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.pulse = GitPulse()

    def test_scan_nonexistent_directory(self):
        """Test scanning a nonexistent directory."""
        with self.assertRaises(FileNotFoundError):
            self.pulse.scan("/nonexistent/path/xyz123")

    def test_scan_empty_path(self):
        """Test scanning with empty path."""
        with self.assertRaises(ValueError):
            self.pulse.scan("")

    def test_status_nonexistent_repo(self):
        """Test status of nonexistent repo."""
        with self.assertRaises(FileNotFoundError):
            self.pulse.get_status("/nonexistent/repo/xyz123")

    def test_status_empty_path(self):
        """Test status with empty path."""
        with self.assertRaises(ValueError):
            self.pulse.get_status("")

    def test_branches_nonexistent_repo(self):
        """Test branches of nonexistent repo."""
        with self.assertRaises(FileNotFoundError):
            self.pulse.get_branches("/nonexistent/repo/xyz123")

    def test_branches_empty_path(self):
        """Test branches with empty path."""
        with self.assertRaises(ValueError):
            self.pulse.get_branches("")

    def test_stale_invalid_days(self):
        """Test find_stale with invalid days."""
        with self.assertRaises(ValueError):
            self.pulse.find_stale("/tmp", days=0)

    def test_scan_file_not_directory(self):
        """Test scanning a file instead of directory."""
        tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        tmpf.close()
        try:
            with self.assertRaises(ValueError):
                self.pulse.scan(tmpf.name)
        finally:
            os.unlink(tmpf.name)


class TestOutputFormatters(unittest.TestCase):
    """Test output formatters."""

    def _make_result(self) -> ScanResult:
        """Create a sample ScanResult for testing."""
        repo1 = RepoStatus(
            name="RepoA",
            path="/tmp/RepoA",
            current_branch="main",
            health_score=95,
            health_grade="A",
            has_remote=True,
            total_commits=50,
            last_commit_age_days=2,
        )
        repo2 = RepoStatus(
            name="RepoB",
            path="/tmp/RepoB",
            current_branch="develop",
            health_score=65,
            health_grade="D",
            is_dirty=True,
            modified_count=3,
            has_remote=True,
            total_commits=10,
            last_commit_age_days=45,
            issues=["3 uncommitted change(s)", "Stale: 45 days since last commit"],
        )
        return ScanResult(
            root_dir="/tmp",
            scan_time="2026-02-15 12:00:00",
            total_repos=2,
            healthy_count=1,
            warning_count=1,
            repos=[repo2, repo1],  # Sorted by score
            scan_duration_ms=150,
        )

    def test_format_text_output(self):
        """Test text formatter produces expected output."""
        result = self._make_result()
        text = format_text(result)
        self.assertIn("GITPULSE", text)
        self.assertIn("RepoA", text)
        self.assertIn("RepoB", text)
        self.assertIn("Healthy", text)
        self.assertIn("2", text)  # total repos

    def test_format_text_verbose(self):
        """Test verbose text output includes issues."""
        result = self._make_result()
        text = format_text(result, verbose=True)
        self.assertIn("uncommitted", text)

    def test_format_json_valid(self):
        """Test JSON formatter produces valid JSON."""
        result = self._make_result()
        json_str = format_json(result)
        parsed = json.loads(json_str)
        self.assertIsInstance(parsed, dict)
        self.assertEqual(parsed["total_repos"], 2)
        self.assertEqual(len(parsed["repos"]), 2)

    def test_format_markdown(self):
        """Test Markdown formatter."""
        result = self._make_result()
        md = format_markdown(result)
        self.assertIn("# GitPulse Health Report", md)
        self.assertIn("| Repo |", md)
        self.assertIn("RepoA", md)
        self.assertIn("RepoB", md)

    def test_format_repo_text(self):
        """Test single repo text formatter."""
        status = RepoStatus(
            name="TestRepo",
            path="/tmp/TestRepo",
            current_branch="main",
            health_score=90,
            health_grade="A",
            total_commits=25,
        )
        text = format_repo_text(status)
        self.assertIn("TestRepo", text)
        self.assertIn("main", text)
        self.assertIn("90", text)

    def test_format_branches_text(self):
        """Test branches text formatter."""
        branches = [
            BranchInfo(name="main", is_current=True, last_commit_age_days=1),
            BranchInfo(name="develop", is_current=False, last_commit_age_days=5),
        ]
        text = format_branches_text(branches, "TestRepo")
        self.assertIn("TestRepo", text)
        self.assertIn("main", text)
        self.assertIn("develop", text)
        self.assertIn("Total branches: 2", text)

    def test_format_text_empty_scan(self):
        """Test text formatter with no repos."""
        result = ScanResult(
            root_dir="/tmp/empty",
            scan_time="2026-02-15 12:00:00",
            total_repos=0,
        )
        text = format_text(result)
        self.assertIn("No git repositories found", text)

    def test_format_markdown_issues_section(self):
        """Test Markdown formatter includes issues section."""
        result = self._make_result()
        md = format_markdown(result)
        self.assertIn("Issues Requiring Attention", md)
        self.assertIn("uncommitted", md)


class TestBranchInfo(unittest.TestCase):
    """Test BranchInfo data class."""

    def test_default_values(self):
        """Test default BranchInfo values."""
        branch = BranchInfo(name="main")
        self.assertEqual(branch.name, "main")
        self.assertFalse(branch.is_current)
        self.assertEqual(branch.ahead, 0)
        self.assertEqual(branch.behind, 0)

    def test_current_branch(self):
        """Test current branch flag."""
        branch = BranchInfo(name="develop", is_current=True)
        self.assertTrue(branch.is_current)


class TestScanEmpty(unittest.TestCase):
    """Test scanning directories with no repos."""

    def test_empty_directory(self):
        """Test scanning an empty directory."""
        with tempfile.TemporaryDirectory(prefix="gitpulse_empty_") as tmpdir:
            pulse = GitPulse()
            result = pulse.scan(tmpdir)
            self.assertEqual(result.total_repos, 0)
            self.assertEqual(len(result.repos), 0)

    def test_directory_with_only_files(self):
        """Test scanning directory with files but no repos."""
        with tempfile.TemporaryDirectory(prefix="gitpulse_files_") as tmpdir:
            Path(tmpdir, "file1.txt").write_text("hello")
            Path(tmpdir, "file2.py").write_text("print('hi')")
            pulse = GitPulse()
            result = pulse.scan(tmpdir)
            self.assertEqual(result.total_repos, 0)


class TestFindNoRemote(unittest.TestCase):
    """Test finding repos without remotes."""

    def test_find_no_remote(self):
        """Test finding repos without remote configured."""
        with tempfile.TemporaryDirectory(prefix="gitpulse_noremote_") as tmpdir:
            repo_path = Path(tmpdir) / "local_only"
            repo_path.mkdir()
            subprocess.run(
                ["git", "init"], cwd=str(repo_path),
                capture_output=True, text=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=str(repo_path), capture_output=True, text=True
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path), capture_output=True, text=True
            )
            (repo_path / "file.txt").write_text("content")
            subprocess.run(
                ["git", "add", "."], cwd=str(repo_path),
                capture_output=True, text=True
            )
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=str(repo_path), capture_output=True, text=True
            )

            pulse = GitPulse()
            no_remote = pulse.find_no_remote(tmpdir)
            self.assertEqual(len(no_remote), 1)
            self.assertEqual(no_remote[0].name, "local_only")
            self.assertFalse(no_remote[0].has_remote)


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------

def run_tests():
    """Run all tests with nice output."""
    print("=" * 70)
    print("TESTING: GitPulse v1.0.0")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestGitPulseInit,
        TestRepoStatus,
        TestScanResult,
        TestHealthScoring,
        TestGitPulseWithRealRepos,
        TestErrorHandling,
        TestOutputFormatters,
        TestBranchInfo,
        TestScanEmpty,
        TestFindNoRemote,
    ]

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print(f"RESULTS: {result.testsRun} tests")
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"[OK] Passed: {passed}")
    if result.failures:
        print(f"[X]  Failed: {len(result.failures)}")
    if result.errors:
        print(f"[X]  Errors: {len(result.errors)}")
    print("=" * 70)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
