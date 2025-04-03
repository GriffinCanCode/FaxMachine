#!/usr/bin/env python3
"""QGit doctor module for comprehensive repository health checks.

This module provides advanced diagnostic capabilities for Git repositories,
including configuration checks, performance analysis, and automated fixes.
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from qgits.qgit_errors import GitCommandError
from qgits.qgit_git import GitCommand
from qgits.qgit_utils import format_size


class RepositoryDoctor:
    """Handles comprehensive Git repository health diagnostics and repairs."""

    def __init__(self, verbose: bool = False, fix: bool = False):
        """Initialize the doctor with specified options.

        Args:
            verbose: Whether to show detailed diagnostic information
            fix: Whether to attempt automatic fixes for issues
        """
        self.verbose = verbose
        self.fix = fix
        self.issues: List[Dict] = []
        self.fixes_applied: List[str] = []

    def add_issue(
        self,
        category: str,
        severity: str,
        message: str,
        fix_command: Optional[str] = None,
    ) -> None:
        """Add an issue to the diagnostic report.

        Args:
            category: Category of the issue (e.g., 'config', 'remote', 'hooks')
            severity: Severity level ('critical', 'warning', 'info')
            message: Description of the issue
            fix_command: Optional command that can fix the issue
        """
        self.issues.append(
            {
                "category": category,
                "severity": severity,
                "message": message,
                "fix_command": fix_command,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def check_git_config(self) -> bool:
        """Check Git configuration settings.

        Returns:
            True if all config checks pass, False otherwise
        """
        try:
            # Check user configuration
            user_name = GitCommand.run("git config --get user.name")
            user_email = GitCommand.run("git config --get user.email")

            if not user_name:
                self.add_issue(
                    "config",
                    "critical",
                    "Git user.name not set",
                    "git config --global user.name 'Your Name'",
                )

            if not user_email:
                self.add_issue(
                    "config",
                    "critical",
                    "Git user.email not set",
                    "git config --global user.email 'your.email@example.com'",
                )

            # Check core settings
            core_settings = {
                "core.autocrlf": ("input" if sys.platform != "win32" else "true"),
                "core.fileMode": "true",
                "core.ignorecase": "false",
                "pull.rebase": "true",
            }

            for setting, expected in core_settings.items():
                value = GitCommand.run(f"git config --get {setting}")
                if value != expected:
                    self.add_issue(
                        "config",
                        "warning",
                        f"Recommended setting {setting}={expected} not set (current: {value or 'not set'})",
                        f"git config --global {setting} {expected}",
                    )

            # Check for duplicate entries
            config_list = GitCommand.run("git config --list")
            seen_keys = {}
            for line in config_list.split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    if key in seen_keys:
                        self.add_issue(
                            "config",
                            "warning",
                            f"Duplicate config entry found: {key}",
                            "# Manual fix required - check .git/config and ~/.gitconfig",
                        )
                    seen_keys[key] = value

            return (
                len(
                    [
                        i
                        for i in self.issues
                        if i["category"] == "config" and i["severity"] == "critical"
                    ]
                )
                == 0
            )

        except GitCommandError as e:
            self.add_issue("config", "critical", f"Error checking git config: {str(e)}")
            return False

    def check_remote_connection(self) -> bool:
        """Check remote repository connectivity and configuration.

        Returns:
            True if remote checks pass, False otherwise
        """
        try:
            # Get remote configuration
            remotes = GitCommand.run("git remote -v").split("\n")
            if not remotes:
                self.add_issue(
                    "remote",
                    "warning",
                    "No remote repositories configured",
                    "git remote add origin <repository-url>",
                )
                return True

            # Check each remote
            for remote in remotes:
                if not remote:
                    continue

                name, url, *_ = remote.split()

                # Test connection
                try:
                    GitCommand.run(f"git ls-remote --exit-code {name}")
                except GitCommandError:
                    self.add_issue(
                        "remote",
                        "critical",
                        f"Cannot connect to remote '{name}' ({url})",
                        "# Check credentials and network connection",
                    )

                # Check for HTTPS vs SSH
                if url.startswith("https://"):
                    self.add_issue(
                        "remote",
                        "info",
                        f"Remote '{name}' uses HTTPS - consider using SSH for better security",
                        "# Convert to SSH using: git remote set-url origin git@github.com:user/repo.git",
                    )

            return (
                len(
                    [
                        i
                        for i in self.issues
                        if i["category"] == "remote" and i["severity"] == "critical"
                    ]
                )
                == 0
            )

        except GitCommandError as e:
            self.add_issue("remote", "critical", f"Error checking remotes: {str(e)}")
            return False

    def check_large_files(self, size_threshold_mb: int = 100) -> bool:
        """Check for large files that might impact repository performance.

        Args:
            size_threshold_mb: Size threshold in MB to flag large files

        Returns:
            True if no problematic large files found, False otherwise
        """
        try:
            # Get all objects in the repository
            objects = GitCommand.run("git rev-list --objects --all").split("\n")

            # Get sizes of all objects
            sizes = GitCommand.run(
                "git cat-file --batch-check='%(objectname) %(objecttype) %(objectsize) %(rest)'"
                " --batch-all-objects"
            ).split("\n")

            large_files = []
            for size_line in sizes:
                if not size_line:
                    continue

                parts = size_line.split()
                if len(parts) >= 3 and parts[1] == "blob":
                    size_mb = int(parts[2]) / (1024 * 1024)
                    if size_mb > size_threshold_mb:
                        filename = next(
                            (
                                line.split()[1]
                                for line in objects
                                if line.startswith(parts[0])
                            ),
                            "unknown",
                        )
                        large_files.append((filename, size_mb))

            if large_files:
                for filename, size in large_files:
                    self.add_issue(
                        "storage",
                        "warning",
                        f"Large file detected: {filename} ({size:.1f}MB)",
                        "# Consider using Git LFS or adding to .gitignore",
                    )
                return False

            return True

        except GitCommandError as e:
            self.add_issue(
                "storage", "warning", f"Error checking large files: {str(e)}"
            )
            return False

    def check_branch_status(self) -> bool:
        """Check status of local and remote branches.

        Returns:
            True if branch status is healthy, False otherwise
        """
        try:
            current = GitCommand.get_current_branch()

            # Check if detached HEAD
            if current == "HEAD":
                self.add_issue(
                    "branch",
                    "critical",
                    "Detached HEAD state detected",
                    "git checkout <branch-name>",
                )
                return False

            # Check branch sync status
            try:
                behind_ahead = GitCommand.run(
                    f"git rev-list --left-right --count origin/{current}...HEAD"
                ).split()
                if behind_ahead and len(behind_ahead) == 2:
                    behind, ahead = map(int, behind_ahead)
                    if behind > 0:
                        self.add_issue(
                            "branch",
                            "warning",
                            f"Current branch is behind origin/{current} by {behind} commit(s)",
                            f"git pull origin {current}",
                        )
                    if ahead > 0:
                        self.add_issue(
                            "branch",
                            "info",
                            f"Current branch is ahead of origin/{current} by {ahead} commit(s)",
                            f"git push origin {current}",
                        )
            except GitCommandError:
                # Remote branch might not exist
                self.add_issue(
                    "branch",
                    "info",
                    f"No upstream branch set for '{current}'",
                    f"git push -u origin {current}",
                )

            return True

        except GitCommandError as e:
            self.add_issue(
                "branch", "critical", f"Error checking branch status: {str(e)}"
            )
            return False

    def check_hooks(self) -> bool:
        """Check Git hooks configuration and permissions.

        Returns:
            True if hooks are properly configured, False otherwise
        """
        try:
            hooks_dir = ".git/hooks"
            if not os.path.exists(hooks_dir):
                self.add_issue("hooks", "warning", "Hooks directory not found")
                return False

            # Check common hooks
            common_hooks = [
                "pre-commit",
                "pre-push",
                "commit-msg",
                "post-checkout",
                "pre-rebase",
            ]

            for hook in common_hooks:
                hook_path = os.path.join(hooks_dir, hook)
                sample_path = f"{hook_path}.sample"

                if os.path.exists(hook_path):
                    # Check if hook is executable
                    if not os.access(hook_path, os.X_OK):
                        self.add_issue(
                            "hooks",
                            "warning",
                            f"Hook '{hook}' exists but is not executable",
                            f"chmod +x {hook_path}",
                        )
                elif os.path.exists(sample_path):
                    self.add_issue(
                        "hooks",
                        "info",
                        f"Sample hook '{hook}' available but not implemented",
                        f"cp {sample_path} {hook_path} && chmod +x {hook_path}",
                    )

            return True

        except Exception as e:
            self.add_issue("hooks", "warning", f"Error checking hooks: {str(e)}")
            return False

    def check_gitignore(self) -> bool:
        """Check .gitignore configuration and common patterns.

        Returns:
            True if .gitignore is properly configured, False otherwise
        """
        try:
            gitignore_path = ".gitignore"

            # Common patterns that should be ignored
            common_patterns = {
                "IDE": ["*.swp", ".idea/", ".vscode/", "*.sublime-*"],
                "Python": ["__pycache__/", "*.py[cod]", "*.so", "venv/", ".env"],
                "Node.js": ["node_modules/", "npm-debug.log", "yarn-debug.log*"],
                "macOS": [".DS_Store", ".AppleDouble", ".LSOverride"],
                "Windows": ["Thumbs.db", "Desktop.ini"],
                "Build": ["build/", "dist/", "*.egg-info/"],
            }

            if not os.path.exists(gitignore_path):
                self.add_issue(
                    "gitignore",
                    "warning",
                    ".gitignore file not found",
                    "touch .gitignore",
                )
                return False

            # Read current patterns
            with open(gitignore_path, "r") as f:
                current_patterns = set(
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                )

            # Check for missing common patterns
            for category, patterns in common_patterns.items():
                missing = [p for p in patterns if p not in current_patterns]
                if missing:
                    self.add_issue(
                        "gitignore",
                        "info",
                        f"Missing common {category} ignore patterns: {', '.join(missing)}",
                        f"echo '{chr(10).join(missing)}' >> .gitignore",
                    )

            # Check for tracked files that should be ignored
            status = GitCommand.run("git status --porcelain")
            for line in status.split("\n"):
                if not line:
                    continue

                status_code = line[:2]
                filename = line[3:]

                # Check if file matches any common pattern
                for patterns in common_patterns.values():
                    for pattern in patterns:
                        if pattern.endswith("/"):
                            if filename.startswith(pattern[:-1]):
                                self.add_issue(
                                    "gitignore",
                                    "warning",
                                    f"File '{filename}' matches common ignore pattern but is tracked",
                                    f"git rm --cached -r {filename}",
                                )
                        elif pattern.startswith("*."):
                            if filename.endswith(pattern[1:]):
                                self.add_issue(
                                    "gitignore",
                                    "warning",
                                    f"File '{filename}' matches common ignore pattern but is tracked",
                                    f"git rm --cached {filename}",
                                )

            return True

        except Exception as e:
            self.add_issue(
                "gitignore", "warning", f"Error checking .gitignore: {str(e)}"
            )
            return False

    def check_lfs_status(self) -> bool:
        """Check Git LFS configuration and tracked files.

        Returns:
            True if LFS is properly configured or not needed, False if issues found
        """
        try:
            # Check if Git LFS is installed
            try:
                GitCommand.run("git lfs version")
                lfs_installed = True
            except GitCommandError:
                lfs_installed = False

            # Check for potential LFS candidates
            large_files = []
            binary_extensions = {
                ".zip",
                ".pdf",
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".mp4",
                ".mov",
                ".bin",
            }

            status = GitCommand.run("git status --porcelain")
            for line in status.split("\n"):
                if not line:
                    continue

                filename = line[3:]
                ext = os.path.splitext(filename)[1].lower()

                if ext in binary_extensions:
                    try:
                        size = os.path.getsize(filename)
                        if size > 5 * 1024 * 1024:  # 5MB
                            large_files.append((filename, size))
                    except OSError:
                        continue

            if large_files and not lfs_installed:
                self.add_issue(
                    "lfs",
                    "warning",
                    "Large binary files detected but Git LFS not installed",
                    "git lfs install",
                )
                for filename, size in large_files:
                    self.add_issue(
                        "lfs",
                        "info",
                        f"Consider using Git LFS for: {filename} ({format_size(size)})",
                        f"git lfs track {filename}",
                    )
                return False

            if lfs_installed:
                # Check LFS configuration
                try:
                    lfs_files = GitCommand.run("git lfs ls-files")
                    if not lfs_files:
                        self.add_issue(
                            "lfs",
                            "info",
                            "Git LFS is installed but no files are tracked",
                        )
                except GitCommandError as e:
                    self.add_issue(
                        "lfs", "warning", f"Error checking LFS files: {str(e)}"
                    )

            return True

        except Exception as e:
            self.add_issue("lfs", "warning", f"Error checking LFS status: {str(e)}")
            return False

    def check_commit_history(self) -> bool:
        """Check commit history for potential issues.

        Returns:
            True if commit history is healthy, False if issues found
        """
        try:
            # Check for merge conflicts markers
            try:
                conflicts = GitCommand.run("git grep -l '^<<<<<<< HEAD' HEAD")
                if conflicts:
                    self.add_issue(
                        "history",
                        "critical",
                        "Unresolved merge conflict markers found",
                        "# Manually resolve conflicts in: "
                        + conflicts.replace("\n", ", "),
                    )
            except GitCommandError:
                pass  # No conflict markers found

            # Check for large commits
            large_commits = []
            log = GitCommand.run(
                "git log --pretty=format:'%h %ad %s' --date=short --numstat"
            )
            current_commit = None
            current_changes = 0

            for line in log.split("\n"):
                if not line:
                    continue
                if not line[0].isdigit():
                    if current_commit and current_changes > 500:
                        large_commits.append((current_commit, current_changes))
                    current_commit = line
                    current_changes = 0
                else:
                    added, deleted, _ = line.split("\t")
                    if added.isdigit() and deleted.isdigit():
                        current_changes += int(added) + int(deleted)

            if large_commits:
                for commit, changes in large_commits:
                    self.add_issue(
                        "history",
                        "warning",
                        f"Large commit detected: {commit} ({changes} changes)",
                        "# Consider breaking large commits into smaller ones",
                    )

            # Check for uncommitted changes
            status = GitCommand.get_status()
            if status:
                self.add_issue(
                    "history",
                    "info",
                    "Uncommitted changes present in working directory",
                    "git status",
                )

            return True

        except GitCommandError as e:
            self.add_issue(
                "history", "warning", f"Error checking commit history: {str(e)}"
            )
            return False

    def check_submodules(self) -> bool:
        """Check submodule configuration and status.

        Returns:
            True if submodules are properly configured or not present, False if issues found
        """
        try:
            # Check for submodule configuration
            if os.path.exists(".gitmodules"):
                try:
                    submodule_status = GitCommand.run("git submodule status")
                    for line in submodule_status.split("\n"):
                        if not line:
                            continue

                        status_char = line[0]
                        if status_char == "-":
                            self.add_issue(
                                "submodules",
                                "critical",
                                f"Uninitialized submodule in {line}",
                                "git submodule update --init --recursive",
                            )
                        elif status_char == "+":
                            self.add_issue(
                                "submodules",
                                "warning",
                                f"Submodule has uncommitted changes: {line}",
                                "# Check submodule status and commit changes",
                            )
                        elif status_char == "U":
                            self.add_issue(
                                "submodules",
                                "critical",
                                f"Submodule has merge conflicts: {line}",
                                "# Resolve conflicts in submodule",
                            )

                except GitCommandError as e:
                    self.add_issue(
                        "submodules", "critical", f"Error checking submodules: {str(e)}"
                    )
                    return False

            return True

        except Exception as e:
            self.add_issue(
                "submodules", "warning", f"Error checking submodules: {str(e)}"
            )
            return False

    def run_all_checks(self) -> bool:
        """Run all diagnostic checks.

        Returns:
            True if all critical checks pass, False otherwise
        """
        checks = [
            self.check_git_config,
            self.check_remote_connection,
            self.check_large_files,
            self.check_branch_status,
            self.check_hooks,
            self.check_gitignore,
            self.check_lfs_status,
            self.check_commit_history,
            self.check_submodules,
        ]

        all_critical_passed = True
        for check in checks:
            try:
                if not check():
                    all_critical_passed = False
            except Exception as e:
                self.add_issue(
                    "system", "critical", f"Error running {check.__name__}: {str(e)}"
                )
                all_critical_passed = False

        return all_critical_passed

    def apply_fixes(self) -> Tuple[int, int]:
        """Apply automated fixes for identified issues.

        Returns:
            Tuple of (number of fixes applied, number of fixes failed)
        """
        if not self.fix:
            return 0, 0

        fixes_applied = 0
        fixes_failed = 0

        for issue in self.issues:
            if issue["fix_command"] and not issue["fix_command"].startswith("#"):
                try:
                    if self.verbose:
                        print(f"Applying fix: {issue['fix_command']}")

                    GitCommand.run(issue["fix_command"])
                    self.fixes_applied.append(
                        f"Fixed {issue['category']}: {issue['message']}"
                    )
                    fixes_applied += 1

                except GitCommandError as e:
                    if self.verbose:
                        print(f"Fix failed: {str(e)}")
                    fixes_failed += 1

        return fixes_applied, fixes_failed

    def print_report(self) -> None:
        """Print the diagnostic report with issues and fixes."""
        if not self.issues:
            print("\n✨ No issues found - repository is healthy!")
            return

        # Group issues by severity
        severity_groups = {"critical": [], "warning": [], "info": []}

        for issue in self.issues:
            severity_groups[issue["severity"]].append(issue)

        # Print issues by severity
        print("\n📋 Repository Health Report")
        print("=" * 60)

        severity_icons = {"critical": "❌", "warning": "⚠️ ", "info": "ℹ️ "}

        for severity in ["critical", "warning", "info"]:
            issues = severity_groups[severity]
            if issues:
                print(f"\n{severity.upper()} Issues:")
                for issue in issues:
                    print(f"\n{severity_icons[severity]} {issue['message']}")
                    if issue["fix_command"]:
                        if issue["fix_command"].startswith("#"):
                            print(f"   Solution: {issue['fix_command'][2:]}")
                        else:
                            print(f"   Fix: {issue['fix_command']}")

        # Print applied fixes
        if self.fixes_applied:
            print("\n✅ Applied Fixes:")
            for fix in self.fixes_applied:
                print(f"• {fix}")

        print("\n" + "=" * 60)
