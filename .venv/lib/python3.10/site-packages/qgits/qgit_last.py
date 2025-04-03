#!/usr/bin/env python3
"""QGit last command implementation for managing commit checkouts with safespace integration."""

import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

from qgits.qgit_core import run_command
from qgits.qgit_errors import GitCommandError, GitStateError
from qgits.qgit_logger import logger

def get_recent_commits(count: int = 10) -> List[Tuple[str, str, str]]:
    """Get recent commits with their hashes and messages.
    
    Args:
        count: Number of recent commits to fetch
        
    Returns:
        List of tuples containing (hash, date, message)
    """
    try:
        # Validate input
        count = max(1, min(count, 100))  # Limit between 1 and 100
        
        cmd = f'git log -n {count} --pretty=format:"%H|%ad|%s" --date=short'
        output = run_command(cmd)
        commits = []
        for line in output.strip().split('\n'):
            if line and line.count('|') == 2:  # Validate line format
                hash_val, date, message = line.split('|', 2)
                if len(hash_val) == 40:  # Validate hash length
                    commits.append((hash_val, date, message))
        return commits
    except GitCommandError as e:
        logger.log(
            level="error",
            command="last",
            message="Failed to get recent commits",
            metadata={"error": str(e)}
        )
        return []

def create_safespace(commit_hash: str) -> str:
    """Create a safespace directory for current changes.
    
    Args:
        commit_hash: Hash of the commit being checked out
        
    Returns:
        Path to created safespace directory
        
    Raises:
        GitStateError: If safespace creation fails
    """
    # Validate commit hash
    if not commit_hash or not commit_hash.isalnum() or len(commit_hash) != 40:
        raise GitStateError("Invalid commit hash")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safespace_dir = Path(f".safespace_{commit_hash[:8]}_{timestamp}")
    temp_dir = None
    
    try:
        # Create temporary directory first
        temp_dir = Path(tempfile.mkdtemp(prefix="qgit_safespace_"))
        temp_dir.chmod(0o700)
        
        # Save metadata
        metadata = {
            "commit_hash": commit_hash,
            "created_at": datetime.now().isoformat(),
            "branch": run_command("git rev-parse --abbrev-ref HEAD").strip(),
            "working_dir": os.getcwd(),
            "current_commit": run_command("git rev-parse HEAD").strip()
        }
        
        with open(temp_dir / "metadata.json", "w") as f:
            import json
            json.dump(metadata, f, indent=2)
        
        # Save current state including staged changes
        with open(temp_dir / "changes.patch", "w") as f:
            try:
                # Save both staged and unstaged changes
                staged_changes = run_command("git diff --staged")
                unstaged_changes = run_command("git diff")
                f.write("# Staged changes\n")
                f.write(staged_changes)
                f.write("\n# Unstaged changes\n")
                f.write(unstaged_changes)
            except GitCommandError:
                # Handle case where there might be no HEAD
                pass
        
        # Save current directory state
        with open(temp_dir / "status", "w") as f:
            f.write(run_command("git status --porcelain"))
        
        # Save all tracked files in their current state
        current_files = run_command("git ls-files").split("\n")
        tracked_dir = temp_dir / "tracked"
        tracked_dir.mkdir(mode=0o700)
        
        for file_path in current_files:
            if file_path.strip():
                try:
                    src_path = Path(file_path).resolve()
                    if not src_path.is_relative_to(Path.cwd()):
                        continue
                        
                    dest_path = tracked_dir / file_path
                    dest_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
                    
                    if src_path.is_file():
                        shutil.copy2(src_path, dest_path)
                except (OSError, shutil.Error) as e:
                    logger.log(
                        level="warning",
                        command="last",
                        message=f"Failed to copy tracked file {file_path}: {str(e)}"
                    )
        
        # Save untracked files
        status_output = run_command("git status --porcelain")
        untracked_dir = temp_dir / "untracked"
        untracked_dir.mkdir(mode=0o700)
        
        for line in status_output.split('\n'):
            if line.startswith('??'):
                src_file = line[3:].strip()
                if not os.path.exists(src_file):
                    continue
                    
                # Ensure path is safe
                try:
                    src_path = Path(src_file).resolve()
                    if not src_path.is_relative_to(Path.cwd()):
                        logger.log(
                            level="warning",
                            command="last",
                            message=f"Skipping file outside working directory: {src_file}"
                        )
                        continue
                except (ValueError, RuntimeError):
                    continue
                
                dest_path = untracked_dir / src_file
                dest_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
                
                try:
                    if src_path.is_file():
                        shutil.copy2(src_path, dest_path)
                    elif src_path.is_dir():
                        shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
                except (OSError, shutil.Error) as e:
                    logger.log(
                        level="warning",
                        command="last",
                        message=f"Failed to copy {src_file}: {str(e)}"
                    )
        
        # Atomically move temporary directory to final location
        if safespace_dir.exists():
            raise GitStateError(f"Safespace directory already exists: {safespace_dir}")
        
        shutil.move(str(temp_dir), str(safespace_dir))
        return str(safespace_dir)
        
    except Exception as e:
        # Clean up temporary directory in case of failure
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise GitStateError(f"Failed to create safespace: {str(e)}")

