#!/usr/bin/env python3

from datetime import datetime, timedelta
from typing import Optional

from qgits.qgit_errors import (
    GitCommandError,
    GitRepositoryError,
    GitStateError,
    format_error,
)
from qgits.qgit_git import GitCommand


def create_snapshot(
    message: Optional[str] = None,
    no_tag: bool = False,
    push: bool = False,
    stash: bool = False,
    branch: Optional[str] = None,
    expire_days: Optional[int] = None,
    include_untracked: bool = False,
) -> bool:
    """Create a temporary commit of current changes that can be easily restored.

    Args:
        message: Optional snapshot message
        no_tag: Whether to skip creating a tag
        push: Whether to push changes to remote
        stash: Whether to use git stash instead of commit
        branch: Optional new branch name to create
        expire_days: Optional number of days until snapshot expires
        include_untracked: Whether to include untracked files

    Returns:
        True if snapshot was created successfully, False otherwise

    Raises:
        GitRepositoryError: If not in a Git repository
        GitStateError: If repository is in an invalid state
        GitCommandError: If Git operations fail
    """
    # Check for uncommitted changes
    try:
        status = GitCommand.get_status(porcelain=True)
        if not status:
            print("No changes to snapshot.")
            return False

        # Get current timestamp for snapshot ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_id = f"snapshot_{timestamp}"

        if stash:
            # Use git stash with custom message
            stash_message = message or f"Snapshot {snapshot_id}"
            GitCommand.stash(message=stash_message, include_untracked=include_untracked)
            print(f"✨ Created snapshot stash: {stash_message}")
            return True

        if branch:
            # Create and switch to new branch
            GitCommand.checkout(branch, create=True)
            print(f"Created new branch: {branch}")

        # Stage changes
        if include_untracked:
            GitCommand.stage_files()
        else:
            GitCommand.stage_files(GitCommand.get_modified_files())

        # Create commit
        snapshot_message = message or "Temporary snapshot"
        commit_message = f"SNAPSHOT: {snapshot_message} ({snapshot_id})"
        GitCommand.commit(commit_message)

        if not no_tag:
            # Create a tag for easy reference
            tag_name = f"snapshot/{snapshot_id}"
            tag_message = None
            if expire_days:
                expiry_date = (datetime.now() + timedelta(days=expire_days)).strftime(
                    "%Y-%m-%d"
                )
                tag_message = f"Expires: {expiry_date}"
            GitCommand.create_tag(tag_name, message=tag_message)
            print(f"✨ Created snapshot: {snapshot_id}")
            print(f"To restore this snapshot later, use: git checkout {tag_name}")

        if push:
            current_branch = GitCommand.get_current_branch()
            GitCommand.push("origin", current_branch, tags=not no_tag)
            print("Pushed snapshot to remote")

        return True

    except (GitCommandError, GitStateError, GitRepositoryError) as e:
        print(format_error(e))
        return False


def list_snapshots() -> None:
    """List all available snapshots with their details.

    Raises:
        GitCommandError: If Git operations fail
        GitStateError: If repository is in an invalid state
        GitRepositoryError: If not in a Git repository
    """
    try:
        # Get all snapshot tags
        tags = GitCommand.run("git tag -l 'snapshot/*'").split("\n")
        if not tags or not tags[0]:
            print("No snapshots found.")
            return

        print("\n📸 Available Snapshots:")
        print("=" * 60)

        for tag in tags:
            try:
                # Get tag details
                tag_info = GitCommand.run(f"git show-ref -d {tag}").split()[0]
                commit_info = GitCommand.get_commit_info(tag_info)

                # Extract snapshot ID from message
                snapshot_id = commit_info["message"].split("(")[-1].rstrip(")")

                # Get expiry info if available
                try:
                    expiry = GitCommand.run(f"git tag -l --format='%(contents)' {tag}")
                    if "Expires:" in expiry:
                        expiry_date = expiry.split("Expires:")[1].strip()
                        expiry_info = f"(Expires: {expiry_date})"
                    else:
                        expiry_info = ""
                except GitCommandError:
                    expiry_info = ""

                print(f"\n• Snapshot: {snapshot_id}")
                print(f"  Created: {commit_info['timestamp']}")
                print(
                    f"  Message: {commit_info['message'].split(':')[1].split('(')[0].strip()}"
                )
                if expiry_info:
                    print(f"  {expiry_info}")
                print(f"  Commit:  {commit_info['hash'][:8]}")
            except GitCommandError as e:
                print(f"Error reading snapshot {tag}: {format_error(e)}")

        print("\n" + "=" * 60)
        print("To restore a snapshot: git checkout <snapshot-tag>")
        print("To delete a snapshot: git tag -d <snapshot-tag>")

    except (GitCommandError, GitStateError, GitRepositoryError) as e:
        print(format_error(e))


