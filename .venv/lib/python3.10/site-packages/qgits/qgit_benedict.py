#!/usr/bin/env python3
"""QGit Benedict module for repository scanning and sensitive file management.

This module provides core functionality for:
1. Scanning repositories for potentially sensitive files
2. Managing .gitignore patterns
3. Handling tracked/untracked file operations
"""

import fnmatch
import os
from datetime import datetime
from time import sleep
from typing import Any, Dict, Generator, List, Tuple

from qgits.qgit_errors import (
    FileOperationError,
    GitCommandError,
    GitRepositoryError,
    GitStateError,
    format_error,
)
from qgits.qgit_git import GitCommand
from qgits.qgit_utils import (
    detect_risky_files,
    format_category_emoji,
    format_size,
    generate_gitignore_from_scan,
    group_files_by_pattern,
)

# Default patterns for sensitive files
DEFAULT_SENSITIVE_PATTERNS = [
    "*.db",
    "*.sqlite3",  # Database files
    "*.log",
    "logs/",  # Log files
    "__pycache__/",
    "*.pyc",  # Python cache
    ".env",
    ".venv/",
    "venv/",  # Virtual environments
    ".DS_Store",  # macOS files
    "node_modules/",  # Node.js modules
    "*.cache",
    ".cache/",  # Cache files
]

# CLI Formatting Constants
COLORS = {
    "HEADER": "\033[95m",
    "BLUE": "\033[94m",
    "CYAN": "\033[96m",
    "GREEN": "\033[92m",
    "WARNING": "\033[93m",
    "FAIL": "\033[91m",
    "ENDC": "\033[0m",
    "BOLD": "\033[1m",
    "UNDERLINE": "\033[4m",
}

SPINNERS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def _spinner(message: str) -> Generator[str, None, None]:
    """Generate spinner frames with message.

    Args:
        message: Message to display with spinner

    Yields:
        Formatted spinner frame
    """
    while True:
        for frame in SPINNERS:
            yield f"\r{COLORS['CYAN']}{frame}{COLORS['ENDC']} {message}"
            sleep(0.1)


def _format_header(text: str) -> str:
    """Format text as header.

    Args:
        text: Text to format

    Returns:
        Formatted header text
    """
    return f"\n{COLORS['HEADER']}{COLORS['BOLD']}{text}{COLORS['ENDC']}\n{'=' * (len(text) + 2)}"


def _format_subheader(text: str) -> str:
    """Format text as subheader.

    Args:
        text: Text to format

    Returns:
        Formatted subheader text
    """
    return f"\n{COLORS['BLUE']}{text}{COLORS['ENDC']}\n{'-' * (len(text) + 2)}"


def _format_success(text: str) -> str:
    """Format text as success message.

    Args:
        text: Text to format

    Returns:
        Formatted success text
    """
    return f"{COLORS['GREEN']}✓ {text}{COLORS['ENDC']}"


def _format_warning(text: str) -> str:
    """Format text as warning message.

    Args:
        text: Text to format

    Returns:
        Formatted warning text
    """
    return f"{COLORS['WARNING']}⚠ {text}{COLORS['ENDC']}"


def _format_error(text: str) -> str:
    """Format text as error message.

    Args:
        text: Text to format

    Returns:
        Formatted error text
    """
    return f"{COLORS['FAIL']}✗ {text}{COLORS['ENDC']}"


def scan_repository(
    directory: str = ".", batch_size: int = 1000
) -> Tuple[Dict[str, List[Dict[str, Any]]], int]:
    """Scan repository for potentially risky files.

    Args:
        directory: Directory to scan
        batch_size: Number of files to process in each batch

    Returns:
        Tuple of (scan results, total files scanned)

    Raises:
        FileOperationError: If file operations fail
    """
    try:
        print(_format_header("Repository Security Scan"))
        spinner = _spinner("Scanning repository for potentially risky files...")
        for frame in spinner:
            print(frame, end="", flush=True)
            # Break after a short time - in real implementation this would be tied to detect_risky_files progress
            sleep(0.5)
            break

        results, total_files = detect_risky_files(directory, batch_size)
        print(
            "\r" + _format_success("Scan completed successfully!") + " " * 50
        )  # Clear spinner line

        # Calculate and display summary statistics
        _display_scan_summary(results, total_files)

        return results, total_files

    except Exception as e:
        print(
            "\r" + _format_error(f"Scan failed: {str(e)}") + " " * 50
        )  # Clear spinner line
        raise FileOperationError(
            "Failed to scan repository", filepath=directory, operation="scan"
        ) from e


