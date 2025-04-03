"""Module for safely removing files from Git history while preserving local copies."""

import os
import subprocess
from datetime import datetime
from typing import List, Optional

from qgits.qgit_logger import logger


def verify_local_files(patterns: List[str]) -> bool:
    """Verify that the specified patterns match files that exist locally.

    Args:
        patterns: List of file patterns to check

    Returns:
        True if verification passes, False otherwise
    """
    for pattern in patterns:
        try:
            # Use git ls-files to check if pattern matches any tracked files
            result = subprocess.run(
                ["git", "ls-files", pattern], capture_output=True, text=True, check=True
            )
            if not result.stdout.strip():
                logger.log(
                    level="warning",
                    command="cancel",
                    message=f"Pattern '{pattern}' doesn't match any tracked files",
                    metadata={"timestamp": datetime.now().isoformat()},
                )
                return False

            # Verify local files exist
            matched_files = result.stdout.strip().split("\n")
            for file in matched_files:
                if not os.path.exists(file):
                    logger.log(
                        level="error",
                        command="cancel",
                        message=f"Local file '{file}' not found",
                        metadata={"timestamp": datetime.now().isoformat()},
                    )
                    return False

        except subprocess.CalledProcessError as e:
            logger.log(
                level="error",
                command="cancel",
                message="Failed to verify files",
                metadata={"error": str(e), "timestamp": datetime.now().isoformat()},
            )
            return False

    return True


def cancel_files(
    patterns: List[str], from_commit: Optional[str] = None, verify: bool = True
) -> bool:
    """Remove specified files from Git history while preserving local copies.

    Args:
        patterns: List of file patterns to remove from history
        from_commit: Optional starting commit to remove files from
        verify: Whether to verify operation won't affect local files

    Returns:
        True if operation succeeded, False otherwise
    """
    try:
        # Verify local files if requested
        if verify and not verify_local_files(patterns):
            print("Verification failed. Aborting operation.")
            return False

        # Create backup branch
        current_branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
        backup_branch = f"backup/{current_branch}/pre-cancel-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        subprocess.run(["git", "branch", backup_branch], check=True)

        # Build filter-branch command
        cmd = ["git", "filter-branch", "--force", "--index-filter"]

        # Construct git rm command for each pattern
        rm_cmd = "git rm -rf --cached --ignore-unmatch " + " ".join(
            f'"{p}"' for p in patterns
        )
        cmd.extend([rm_cmd])

        # Add starting commit if specified
        if from_commit:
            cmd.extend([from_commit + "..HEAD"])

        # Run the filter-branch command
        subprocess.run(cmd, check=True)

        # Clean up
        subprocess.run(
            [
                "git",
                "for-each-ref",
                "--format=%(refname)",
                "refs/original/",
                "|",
                "xargs",
                "-n",
                "1",
                "git",
                "update-ref",
                "-d",
            ],
            check=True,
        )
        subprocess.run(["git", "reflog", "expire", "--expire=now", "--all"], check=True)
        subprocess.run(["git", "gc", "--prune=now"], check=True)

        logger.log(
            level="info",
            command="cancel",
            message="Successfully removed files from Git history",
            metadata={
                "patterns": patterns,
                "from_commit": from_commit,
                "backup_branch": backup_branch,
                "timestamp": datetime.now().isoformat(),
            },
        )

        print(
            f"Operation completed successfully. Backup branch created: {backup_branch}"
        )
        return True

    except subprocess.CalledProcessError as e:
        logger.log(
            level="error",
            command="cancel",
            message="Failed to remove files from history",
            metadata={"error": str(e), "timestamp": datetime.now().isoformat()},
        )
        print(f"Error: {str(e)}")
        return False