def checkout_commit(commit_hash: str, safespace_dir: Optional[str] = None) -> None:
    """Checkout a specific commit, optionally saving current changes to safespace.
    
    Args:
        commit_hash: Hash of commit to checkout
        safespace_dir: Directory where changes are saved
        
    Raises:
        GitStateError: If checkout fails
    """
    # Validate commit hash
    if not commit_hash or not commit_hash.isalnum() or len(commit_hash) != 40:
        raise GitStateError("Invalid commit hash")
    
    try:
        # Verify commit exists using rev-parse instead of cat-file
        try:
            run_command(f"git rev-parse --verify {commit_hash}^{{commit}}")
        except GitCommandError:
            raise GitStateError(f"Commit {commit_hash} does not exist")
        
        if safespace_dir:
            # Check for uncommitted changes
            status = run_command("git status --porcelain")
            if status.strip():
                stash_msg = f'Temporary stash for qgit last ({datetime.now().isoformat()})'
                run_command(f"git stash save '{stash_msg}'")
                logger.log(
                    level="info",
                    command="last",
                    message="Changes stashed",
                    metadata={"stash_message": stash_msg}
                )
        
        # Create backup branch
        current_branch = run_command("git rev-parse --abbrev-ref HEAD").strip()
        backup_branch = f"backup_{current_branch}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        run_command(f"git branch {backup_branch}")
        
        # Checkout the commit
        run_command(f"git checkout {commit_hash}")
        
        logger.log(
            level="info",
            command="last",
            message="Commit checked out successfully",
            metadata={
                "commit": commit_hash,
                "backup_branch": backup_branch,
                "safespace": safespace_dir
            }
        )
        
    except GitCommandError as e:
        raise GitStateError(f"Failed to checkout commit: {str(e)}")

def complete_last(safespace_dir: str) -> None:
    """Clean up safespace directory after finishing with the old version.
    
    Args:
        safespace_dir: Path to safespace directory to clean up
        
    Raises:
        GitStateError: If cleanup fails
    """
    try:
        safespace_path = Path(safespace_dir)
        
        # Validate safespace directory
        if not safespace_path.is_absolute():
            safespace_path = Path.cwd() / safespace_path
            
        if not safespace_path.exists():
            raise GitStateError(f"Safespace directory not found: {safespace_dir}")
            
        if not safespace_path.name.startswith('.safespace_'):
            raise GitStateError(f"Invalid safespace directory: {safespace_dir}")
            
        # Verify it's a safespace directory by checking for metadata
        if not (safespace_path / "metadata.json").exists():
            raise GitStateError(f"Invalid safespace directory (no metadata): {safespace_dir}")
            
        # Remove directory with error handling
        try:
            shutil.rmtree(safespace_path)
        except PermissionError:
            # If permission error, try to fix permissions first
            for root, dirs, files in os.walk(safespace_path):
                for d in dirs:
                    os.chmod(os.path.join(root, d), 0o700)
                for f in files:
                    os.chmod(os.path.join(root, f), 0o600)
            shutil.rmtree(safespace_path)
            
        logger.log(
            level="info",
            command="last",
            message="Safespace cleaned up successfully",
            metadata={"safespace": str(safespace_path)}
        )
            
    except OSError as e:
        raise GitStateError(f"Failed to clean up safespace: {str(e)}") 