def _display_scan_summary(
    results: Dict[str, List[Dict[str, Any]]], total_files: int
) -> None:
    """Display formatted summary of scan results.

    Args:
        results: Scan results by category
        total_files: Total number of files scanned
    """
    # Calculate totals
    category_totals = {}
    total_size = 0
    for category, files in results.items():
        size = sum(file_info["size"] for file_info in files)
        category_totals[category] = {"count": len(files), "size": size}
        total_size += size

    # Print summary
    print(_format_header("📊 Scan Summary"))
    print(f"Total files scanned: {COLORS['BOLD']}{total_files:,}{COLORS['ENDC']}")
    total_risky = sum(len(files) for files in results.values())
    print(
        f"Total risky files found: {COLORS['WARNING' if total_risky > 0 else 'GREEN']}{total_risky:,}{COLORS['ENDC']}"
    )
    print(
        f"Total size of risky files: {COLORS['BOLD']}{format_size(total_size)}{COLORS['ENDC']}"
    )

    # Print category details
    for category, files in results.items():
        if not files:
            continue

        emoji = format_category_emoji(category)
        total_cat_size = category_totals[category]["size"]
        print(
            _format_subheader(
                f"{emoji} {category.title()} ({len(files)} files, {format_size(total_cat_size)})"
            )
        )
        _display_category_details(files)


def _display_category_details(files: List[Dict[str, Any]]) -> None:
    """Display detailed breakdown of files within a category.

    Args:
        files: List of file information dictionaries
    """
    pattern_groups = group_files_by_pattern(files)
    for pattern, group_files in pattern_groups.items():
        group_size = sum(f["size"] for f in group_files)
        print(f"\n  {COLORS['CYAN']}📎 Pattern: {pattern}{COLORS['ENDC']}")
        print(
            f"     Found {COLORS['BOLD']}{len(group_files)}{COLORS['ENDC']} files ({format_size(group_size)})"
        )

        # Show top 5 largest files
        sorted_files = sorted(group_files, key=lambda x: x["size"], reverse=True)
        for file_info in sorted_files[:5]:
            size_str = format_size(file_info["size"])
            print(
                f"     • {COLORS['BLUE']}{file_info['path']}{COLORS['ENDC']} ({size_str})"
            )

        if len(group_files) > 5:
            print(
                f"     {COLORS['WARNING']}... and {len(group_files) - 5} more files{COLORS['ENDC']}"
            )


def update_gitignore(
    scan_results: Dict[str, List[Dict[str, Any]]], auto_commit: bool = False
) -> bool:
    """Update .gitignore with patterns from scan results.

    Args:
        scan_results: Results from repository scan
        auto_commit: Whether to automatically commit changes

    Returns:
        True if update was successful, False otherwise

    Raises:
        GitCommandError: If Git operations fail
        GitStateError: If repository is in an invalid state
        GitRepositoryError: If not in a Git repository
        FileOperationError: If file operations fail
    """
    try:
        # Backup existing .gitignore
        if os.path.exists(".gitignore"):
            _backup_gitignore()

        # Generate and write new patterns
        _write_gitignore(generate_gitignore_from_scan(scan_results))
        print("✅ Updated .gitignore with recommended patterns!")

        # Handle auto-commit if requested
        if auto_commit:
            return _commit_gitignore_changes()

        return True

    except (
        GitCommandError,
        GitStateError,
        GitRepositoryError,
        FileOperationError,
    ) as e:
        print(format_error(e))
        return False


def _backup_gitignore() -> None:
    """Create a timestamped backup of the existing .gitignore file.

    Raises:
        FileOperationError: If backup operation fails
    """
    backup_path = f'.gitignore.backup-{datetime.now().strftime("%Y%m%d%H%M%S")}'
    try:
        os.rename(".gitignore", backup_path)
        print(_format_success(f"Existing .gitignore backed up to {backup_path}"))
    except OSError as e:
        raise FileOperationError(
            "Failed to backup .gitignore", filepath=".gitignore", operation="backup"
        ) from e


def _write_gitignore(content: str) -> None:
    """Write new content to .gitignore file.

    Args:
        content: New .gitignore content

    Raises:
        FileOperationError: If write operation fails
    """
    try:
        with open(".gitignore", "w") as f:
            f.write(content)
    except IOError as e:
        raise FileOperationError(
            "Failed to write .gitignore", filepath=".gitignore", operation="write"
        ) from e


def _commit_gitignore_changes() -> bool:
    """Commit and push .gitignore changes.

    Returns:
        True if successful, False otherwise
    """
    try:
        GitCommand.stage_files([".gitignore"])
        GitCommand.commit(
            "🔒 Update .gitignore with security patterns from qgit"
        )
        current_branch = GitCommand.get_current_branch()
        GitCommand.push("origin", current_branch)
        print("✅ Committed and synced updated .gitignore to repository")
        return True
    except (GitCommandError, GitStateError, GitRepositoryError) as e:
        print(f"⚠️  Warning: Could not commit .gitignore changes: {format_error(e)}")
        return False


