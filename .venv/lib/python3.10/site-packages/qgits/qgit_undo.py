#!/usr/bin/env python3

from datetime import datetime
from typing import Any, Dict, List

from qgits.qgit_errors import (
    GitCommandError,
    GitRepositoryError,
    GitStateError,
    format_error,
)
from qgits.qgit_git import GitCommand
from qgits.qgit_snapshot import create_snapshot


def analyze_operations(operations: List[str]) -> List[Dict[str, Any]]:
    """Analyze git operations and return structured information.

    Args:
        operations: List of git reflog entries to analyze

    Returns:
        List of dictionaries containing analyzed operation information

    Raises:
        GitCommandError: If Git operations fail
        GitStateError: If repository is in an invalid state
    """
    analyzed_ops = []

    for op in operations:
        parts = op.split()
        if len(parts) < 3:
            continue

        ref, commit_hash, *action = parts
        action = " ".join(action)

        try:
            # Check if this operation affects any remote branches
            remote_branches = GitCommand.run(
                f"git branch -r --contains {commit_hash}"
            ).strip()

            operation_info = {
                "type": "unknown",
                "ref": ref,
                "commit": commit_hash,
                "action": action,
                "affects_remote": bool(remote_branches),
                "branches_affected": (
                    remote_branches.split("\n") if remote_branches else []
                ),
                "timestamp": GitCommand.get_commit_info(commit_hash)[
                    "timestamp"
                ].isoformat(),
            }

            # Categorize the operation
            if "commit" in action and "SNAPSHOT:" in action:
                operation_info["type"] = "snapshot"
            elif "checkout" in action:
                operation_info["type"] = "checkout"
            elif "merge" in action:
                operation_info["type"] = "merge"
            elif "commit" in action:
                operation_info["type"] = "commit"
            elif "reset" in action:
                operation_info["type"] = "reset"
            else:
                continue

            analyzed_ops.append(operation_info)

        except GitCommandError as e:
            print(
                f"Warning: Could not analyze operation {commit_hash}: {format_error(e)}"
            )
            continue

    return analyzed_ops


def show_impact_analysis(operations: List[Dict[str, Any]]) -> None:
    """Display detailed analysis of operations to be undone.

    Args:
        operations: List of analyzed operations to display
    """
    print("\n📊 Undo Impact Analysis:")
    print("=" * 60)

    # Group operations by type
    op_types = {}
    for op in operations:
        op_type = op["type"]
        if op_type not in op_types:
            op_types[op_type] = []
        op_types[op_type].append(op)

    # Show summary
    print("\n📋 Summary:")
    print("-" * 30)
    for op_type, ops in op_types.items():
        print(f"• {op_type.title()}: {len(ops)} operation(s)")

    # Show remote impact
    remote_ops = [op for op in operations if op["affects_remote"]]
    if remote_ops:
        print("\n⚠️  Remote Impact:")
        print("-" * 30)
        affected_branches = set()
        for op in remote_ops:
            affected_branches.update(op["branches_affected"])
        for branch in sorted(affected_branches):
            print(f"• {branch}")

    # Show detailed operations
    print("\n🔍 Detailed Operations:")
    print("-" * 60)
    for i, op in enumerate(operations, 1):
        print(f"\n{i}. {op['type'].upper()}")
        print(f"   Action: {op['action']}")
        print(f"   Time: {op['timestamp']}")
        if op["affects_remote"]:
            print("   ⚠️  Affects remote branches:")
            for branch in op["branches_affected"]:
                print(f"      - {branch}")

    print("\n" + "=" * 60)