def cleanup_snapshots(days: int = 30) -> None:
    """Clean up expired snapshots older than specified days.

    Args:
        days: Number of days to keep snapshots for

    Raises:
        GitCommandError: If Git operations fail
        GitStateError: If repository is in an invalid state
        GitRepositoryError: If not in a Git repository
    """
    try:
        # Get all snapshot tags
        tags = GitCommand.run("git tag -l 'snapshot/*'").split("\n")
        if not tags or not tags[0]:
            print("No snapshots found.")
            return

        cleaned = 0
        cutoff_date = datetime.now() - timedelta(days=days)

        print(f"\n🧹 Cleaning up snapshots older than {days} days...")
        print("=" * 60)

        for tag in tags:
            try:
                # Get tag creation date
                tag_info = GitCommand.run(f"git show-ref -d {tag}").split()[0]
                commit_info = GitCommand.get_commit_info(tag_info)
                tag_date = commit_info["timestamp"]

                # Check expiry info
                try:
                    expiry = GitCommand.run(f"git tag -l --format='%(contents)' {tag}")
                    if "Expires:" in expiry:
                        expiry_date = datetime.strptime(
                            expiry.split("Expires:")[1].strip(), "%Y-%m-%d"
                        )
                        if expiry_date <= datetime.now():
                            GitCommand.delete_tag(tag)
                            print(f"Removed expired snapshot: {tag}")
                            cleaned += 1
                            continue
                except GitCommandError:
                    pass

                # Check age
                if tag_date.replace(tzinfo=None) < cutoff_date:
                    GitCommand.delete_tag(tag)
                    print(f"Removed old snapshot: {tag}")
                    cleaned += 1

            except GitCommandError as e:
                print(f"Error processing snapshot {tag}: {format_error(e)}")

        print("\n" + "=" * 60)
        if cleaned:
            print(f"✨ Cleaned up {cleaned} snapshot(s)")
        else:
            print("No snapshots needed cleaning")

    except (GitCommandError, GitStateError, GitRepositoryError) as e:
        print(format_error(e))


def restore_snapshot(snapshot_id: str) -> bool:
    """Restore a specific snapshot by ID or tag.

    Args:
        snapshot_id: The ID or tag of the snapshot to restore

    Returns:
        True if snapshot was restored successfully, False otherwise

    Raises:
        GitCommandError: If Git operations fail
        GitStateError: If repository is in an invalid state
        GitRepositoryError: If not in a Git repository
    """
    try:
        # Check if snapshot exists
        tag = (
            f"snapshot/{snapshot_id}"
            if not snapshot_id.startswith("snapshot/")
            else snapshot_id
        )
        tags = GitCommand.get_tag_list()
        tag_names = [t[0] for t in tags]

        if tag not in tag_names:
            print(f"Snapshot {snapshot_id} not found.")
            return False

        # Check for uncommitted changes
        status = GitCommand.get_status(porcelain=True)
        if status:
            print("\n⚠️  You have uncommitted changes.")
            response = input(
                "Would you like to stash them before proceeding? (Y/n): "
            ).lower()
            if response != "n":
                GitCommand.stash(message="Changes before snapshot restore")
                print("Changes stashed.")

        # Restore snapshot
        GitCommand.checkout(tag)
        print(f"✨ Restored snapshot: {snapshot_id}")

        # Check if snapshot has expired
        try:
            expiry = GitCommand.run(f"git tag -l --format='%(contents)' {tag}")
            if "Expires:" in expiry:
                expiry_date = datetime.strptime(
                    expiry.split("Expires:")[1].strip(), "%Y-%m-%d"
                )
                if expiry_date <= datetime.now():
                    print("\n⚠️  Note: This snapshot has expired.")
                    print(
                        "You may want to create a new snapshot or commit these changes permanently."
                    )
        except GitCommandError:
            pass

        return True

    except (GitCommandError, GitStateError, GitRepositoryError) as e:
        print(format_error(e))
        return False
