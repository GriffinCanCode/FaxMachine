#!/usr/bin/env python3
"""Single source of truth for Git command operations.

This module provides a centralized interface for executing Git commands and
handling common Git operations. All other modules should use this interface
rather than implementing their own Git command execution.
"""

import subprocess
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from qgits.qgit_errors import (
    GitCommandError,
    GitConfigError,
    GitNetworkError,
    GitRepositoryError,
    GitStateError,
)
from .qgit_logger import logger


class GitCommand:
    """Centralized interface for Git operations.

    This class provides a single source of truth for executing Git commands
    and handling common Git operations. All other modules should use this
    interface rather than implementing their own Git command execution.
    """

    @staticmethod
    def run(command: str, check: bool = True) -> str:
        """Execute a Git command and return its output.

        Args:
            command: The Git command to execute
            check: Whether to raise an exception on non-zero exit codes

        Returns:
            The command output as string

        Raises:
            GitCommandError: If the command fails and check is True
            GitNetworkError: If the command fails due to network issues
            GitStateError: If the repository is in an invalid state
        """
        start_time = time.time()
        try:
            result = subprocess.run(
                command, shell=True, check=check, capture_output=True, text=True
            )
            duration = time.time() - start_time

            # Log successful command
            logger.log(
                level="info",
                command=command,
                message="Git command executed successfully",
                metadata={
                    "output": result.stdout.strip(),
                    "error": result.stderr.strip() if result.stderr else None,
                    "return_code": result.returncode,
                },
                status="success",
                duration=duration,
            )

            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip()
            duration = time.time() - start_time

            # Determine error type and log accordingly
            if any(
                s in error_msg.lower()
                for s in ["network", "connection refused", "ssh", "timeout"]
            ):
                error_type = "network"
                error_class = GitNetworkError
                error_msg = "Network error during Git operation"
            elif "not a git repository" in error_msg.lower():
                error_type = "repository"
                error_class = GitRepositoryError
                error_msg = "Not a Git repository"
            elif any(
                s in error_msg.lower()
                for s in ["index locked", "head locked", "ref locked"]
            ):
                error_type = "state"
                error_class = GitStateError
                error_msg = "Repository is in a locked state"
            else:
                error_type = "command"
                error_class = GitCommandError
                error_msg = f"Git command failed: {command}"

            # Log error
            logger.log(
                level="error",
                command=command,
                message=error_msg,
                metadata={
                    "error_type": error_type,
                    "error_output": e.stderr.strip(),
                    "return_code": e.returncode,
                },
                status="error",
                duration=duration,
            )

            if check:
                raise error_class(command, e.stderr.strip())
            return error_msg

    @classmethod
    def is_repo(cls) -> bool:
        """Check if current directory is a Git repository.

        Returns:
            True if current directory is a Git repo, False otherwise
        """
        try:
            cls.run("git rev-parse --is-inside-work-tree", check=False)
            return True
        except:
            return False

    @classmethod
    def get_current_branch(cls) -> str:
        """Get the name of the current Git branch.

        Returns:
            The name of the current branch

        Raises:
            GitCommandError: If not in a Git repository or other error
        """
        return cls.run("git rev-parse --abbrev-ref HEAD")

    @classmethod
    def get_staged_files(cls) -> List[str]:
        """Get list of staged files.

        Returns:
            List of filenames that are currently staged
        """
        return cls.run("git diff --cached --name-only").split("\n")

    @classmethod
    def get_modified_files(cls) -> List[str]:
        """Get list of modified files.

        Returns:
            List of filenames that have been modified but not staged
        """
        return cls.run("git ls-files -m").split("\n")

    @classmethod
    def get_untracked_files(cls) -> List[str]:
        """Get list of untracked files.

        Returns:
            List of filenames that are not tracked by Git
        """
        return cls.run("git ls-files --others --exclude-standard").split("\n")

    @classmethod
    def stage_files(cls, files: Optional[List[str]] = None) -> None:
        """Stage files for commit.

        Args:
            files: List of files to stage. If None, stages all changes.
        """
        start_time = time.time()
        try:
            if files:
                for file in files:
                    cls.run(f"git add '{file}'")
            else:
                cls.run("git add --all")

            duration = time.time() - start_time
            logger.log(
                level="info",
                command="stage_files",
                message="Files staged successfully",
                metadata={"files": files if files else "all"},
                status="success",
                duration=duration,
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.log(
                level="error",
                command="stage_files",
                message="Failed to stage files",
                metadata={"files": files if files else "all", "error": str(e)},
                status="error",
                duration=duration,
            )
            raise

    @classmethod
    def commit(cls, message: str, allow_empty: bool = False) -> str:
        """Create a new commit.

        Args:
            message: Commit message
            allow_empty: Whether to allow empty commits

        Returns:
            The hash of the new commit

        Raises:
            GitCommandError: If commit fails
        """
        start_time = time.time()
        try:
            cmd = ["git commit"]
            if allow_empty:
                cmd.append("--allow-empty")
            cmd.append(f"-m '{message}'")
            cls.run(" ".join(cmd))
            commit_hash = cls.run("git rev-parse HEAD")

            duration = time.time() - start_time
            logger.log(
                level="info",
                command="commit",
                message="Changes committed successfully",
                metadata={
                    "commit_message": message,
                    "commit_hash": commit_hash,
                    "allow_empty": allow_empty,
                },
                status="success",
                duration=duration,
            )

            return commit_hash

        except Exception as e:
            duration = time.time() - start_time
            logger.log(
                level="error",
                command="commit",
                message="Failed to commit changes",
                metadata={
                    "commit_message": message,
                    "allow_empty": allow_empty,
                    "error": str(e),
                },
                status="error",
                duration=duration,
            )
            raise

    @classmethod
    def push(
        cls,
        remote: str = "origin",
        branch: Optional[str] = None,
        force: bool = False,
        tags: bool = False,
    ) -> None:
        """Push changes to remote repository.

        Args:
            remote: Name of the remote repository
            branch: Branch to push. If None, pushes current branch
            force: Whether to force push
            tags: Whether to push tags
        """
        start_time = time.time()
        try:
            cmd = ["git push"]
            if force:
                cmd.append("--force-with-lease")
            if tags:
                cmd.append("--tags")
            cmd.append(remote)
            if branch:
                cmd.append(branch)
            else:
                # If no branch specified, get current branch
                current_branch = cls.get_current_branch()
                cmd.append(current_branch)
            cls.run(" ".join(cmd))

            duration = time.time() - start_time
            logger.log(
                level="info",
                command="push",
                message="Changes pushed successfully",
                metadata={
                    "remote": remote,
                    "branch": branch if branch else cls.get_current_branch(),
                    "force": force,
                    "tags": tags,
                },
                status="success",
                duration=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.log(
                level="error",
                command="push",
                message="Failed to push changes",
                metadata={
                    "remote": remote,
                    "branch": branch,
                    "force": force,
                    "tags": tags,
                    "error": str(e),
                },
                status="error",
                duration=duration,
            )
            raise

    @classmethod
    def pull(cls, remote: str = "origin", branch: Optional[str] = None) -> None:
        """Pull changes from remote repository.

        Args:
            remote: Name of the remote repository
            branch: Branch to pull. If None, pulls current branch
        """
        cmd = ["git pull", remote]
        if branch:
            cmd.append(branch)
        cls.run(" ".join(cmd))

    @classmethod
    def checkout(cls, target: str, create: bool = False) -> None:
        """Checkout a branch or commit.

        Args:
            target: Branch name or commit hash to checkout
            create: Whether to create a new branch
        """
        cmd = ["git checkout"]
        if create:
            cmd.append("-b")
        cmd.append(target)
        cls.run(" ".join(cmd))

    @classmethod
    def reset(cls, target: str = "HEAD", mode: str = "--mixed") -> None:
        """Reset the repository state.

        Args:
            target: Commit to reset to
            mode: Reset mode (--soft, --mixed, or --hard)
        """
        cls.run(f"git reset {mode} {target}")

    @classmethod
    def stash(
        cls, message: Optional[str] = None, include_untracked: bool = False
    ) -> None:
        """Stash changes.

        Args:
            message: Optional stash message
            include_untracked: Whether to include untracked files
        """
        cmd = ["git stash push"]
        if include_untracked:
            cmd.append("-u")
        if message:
            cmd.append(f'-m "{message}"')
        cls.run(" ".join(cmd))

    @classmethod
    def create_tag(cls, name: str, message: Optional[str] = None) -> None:
        """Create a new tag.

        Args:
            name: Tag name
            message: Optional tag message
        """
        cmd = ["git tag"]
        if message:
            cmd.extend(["-a", name, "-m", f"'{message}'"])
        else:
            cmd.append(name)
        cls.run(" ".join(cmd))

    @classmethod
    def delete_tag(cls, name: str) -> None:
        """Delete a tag.

        Args:
            name: Tag name to delete
        """
        cls.run(f"git tag -d {name}")

    @classmethod
    def get_config(cls, key: str) -> Optional[str]:
        """Get Git configuration value.

        Args:
            key: Configuration key

        Returns:
            Configuration value or None if not set

        Raises:
            GitConfigError: If there is an error accessing the configuration
        """
        try:
            return cls.run(f"git config --get {key}")
        except GitCommandError as e:
            if "key does not exist" in e.error_output.lower():
                return None
            raise GitConfigError(
                f"Error accessing Git config key: {key}",
                command=e.command,
                error_output=e.error_output,
            )

    @classmethod
    def set_config(cls, key: str, value: str, global_config: bool = False) -> None:
        """Set Git configuration value.

        Args:
            key: Configuration key
            value: Configuration value
            global_config: Whether to set in global config

        Raises:
            GitConfigError: If there is an error setting the configuration
        """
        try:
            cmd = ["git config"]
            if global_config:
                cmd.append("--global")
            cmd.extend([key, f"'{value}'"])
            cls.run(" ".join(cmd))
        except GitCommandError as e:
            raise GitConfigError(
                f"Error setting Git config key: {key}",
                command=e.command,
                error_output=e.error_output,
            )

    @classmethod
    def get_remote_url(cls, remote: str = "origin") -> Optional[str]:
        """Get URL of a remote repository.

        Args:
            remote: Name of the remote

        Returns:
            Remote URL or None if not set
        """
        try:
            return cls.run(f"git config --get remote.{remote}.url")
        except GitCommandError:
            return None

    @classmethod
    def add_remote(cls, name: str, url: str) -> None:
        """Add a new remote repository.

        Args:
            name: Remote name
            url: Remote URL
        """
        cls.run(f"git remote add {name} {url}")

    @classmethod
    def get_commit_info(cls, commit: str = "HEAD") -> Dict[str, str]:
        """Get information about a commit.

        Args:
            commit: Commit reference

        Returns:
            Dictionary containing commit information
        """
        format_str = "%H|%an|%ae|%at|%s"
        info = cls.run(f"git show -s --format='{format_str}' {commit}").split("|")
        return {
            "hash": info[0],
            "author_name": info[1],
            "author_email": info[2],
            "timestamp": datetime.fromtimestamp(int(info[3])),
            "message": info[4],
        }

    @classmethod
    def get_file_history(cls, path: str, max_entries: int = 10) -> List[Dict[str, Any]]:
        """Get commit history for a file.

        Args:
            path: File path
            max_entries: Maximum number of entries to return

        Returns:
            List of dictionaries containing commit information
        """
        format_str = "%H|%an|%ae|%at|%s"
        log = cls.run(f"git log -n {max_entries} --format='{format_str}' -- '{path}'")
        history = []

        for line in log.split("\n"):
            if not line:
                continue
            info = line.split("|")
            history.append(
                {
                    "hash": info[0],
                    "author_name": info[1],
                    "author_email": info[2],
                    "timestamp": datetime.fromtimestamp(int(info[3])),
                    "message": info[4],
                }
            )

        return history

    @classmethod
    def get_branch_list(cls, remote: bool = False) -> List[str]:
        """Get list of branches.

        Args:
            remote: Whether to list remote branches

        Returns:
            List of branch names
        """
        cmd = ["git branch"]
        if remote:
            cmd.append("-r")
        branches = cls.run(" ".join(cmd))
        return [b.strip().replace("* ", "") for b in branches.split("\n") if b]

    @classmethod
    def get_tag_list(cls) -> List[Tuple[str, Optional[str]]]:
        """Get list of tags with messages.

        Returns:
            List of tuples containing tag name and message
        """
        tags = cls.run("git tag -n").split("\n")
        result = []
        for tag in tags:
            if not tag:
                continue
            parts = tag.split(maxsplit=1)
            name = parts[0]
            message = parts[1] if len(parts) > 1 else None
            result.append((name, message))
        return result

    @classmethod
    def get_status(cls, porcelain: bool = False) -> str:
        """Get repository status.

        Args:
            porcelain: Whether to use machine-readable format

        Returns:
            Status string
        """
        cmd = ["git status"]
        if porcelain:
            cmd.append("--porcelain")
        return cls.run(" ".join(cmd))

    @classmethod
    def get_diff(cls, staged: bool = False, files: Optional[List[str]] = None) -> str:
        """Get diff of changes.

        Args:
            staged: Whether to show staged changes
            files: Optional list of files to show diff for

        Returns:
            Diff string
        """
        cmd = ["git diff"]
        if staged:
            cmd.append("--cached")
        if files:
            cmd.extend([f"'{f}'" for f in files])
        return cls.run(" ".join(cmd))
