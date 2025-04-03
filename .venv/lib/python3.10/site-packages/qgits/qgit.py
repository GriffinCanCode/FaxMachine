"""Main entry point for QGit commands."""

import argparse
import sys
from typing import Optional
import os
from pathlib import Path

from qgits.qgit_commands import (
    BenedictCommand,
    StatsCommand,
    DoctorCommand,
    LastCommand,
    ShoveCommand,
    LeaderboardCommand,
    GPGCommand,
)
from qgits.qgit_author import AuthorCommand
from qgits.qgit_dict import QGIT_COMMANDS
from qgits.setup_verification import ensure_git_setup
from qgits.qgit_snapshot import create_snapshot, list_snapshots, cleanup_snapshots
from qgits.qgit_undo import undo_operation
from qgits.qgit_visuals import visualize_repo
from qgits.qgit_gui import run_gui, show_help
from qgits.qgit_errors import (
    GitCommandError,
    GitConfigError,
    GitRepositoryError,
    GitStateError,
    GitNetworkError,
    FileOperationError,
    format_error,
)
from qgits.qgit_git import GitCommand
from qgits.qgit_logger import logger
from qgits.qgit_cancel import cancel_files

def setup_environment():
    """Set up the QGit environment."""
    try:
        # Ensure QGit directories exist
        home = os.path.expanduser("~")
        qgit_dir = os.path.join(home, ".qgit")
        os.makedirs(qgit_dir, exist_ok=True)
        os.makedirs(os.path.join(qgit_dir, "logs"), exist_ok=True)
        os.makedirs(os.path.join(qgit_dir, "cache"), exist_ok=True)

        # Set up logging
        logger.log(
            level="info",
            command="setup",
            message="QGit environment initialized",
            metadata={"qgit_dir": qgit_dir}
        )

        return True
    except Exception as e:
        print(f"Error setting up QGit environment: {str(e)}")
        return False