def check_tracked_files(file_patterns: List[str] = None) -> Dict[str, Dict[str, Any]]:
    """Check for problematic files that are being tracked.

    Args:
        file_patterns: List of file patterns to check. If None, uses default patterns.

    Returns:
        Dictionary mapping filenames to their information

    Raises:
        GitCommandError: If Git operations fail
        GitStateError: If repository is in an invalid state
        GitRepositoryError: If not in a Git repository
        FileOperationError: If file operations fail
    """
    if file_patterns is None:
        file_patterns = DEFAULT_SENSITIVE_PATTERNS

    try:
        tracked_files = GitCommand.run("git ls-files").split("\n")
        return _find_problematic_files(tracked_files, file_patterns)

    except (GitCommandError, GitStateError, GitRepositoryError) as e:
        print(format_error(e))
        return {}


def _find_problematic_files(
    tracked_files: List[str], patterns: List[str]
) -> Dict[str, Dict[str, Any]]:
    """Find tracked files matching problematic patterns.

    Args:
        tracked_files: List of tracked file paths
        patterns: List of problematic patterns to check

    Returns:
        Dictionary of problematic files and their info

    Raises:
        FileOperationError: If file operations fail
    """
    problematic_files = {}

    for pattern in patterns:
        # Convert git pattern to Python glob pattern
        if pattern.startswith("*"):
            pattern = f".{pattern}"

        matches = [f for f in tracked_files if fnmatch.fnmatch(f, pattern)]

        for file in matches:
            try:
                size = os.path.getsize(file)
                problematic_files[file] = {"size": size, "pattern": pattern}
            except OSError as e:
                raise FileOperationError(
                    f"Failed to get size of file: {file}",
                    filepath=file,
                    operation="getsize",
                ) from e

    return problematic_files


def reverse_tracking(file_patterns: List[str] = None) -> bool:
    """Untrack files from git, add them to gitignore, and clean git history
    while preserving local files.

    Args:
        file_patterns: List of file patterns to untrack. If None, uses default patterns.

    Returns:
        True if operation was successful, False otherwise

    Raises:
        GitCommandError: If Git operations fail
        GitStateError: If repository is in an invalid state
        GitRepositoryError: If not in a Git repository
        FileOperationError: If file operations fail
    """
    problematic_files = check_tracked_files(file_patterns)

    if not problematic_files:
        print("No problematic files found in git tracking.")
        return True

    _display_problematic_files(problematic_files)

    response = input(
        "\nDo you want to untrack these files and update .gitignore? (y/N): "
    ).lower()
    if response != "y":
        print("Operation cancelled.")
        return False

    try:
        _update_gitignore_with_patterns(problematic_files)
        _untrack_problematic_files(problematic_files)
        return True

    except (
        GitCommandError,
        GitStateError,
        GitRepositoryError,
        FileOperationError,
    ) as e:
        print(format_error(e))
        return False


def _display_problematic_files(files: Dict[str, Dict[str, Any]]) -> None:
    """Display information about problematic tracked files.

    Args:
        files: Dictionary of problematic files and their info
    """
    print(_format_header("Problematic Tracked Files"))

    for file, info in files.items():
        size = info["size"]
        size_str = (
            f"{size/1024/1024:.2f} MB" if size > 1024 * 1024 else f"{size/1024:.2f} KB"
        )
        print(f"{COLORS['WARNING']}• {file}{COLORS['ENDC']} ({size_str})")
        print(f"  {COLORS['CYAN']}Matched by: {info['pattern']}{COLORS['ENDC']}")


def _update_gitignore_with_patterns(files: Dict[str, Dict[str, Any]]) -> None:
    """Update .gitignore with patterns from problematic files.

    Args:
        files: Dictionary of problematic files and their info

    Raises:
        FileOperationError: If file operations fail
    """
    patterns_to_add = set(info["pattern"] for info in files.values())

    try:
        with open(".gitignore", "a+") as f:
            f.seek(0)
            existing_patterns = f.read().splitlines()
            new_patterns = [p for p in patterns_to_add if p not in existing_patterns]
            if new_patterns:
                f.write("\n" + "\n".join(new_patterns) + "\n")
    except IOError as e:
        raise FileOperationError(
            "Failed to update .gitignore", filepath=".gitignore", operation="append"
        ) from e