def choose_operations_interactively(
    operations: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Allow user to interactively choose which operations to undo.

    Args:
        operations: List of analyzed operations to choose from

    Returns:
        List of selected operations to undo
    """
    if not operations:
        return []

    print("\n🔍 Select operations to undo:")
    print("=" * 60)

    selected_ops = []
    for i, op in enumerate(operations, 1):
        print(f"\n{i}. {op['type'].upper()}")
        print(f"   Action: {op['action']}")
        print(f"   Time: {op['timestamp']}")
        if op["affects_remote"]:
            print("   ⚠️  Affects remote branches:")
            for branch in op["branches_affected"]:
                print(f"      - {branch}")

        while True:
            response = input("\nUndo this operation? (y/n/q): ").lower()
            if response == "q":
                print("\nOperation cancelled.")
                return []
            elif response in ("y", "n"):
                if response == "y":
                    selected_ops.append(op)
                break
            else:
                print("Please enter 'y' for yes, 'n' for no, or 'q' to quit")

    if not selected_ops:
        print("\nNo operations selected.")
        return []

    print("\n✓ Selected operations to undo:")
    for i, op in enumerate(selected_ops, 1):
        print(f"{i}. {op['type']}: {op['action']}")

    confirm = input("\nProceed with these operations? (y/N): ").lower()
    return selected_ops if confirm == "y" else []


def execute_undo_operations(
    operations: List[Dict[str, Any]], reset_type: str = "--mixed"
) -> bool:
    """Execute the undo operations with proper error handling.

    Args:
        operations: List of operations to undo
        reset_type: Type of reset to perform (--mixed, --soft, --hard)

    Returns:
        True if all operations were undone successfully, False otherwise

    Raises:
        GitCommandError: If Git operations fail
        GitStateError: If repository is in an invalid state
        GitRepositoryError: If not in a Git repository
    """
    try:
        for op in operations:
            print(f"\n🔄 Undoing: {op['type']} - {op['action']}")

            if op["type"] == "snapshot":
                GitCommand.reset("HEAD~1", mode=reset_type)
                # Remove associated tag if it exists
                tag_name = f"snapshot/{op['ref']}"
                try:
                    GitCommand.delete_tag(tag_name)
                except GitCommandError:
                    pass

            elif op["type"] == "checkout":
                GitCommand.checkout(op["ref"])

            elif op["type"] == "merge":
                GitCommand.reset("ORIG_HEAD", mode=reset_type)

            elif op["type"] == "commit":
                GitCommand.reset("HEAD~1", mode=reset_type)

            elif op["type"] == "reset":
                GitCommand.reset(op["ref"], mode=reset_type)

            print(f"✓ Successfully undid {op['type']}")

        return True

    except (GitCommandError, GitStateError, GitRepositoryError) as e:
        print(format_error(e))
        return False


def show_completion_status(operations: List[Dict[str, Any]]) -> None:
    """Show final status after completing undo operations.

    Args:
        operations: List of operations that were undone

    Raises:
        GitCommandError: If Git operations fail
        GitStateError: If repository is in an invalid state
    """
    print("\n✨ Undo Operations Completed")
    print("=" * 60)

    # Show summary of completed operations
    print("\n📋 Completed Actions:")
    op_counts = {}
    for op in operations:
        op_type = op["type"]
        op_counts[op_type] = op_counts.get(op_type, 0) + 1

    for op_type, count in op_counts.items():
        print(f"• Undid {count} {op_type} operation(s)")

    try:
        # Show current status
        status = GitCommand.get_status()
        if status:
            print("\n📄 Current Status:")
            print("-" * 30)
            print(status)

        # Show branch status
        current_branch = GitCommand.get_current_branch()
        if current_branch != "HEAD":
            try:
                behind_ahead = GitCommand.run(
                    f"git rev-list --left-right --count origin/{current_branch}...HEAD"
                ).split()
                if behind_ahead and len(behind_ahead) == 2:
                    behind, ahead = map(int, behind_ahead)
                    print("\n📊 Branch Status:")
                    print("-" * 30)
                    if ahead > 0:
                        print(f"• Your branch is ahead by {ahead} commit(s)")
                        print(
                            "  To push these changes: git push --force-with-lease origin "
                            + current_branch
                        )
                    if behind > 0:
                        print(f"• Your branch is behind by {behind} commit(s)")
                        print("  To update: git pull origin " + current_branch)
            except GitCommandError:
                pass

        print("\n" + "=" * 60)

    except (GitCommandError, GitStateError) as e:
        print(format_error(e))


def undo_operation(
    steps: int = 1,
    force: bool = False,
    dry_run: bool = False,
    no_backup: bool = False,
    interactive: bool = False,
    keep_changes: bool = False,
    remote_safe: bool = False,
) -> bool:
    """Safely undo recent git operations.

    Args:
        steps: Number of operations to undo
        force: Whether to force the operation even with uncommitted changes
        dry_run: Whether to only show what would be done
        no_backup: Whether to skip creating a backup branch
        interactive: Whether to interactively choose operations
        keep_changes: Whether to keep changes in working directory
        remote_safe: Whether to prevent undoing operations affecting remotes

    Returns:
        True if operations were undone successfully, False otherwise

    Raises:
        GitRepositoryError: If not in a Git repository
        GitStateError: If repository is in an invalid state
        GitCommandError: If Git operations fail
    """
    try:
        # Verify we're in a git repository
        if not GitCommand.is_repo():
            raise GitRepositoryError(
                "Not a Git repository", command=None, error_output=None
            )

        # Check for uncommitted changes
        status = GitCommand.get_status(porcelain=True)
        if status and not force:
            print("\n⚠️  You have uncommitted changes.")
            response = input(
                "Would you like to create a snapshot before proceeding? (Y/n): "
            ).lower()
            if response != "n":
                if not create_snapshot(message="Backup before undo operation"):
                    print("Failed to create backup snapshot. Aborting...")
                    return False

        # Create backup branch if requested
        backup_branch = None
        if not no_backup:
            backup_branch = f"backup/undo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            GitCommand.run(f"git branch {backup_branch}")
            print(f"\n✨ Created backup branch: {backup_branch}")

        try:
            # Get recent operations
            operations = GitCommand.run("git reflog --format='%h %gs' -n 50").split(
                "\n"
            )
            analyzed_ops = analyze_operations(operations)

            # Filter to requested number of operations
            operations_to_undo = analyzed_ops[:steps]

            if not operations_to_undo:
                print("No operations found to undo.")
                return False

            # Show impact analysis
            show_impact_analysis(operations_to_undo)

            # Check for remote impact if requested
            if remote_safe:
                remote_ops = [op for op in operations_to_undo if op["affects_remote"]]
                if remote_ops:
                    print("\n❌ Cannot proceed: Some operations affect remote branches")
                    print("Use --force to override this check")
                    return False

            # Allow interactive selection if requested
            if interactive:
                operations_to_undo = choose_operations_interactively(operations_to_undo)
                if not operations_to_undo:
                    return False

            # Execute operations
            if not dry_run:
                reset_type = "--soft" if keep_changes else "--mixed"
                if execute_undo_operations(operations_to_undo, reset_type):
                    show_completion_status(operations_to_undo)
                    return True
            else:
                print("\n🔍 Dry run completed. No changes were made.")
                return True

        except (GitCommandError, GitStateError) as e:
            print(format_error(e))
            # Try to recover using backup branch
            if backup_branch:
                print("\nAttempting to recover using backup branch...")
                try:
                    GitCommand.checkout(backup_branch)
                    print("✓ Successfully recovered to backup state")
                except GitCommandError as e:
                    print(format_error(e))
                    print("❌ Recovery failed. Please check git reflog manually.")
            return False

    except (GitCommandError, GitStateError, GitRepositoryError) as e:
        print(format_error(e))
        return False