def main() -> Optional[int]:
    """Main entry point for QGit commands."""
    try:
        # Set up environment first
        if not setup_environment():
            return 1

        # Parse command line arguments
        parser = argparse.ArgumentParser(description="QGit - A Git operations automation tool")
        parser.add_argument("--version", action="version", version="%(prog)s 1.1.5")
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Register all commands with their descriptions and arguments
        commands = {
            "makegpg": (GPGCommand(), "Configure GPG signing for Git commits", {}),
            "benedict": (BenedictCommand(), "Scan for sensitive files", {
                "--arnold": ("store_true", "Automatically handle sensitive files"),
                "--patterns": (str, "Custom patterns to scan for"),
                "--update": ("store_true", "Update .gitignore automatically"),
                "--reverse": ("store_true", "Untrack matched files")
            }),
            "stats": (StatsCommand(), "Generate repository statistics", {
                "--author": (str, "Filter stats by author"),
                "--team": ("store_true", "Show team collaboration stats"),
                "--files": ("store_true", "Show file-level statistics"),
                "--from": (str, "Start date for analysis (YYYY-MM-DD)"),
                "--to": (str, "End date for analysis (YYYY-MM-DD)"),
                "--format": (str, "Output format (text/json)"),
                "--leaderboard": ("store_true", "Show interactive leaderboard of contributors")
            }),
            "doctor": (DoctorCommand(), "Check repository health", {
                "--verbose": ("store_true", "Show detailed diagnostic information"),
                "--fix": ("store_true", "Attempt to fix issues automatically"),
                "--check-remote": ("store_true", "Include remote repository checks"),
                "--check-lfs": ("store_true", "Include Git LFS configuration checks"),
                "--check-hooks": ("store_true", "Include Git hooks validation")
            }),
            "last": (LastCommand(), "Show last commit details", {
                "subaction": (str, "Sub-actions for last command", ["complete"]),
                "--safespace": ("store_true", "Create safespace for current changes")
            }),
            "shove": (ShoveCommand(), "Force push changes", {
                "--force": ("store_true", "Force push without security checks"),
                "--no-verify": ("store_true", "Skip pre-push verification"),
                "--branch": (str, "Target branch (default: main)")
            }),
            "author": (AuthorCommand(), "Display information about the author", {}),
            "cancel": (None, "Remove files from Git history", {
                "--patterns": (str, "File patterns to remove"),
                "--from": (str, "Starting commit to remove files from"),
                "--verify": ("store_true", "Verify operation before proceeding"),
                "--force": ("store_true", "Skip safety checks")
            }),
            "snapshot": (None, "Create temporary snapshot", {
                "-m": (str, "Snapshot message"),
                "--no-tag": ("store_true", "Skip creating a tag"),
                "--push": ("store_true", "Push snapshot to remote"),
                "--stash": ("store_true", "Create as stash instead of commit"),
                "--branch": (str, "Create snapshot on new branch"),
                "--expire": (int, "Auto-expire snapshot after N days"),
                "--include-untracked": ("store_true", "Include untracked files"),
                "--list": ("store_true", "List available snapshots"),
                "--cleanup": (int, "Clean up snapshots older than N days")
            }),
            "undo": (None, "Safely undo recent operations", {
                "steps": (int, "Number of operations to undo", None, 1),
                "--force": ("store_true", "Skip safety checks"),
                "--dry-run": ("store_true", "Show what would be undone"),
                "--no-backup": ("store_true", "Skip creating backup branch"),
                "--interactive": ("store_true", "Choose operations interactively"),
                "--keep-changes": ("store_true", "Preserve working directory changes"),
                "--remote-safe": ("store_true", "Prevent affecting remote branches")
            }),
            "ancestry": (None, "Show 3D repository visualization", {
                "--focus": (str, "Focus on specific directory or file"),
                "--depth": (int, "Maximum depth to visualize"),
                "--exclude": (str, "Patterns to exclude from visualization")
            }),
            "gui": (None, "Launch GUI interface", {}),
            "help": (None, "Show detailed help", {}),
            # Adding missing commands from qgit_config.py
            "commit": (None, "Stage and commit changes", {
                "-m": (str, "Commit message"),
                "--amend": ("store_true", "Amend the last commit"),
                "--no-verify": ("store_true", "Skip pre-commit hooks")
            }),
            "sync": (None, "Pull and push changes", {
                "--remote": (str, "Remote to sync with (default: origin)"),
                "--branch": (str, "Branch to sync (default: current)"),
                "--no-push": ("store_true", "Only pull, don't push"),
                "--no-pull": ("store_true", "Only push, don't pull")
            }),
            "save": (None, "Commit and sync in one step", {
                "-m": (str, "Commit message"),
                "--no-push": ("store_true", "Only commit, don't push"),
                "--amend": ("store_true", "Amend the last commit")
            }),
            "all": (None, "Stage, commit, and push", {
                "-m": (str, "Commit message", None),
                "--no-push": ("store_true", "Only commit, don't push"),
                "--amend": ("store_true", "Amend the last commit"),
                "--force": ("store_true", "Force push if needed")
            }),
            "first": (None, "Initialize new repository", {
                "--remote": (str, "GitHub repository URL"),
                "--private": ("store_true", "Create as private repository"),
                "--template": (str, "Repository template to use"),
                "--description": (str, "Repository description")
            }),
            "reverse": (None, "Untrack files", {
                "--patterns": (str, "File patterns to untrack"),
                "--keep": ("store_true", "Keep files in working directory"),
                "--force": ("store_true", "Skip confirmation prompts")
            }),
            "expel": (None, "Untrack all files", {
                "--keep": ("store_true", "Keep files in working directory"),
                "--force": ("store_true", "Skip confirmation prompts"),
                "--exclude": (str, "Patterns to exclude from untracking")
            }),
            "leaderboard": (LeaderboardCommand(), "Show interactive leaderboard of contributors", {}),
        }

        # Register all commands
        for cmd_name, (cmd_instance, cmd_help, cmd_args) in commands.items():
            cmd_parser = subparsers.add_parser(cmd_name, help=cmd_help)
            
            # Add command-specific arguments
            for arg_name, arg_spec in cmd_args.items():
                if len(arg_spec) == 2:  # Simple argument
                    arg_type, arg_help = arg_spec
                    if arg_type == "store_true":
                        cmd_parser.add_argument(f"--{arg_name.lstrip('-')}", action="store_true", help=arg_help)
                    else:
                        cmd_parser.add_argument(f"--{arg_name.lstrip('-')}", type=arg_type, help=arg_help)
                elif len(arg_spec) == 3:  # Argument with choices
                    arg_type, arg_help, choices = arg_spec
                    cmd_parser.add_argument(arg_name, type=arg_type, help=arg_help, choices=choices, nargs="?")
                elif len(arg_spec) == 4:  # Positional argument with default
                    arg_type, arg_help, _, default = arg_spec
                    cmd_parser.add_argument(arg_name, type=arg_type, help=arg_help, nargs="?", default=default)

        # Parse arguments
        args = parser.parse_args()

        # If no command specified, launch GUI
        if not args.command:
            run_gui()
            return 0

        # Verify Git setup before proceeding
        if not ensure_git_setup():
            return 1

        try:
            # Log command execution
            logger.log(
                level="info",
                command=args.command,
                message=f"Executing command: {args.command}",
                metadata=vars(args)
            )

            # Execute special commands
            if args.command == "snapshot":
                if getattr(args, "list", False):
                    list_snapshots()
                    return 0
                elif getattr(args, "cleanup", None):
                    cleanup_snapshots(args.cleanup)
                    return 0
                return 0 if create_snapshot(
                    message=getattr(args, "m", None),
                    no_tag=getattr(args, "no_tag", False),
                    push=getattr(args, "push", False),
                    stash=getattr(args, "stash", False),
                    branch=getattr(args, "branch", None),
                    expire_days=getattr(args, "expire", None),
                    include_untracked=getattr(args, "include_untracked", False)
                ) else 1
            elif args.command == "undo":
                return 0 if undo_operation(
                    steps=args.steps,
                    force=args.force,
                    dry_run=args.dry_run,
                    no_backup=args.no_backup,
                    interactive=args.interactive,
                    keep_changes=args.keep_changes,
                    remote_safe=args.remote_safe
                ) else 1
            elif args.command == "cancel":
                return 0 if cancel_files(
                    patterns=args.patterns.split(",") if args.patterns else None,
                    from_commit=getattr(args, "from", None),
                    verify=getattr(args, "verify", True)
                ) else 1
            elif args.command == "ancestry":
                visualize_repo(
                    focus=args.focus if hasattr(args, "focus") else None,
                    depth=args.depth if hasattr(args, "depth") else None,
                    exclude=args.exclude.split(",") if hasattr(args, "exclude") and args.exclude else None
                )
                return 0
            elif args.command == "gui":
                run_gui()
                return 0
            elif args.command == "help":
                show_help()
                return 0
            # Handle new commands
            elif args.command in ["commit", "sync", "save", "all", "first", "reverse", "expel"]:
                from .qgit_core import handle_core_command
                return 0 if handle_core_command(args.command, args) else 1

            # Execute standard commands
            command = commands.get(args.command)[0]
            if not command:
                print(f"Unknown command: {args.command}")
                return 1

            success = command.execute(args)
            
            # Log command completion
            logger.log(
                level="info",
                command=args.command,
                message=f"Command completed: {args.command}",
                status="success" if success else "failure"
            )
            
            return 0 if success else 1

        except GitCommandError as e:
            logger.log(
                level="error",
                command=args.command,
                message=str(e),
                metadata={"error_type": "git_command"}
            )
            print(format_error(e))
            return 1
        except GitConfigError as e:
            logger.log(
                level="error",
                command=args.command,
                message=str(e),
                metadata={"error_type": "git_config"}
            )
            print(format_error(e))
            return 1
        except GitRepositoryError as e:
            logger.log(
                level="error",
                command=args.command,
                message=str(e),
                metadata={"error_type": "git_repository"}
            )
            print(format_error(e))
            return 1
        except GitStateError as e:
            logger.log(
                level="error",
                command=args.command,
                message=str(e),
                metadata={"error_type": "git_state"}
            )
            print(format_error(e))
            return 1
        except GitNetworkError as e:
            logger.log(
                level="error",
                command=args.command,
                message=str(e),
                metadata={"error_type": "git_network"}
            )
            print(format_error(e))
            return 1
        except FileOperationError as e:
            logger.log(
                level="error",
                command=args.command,
                message=str(e),
                metadata={"error_type": "file_operation"}
            )
            print(format_error(e))
            return 1
        except KeyboardInterrupt:
            logger.log(
                level="info",
                command=args.command,
                message="Operation cancelled by user",
                status="cancelled"
            )
            print("\nOperation cancelled by user")
            return 1
        except Exception as e:
            logger.log(
                level="error",
                command=args.command,
                message=str(e),
                metadata={"error_type": "unexpected"}
            )
            print(f"Error executing command: {e}")
            return 1

    except Exception as e:
        logger.log(
            level="error",
            command="main",
            message=str(e),
            metadata={"error_type": "startup"}
        )
        print(f"Error during startup: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 