def _untrack_problematic_files(files: Dict[str, Dict[str, Any]]) -> None:
    """Untrack problematic files from git history.

    Args:
        files: Dictionary of problematic files and their info

    Raises:
        GitCommandError: If Git operations fail
    """
    files_str = " ".join(f"'{f}'" for f in files.keys())

    print(_format_header("Untracking Files"))

    # Stage .gitignore changes
    print(_format_success("Staging .gitignore changes..."))
    GitCommand.stage_files([".gitignore"])

    print(_format_success("Committing changes..."))
    GitCommand.commit("Remove sensitive files and update .gitignore")

    # Clean up git history
    print(_format_warning("Cleaning git history (this may take a while)..."))
    GitCommand.run(
        f"git filter-branch --force --index-filter "
        f"'git rm -r --cached --ignore-unmatch {files_str}' "
        "--prune-empty --tag-name-filter cat -- --all"
    )

    print(
        "\n"
        + _format_success("Files have been untracked and .gitignore has been updated!")
    )
    print(
        _format_warning(
            "\nTo complete the process, force push to your repository with:"
        )
    )
    print(f"{COLORS['CYAN']}git push origin --force --all{COLORS['ENDC']}")


def _untrack_files_in_batches(files: List[str], batch_size: int = 100) -> None:
    """Untrack files in batches to avoid command line length limits.

    Args:
        files: List of files to untrack
        batch_size: Number of files to process in each batch
    """
    for i in range(0, len(files), batch_size):
        batch = files[i : i + batch_size]
        if not batch:
            continue
        files_str = " ".join(f'"{f}"' for f in batch)
        GitCommand.run(f"git rm -r --cached {files_str}")


def expel() -> bool:
    """Untrack all currently tracked files while preserving them locally.

    Returns:
        True if successful, False otherwise
    """
    try:
        print(_format_header("Untracking All Files"))

        # Get list of tracked files
        tracked_files = GitCommand.run("git ls-files").split("\n")
        tracked_files = [f for f in tracked_files if f]  # Remove empty strings

        if not tracked_files:
            print("No tracked files found.")
            return True

        # Show warning and get confirmation
        print(f"\nFound {len(tracked_files)} tracked files.")
        print(
            "\n⚠️  WARNING: This will untrack ALL files above from git while keeping them locally."
        )
        confirm = input("Are you sure? (y/N): ").lower()
        if confirm != "y":
            print("\nOperation cancelled.")
            return False

        print("\nUntracking All Files")
        print("======================")

        # Process files in batches with progress tracking
        total_batches = (len(tracked_files) + 99) // 100  # Round up division
        current_batch = 0

        for i in range(0, len(tracked_files), 100):
            current_batch += 1
            batch = tracked_files[i : i + 100]
            print(
                f"\rUntracking batch {current_batch}/{total_batches} ({len(batch)} files)...",
                end="",
                flush=True,
            )
            files_str = " ".join(f'"{f}"' for f in batch)
            GitCommand.run(f"git rm -r --cached {files_str}")

        print("\r" + _format_success("Successfully untracked all files") + " " * 50)

        # Print helpful next steps
        print("\n" + _format_warning("Next steps:"))
        print(
            f"1. {COLORS['CYAN']}Update your .gitignore to prevent re-tracking files{COLORS['ENDC']}"
        )
        print(
            f"2. {COLORS['CYAN']}Force push with: git push origin --force --all{COLORS['ENDC']}"
        )
        return True

    except (GitCommandError, GitStateError, GitRepositoryError) as e:
        print("\r" + _format_error(f"Failed to untrack files: {str(e)}") + " " * 50)
        return False

def _display_tracked_files(files: List[str]) -> None:
    """Display list of tracked files.

    Args:
        files: List of tracked file paths
    """
    print(_format_header("Currently Tracked Files"))
    for file in files:
        print(f"{COLORS['BLUE']}• {file}{COLORS['ENDC']}")
        
def _untrack_all_files(files: List[str]) -> None:
    """Untrack all specified files from git.

    Args:
        files: List of files to untrack

    Raises:
        GitCommandError: If Git operations fail
    """
    files_str = " ".join(f"'{f}'" for f in files)

    print(_format_header("Untracking All Files"))

    spinner = _spinner("Removing files from git tracking...")
    for frame in spinner:
        print(frame, end="", flush=True)
        GitCommand.run(f"git rm -r --cached {files_str}")
        break

    print("\r" + _format_success("Files removed from git tracking") + " " * 50)

    print(_format_success("Committing changes..."))
    GitCommand.commit("Untrack all files via qgit")

    print("\n" + _format_success("All files have been untracked successfully!"))
    print(_format_warning("\nTo complete the process:"))
    print(
        f"1. {COLORS['CYAN']}Update your .gitignore to prevent re-tracking{COLORS['ENDC']}"
    )
    print(
        f"2. {COLORS['CYAN']}Force push with: git push origin --force --all{COLORS['ENDC']}"
    )
