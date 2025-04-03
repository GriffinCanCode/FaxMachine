#!/usr/bin/env python3
"""QGit command implementations for various Git operations.

This module contains the command classes that implement different Git operations
like scanning for sensitive files, generating repository statistics, and performing
health checks. Each command inherits from the base QGitCommand class.
"""

import argparse
from abc import ABC, abstractmethod
import os
from typing import Dict, Optional, Any
from pathlib import Path

from qgits.qgit_core import is_git_repo, run_command
from qgits.qgit_errors import (
    GitCommandError,
    GitNetworkError,
    GitRepositoryError,
    GitStateError,
    format_error,
)
from qgits.qgit_logger import logger
from qgits.qgit_author_data import get_random_facts, get_random_quote, get_random_advice
from qgits.qgit_stats import get_commit_stats, get_churn_stats, get_team_stats, get_leaderboard_stats

def fallback_display():
    """Display author information in plain text mode if GUI fails."""
    print("\n" + "=" * 40)
    print("  GRIFFIN: THE PROGRAMMING GOD")
    print("=" * 40)
    
    try:
        print("\nFun Facts:")
        for i, fact in enumerate(get_random_facts(3), 1):
            print(f"{i}. {fact}")
        
        print("\nWords of Wisdom:")
        print(f'"{get_random_quote()}"')
        
        print("\nDaily Advice:")
        print(get_random_advice())
    except Exception as e:
        logger.log(
            level="error",
            command="author",
            message=f"Error in fallback display: {str(e)}",
            metadata={"error_type": type(e).__name__}
        )
        print("\nCouldn't load author data, but Griffin is still a programming god.")
    
    print("\n" + "=" * 40 + "\n")


class QGitCommand(ABC):
    """Base class for all qgit commands.

    Provides common functionality like status/error message handling and command execution.
    All concrete command classes should inherit from this.
    """

    def __init__(self):
        """Initialize command with name derived from class name and empty message lists."""
        self.name = self.__class__.__name__.lower().replace("command", "")
        self.description = self.__doc__ or "No description available"
        self.status_messages = []
        self.error_messages = []

    def add_status(self, message: str) -> None:
        """Add a status message to be displayed to the user.

        Args:
            message: Status message to add
        """
        self.status_messages.append(message)

    def add_error(self, message: str) -> None:
        """Add an error message to be displayed to the user.

        Args:
            message: Error message to add
        """
        self.error_messages.append(message)

    def handle_error(self, error: Exception) -> None:
        """Handle an error by formatting and storing it appropriately.

        Args:
            error: The exception to handle
        """
        formatted_error = format_error(error)
        self.add_error(formatted_error)

        # Re-raise certain critical errors
        if isinstance(error, (GitRepositoryError, GitStateError)):
            raise error

    def run_command(self, command: str) -> str:
        """Execute a shell command safely and return its output.

        Args:
            command: Shell command to execute

        Returns:
            Command output as string

        Raises:
            GitCommandError: If the command fails
            GitNetworkError: If there are network issues
            GitStateError: If the repository is in an invalid state
        """
        try:
            result = run_command(command)
            return result
        except (GitCommandError, GitNetworkError, GitStateError) as e:
            self.handle_error(e)
            raise
        except Exception as e:
            self.handle_error(e)
            raise GitCommandError(command, str(e))

    def verify_repository(self) -> None:
        """Verify that we're in a Git repository.

        Raises:
            GitRepositoryError: If not in a Git repository
        """
        if not is_git_repo():
            raise GitRepositoryError(
                "Not a Git repository. Please run 'qgit first' to initialize one or 'git init' manually.",
                command=None,
                error_output=None,
            )

    @abstractmethod
    def execute(self, args: argparse.Namespace) -> bool:
        """Execute the command with given arguments.

        Args:
            args: Parsed command line arguments

        Returns:
            True if command executed successfully, False otherwise

        Raises:
            QGitError: Base class for all QGit errors
        """
        pass


class BenedictCommand(QGitCommand):
    """Scan codebase for potentially risky files and update .gitignore.

    Analyzes the repository for sensitive files like credentials, keys, and logs.
    Can automatically update .gitignore and untrack sensitive files.
    """

    def execute(self, args: argparse.Namespace) -> bool:
        """Execute the benedict scan command.

        Scans codebase, displays results by category, and optionally updates .gitignore.
        Can also automatically untrack sensitive files if --arnold flag is used.

        Args:
            args: Command arguments including arnold flag

        Returns:
            True if scan completed successfully, False otherwise
        """
        try:
            from .qgit_benedict import (
                reverse_tracking,
                scan_repository,
                update_gitignore,
            )

            # Verify we're in a git repository
            self.verify_repository()

            # Delegate scanning to qgit_benedict
            results, total_files = scan_repository()

            # Handle .gitignore updates based on user choice
            should_update = (
                args.arnold
                or input(
                    "\n📝 Would you like to update .gitignore with recommended patterns? (y/N): "
                ).lower()
                == "y"
            )

            if should_update:
                success = update_gitignore(results, auto_commit=args.arnold)
                if not success:
                    return False

                # Handle automatic reverse operation with --arnold flag
                if args.arnold:
                    print(
                        "\n🔄 Initiating automatic reverse operation for tracked files..."
                    )
                    return reverse_tracking()
                else:
                    print(
                        "\n💡 Tip: Run 'qgit reverse' to untrack any already-tracked files matching these patterns"
                    )
                    print(
                        "   This will help ensure sensitive files are not tracked in git history"
                    )

            return True

        except Exception as e:
            self.handle_error(e)
            return False


class LeaderboardCommand(QGitCommand):
    """Display a leaderboard of repository contributors based on line changes.
    
    Shows who has made the most line-by-line changes in the repository,
    with detailed statistics per author and file.
    """
    
    def execute(self, args: argparse.Namespace) -> bool:
        """Execute the leaderboard command.
        
        Args:
            args: Command arguments (unused for this command)
            
        Returns:
            True if leaderboard displayed successfully, False otherwise
        """
        try:
            # Verify we're in a git repository first
            self.verify_repository()
            
            # Get leaderboard statistics with error handling
            try:
                stats = get_leaderboard_stats()
            except Exception as e:
                self.handle_error(e)
                stats = {"authors": []}  # Create empty stats on error
            
            # Handle None return or missing authors
            if not stats or not isinstance(stats, dict):
                stats = {"authors": []}
            if "authors" not in stats:
                stats["authors"] = []
            
            # Import and run the curses-based leaderboard
            import curses
            from .qgit_gui import LeaderboardPage
            
            def run_leaderboard(stdscr):
                return LeaderboardPage(stdscr, stats).run()
            
            # Run the GUI leaderboard using curses
            curses.wrapper(run_leaderboard)
            return True
            
        except Exception as e:
            self.handle_error(e)
            return False


class StatsCommand(QGitCommand):
    """Generate advanced repository analytics and team insights.

    Analyzes commit history, code churn, and team collaboration patterns.
    Can also generate "secret sauce" insights about repository health.
    """

    def execute(self, args: argparse.Namespace) -> bool:
        """Execute the stats generation command.

        Collects and displays commit stats, churn metrics, and team collaboration data.

        Args:
            args: Command arguments including author filter and team flag

        Returns:
            True if stats generated successfully, False otherwise
        """
        try:
            # Handle leaderboard mode
            if hasattr(args, 'leaderboard') and args.leaderboard:
                return LeaderboardCommand().execute(args)
                
            # Collect repository statistics using the new stats module
            commit_stats = get_commit_stats(
                author=args.author,
                start_date=args.from_date if hasattr(args, 'from_date') else None,
                end_date=args.to_date if hasattr(args, 'to_date') else None
            )
            churn_stats = get_churn_stats()
            team_stats = get_team_stats() if args.team else None

            # Display collected statistics
            self._display_stats(commit_stats, churn_stats, team_stats)
            return True

        except Exception as e:
            self.add_error(f"Error generating stats: {str(e)}")
            return False

    def _display_stats(self, commit_stats: Dict[str, Any], 
                      churn_stats: Dict[str, Any], 
                      team_stats: Optional[Dict[str, Any]] = None) -> None:
        """Display collected statistics in a formatted way.

        Args:
            commit_stats: Dictionary containing commit statistics
            churn_stats: Dictionary containing code churn statistics
            team_stats: Optional dictionary containing team statistics
        """
        # Display commit statistics
        print("\n📊 Commit Statistics")
        print("=" * 50)
        print(f"Total Commits: {commit_stats.get('total_commits', 0)}")
        print(f"Unique Authors: {commit_stats.get('unique_authors', 0)}")
        print(f"Daily Average: {commit_stats.get('daily_average', 0):.2f} commits")
        print(f"Weekly Average: {commit_stats.get('weekly_average', 0):.2f} commits")
        print(f"Monthly Average: {commit_stats.get('monthly_average', 0):.2f} commits")

        # Display churn statistics
        print("\n📈 Code Churn")
        print("=" * 50)
        print(f"Total Additions: {churn_stats.get('total_additions', 0)}")
        print(f"Total Deletions: {churn_stats.get('total_deletions', 0)}")
        print(f"Total Changes: {churn_stats.get('total_changes', 0)}")
        
        if churn_stats.get('most_changed_files'):
            print("\nMost Changed Files:")
            for file in churn_stats['most_changed_files']:
                print(f"• {file['file']}: +{file['additions']} -{file['deletions']}")

        # Display team statistics if available
        if team_stats:
            print("\n👥 Team Statistics")
            print("=" * 50)
            print(f"Total Contributors: {team_stats.get('total_authors', 0)}")
            
            if team_stats.get('authors'):
                print("\nContributor Details:")
                for author, stats in team_stats['authors'].items():
                    print(f"\n{author}:")
                    print(f"  • Commits: {stats['commits']}")
                    print(f"  • Active Days: {stats['active_days']}")
                    print(f"  • First Commit: {stats['first_commit']}")
                    print(f"  • Last Commit: {stats['last_commit']}")
                    print(f"  • Activity Span: {stats['commit_span_days']} days")

        print("\n" + "=" * 50)


class DoctorCommand(QGitCommand):
    """Perform a comprehensive health check of the Git repository.

    Runs multiple diagnostic checks to identify potential issues with:
    - Repository configuration
    - Remote connectivity
    - Large files
    - Branch status
    - Git hooks
    - .gitignore setup
    - LFS configuration
    - Submodules
    """

    def execute(self, args: argparse.Namespace) -> bool:
        """Execute the repository health check.

        Runs a series of diagnostic checks and displays results with recommendations.

        Args:
            args: Command arguments including verbose and fix flags

        Returns:
            True if health check completed, False if critical issues found
        """
        try:
            # Initialize doctor with command line options
            from .qgit_doctor import RepositoryDoctor

            doctor = RepositoryDoctor(
                verbose=args.verbose if hasattr(args, "verbose") else False,
                fix=args.fix if hasattr(args, "fix") else False,
            )

            # Run all checks
            all_passed = doctor.run_all_checks()

            # Apply fixes if requested
            if hasattr(args, "fix") and args.fix:
                fixes_applied, fixes_failed = doctor.apply_fixes()
                if fixes_applied > 0 or fixes_failed > 0:
                    print(
                        f"\n🔧 Applied {fixes_applied} fix(es), {fixes_failed} failed"
                    )
                    # Run checks again to verify fixes
                    all_passed = doctor.run_all_checks()

            # Print final report
            doctor.print_report()

            return all_passed

        except Exception as e:
            self.add_error(f"Error during health check: {str(e)}")
            return False


class LastCommand(QGitCommand):
    """Manage commit checkouts with safespace integration.
    
    Allows checking out previous commits while safely storing current changes.
    Can also clean up safespace when done with the old version.
    """
    
    def execute(self, args) -> bool:
        """Execute the last command.
        
        Args:
            args: Command line arguments
            
        Returns:
            True if successful, False otherwise
        """
        from .qgit_last import get_recent_commits, create_safespace, checkout_commit, complete_last
        
        try:
            # Handle complete subaction
            if args.subaction == 'complete':
                # Find all safespace directories
                safespaces = [d for d in os.listdir('.') if d.startswith('.safespace_')]
                if not safespaces:
                    print("No safespaces found to clean up")
                    return True
                
                success = True
                for safespace in safespaces:
                    try:
                        complete_last(safespace)
                        print(f"Successfully cleaned up safespace: {safespace}")
                    except Exception as e:
                        print(f"Failed to clean up safespace {safespace}: {str(e)}")
                        success = False
                return success
            
            # Normal last command execution
            commits = get_recent_commits()
            if not commits:
                print("No commits found")
                return False
            
            # Display commits
            print("\nRecent commits:")
            for i, (hash_val, date, message) in enumerate(commits, 1):
                print(f"{i}. [{date}] {message} ({hash_val[:8]})")
            
            # Get user input
            while True:
                choice = input("\nEnter commit number to checkout (or 'q' to quit): ")
                if choice.lower() == 'q':
                    return True
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(commits):
                        break
                    print("Invalid commit number. Please try again.")
                except ValueError:
                    print("Invalid input. Please enter a number or 'q' to quit.")
            
            # Get selected commit
            commit_hash = commits[index][0]
            
            # Ask about safespace
            save_changes = input("\nSave current changes to safespace? (Y/n): ").lower() != 'n'
            
            # Create safespace if requested
            safespace_dir = None
            if save_changes:
                safespace_dir = create_safespace(commit_hash)
                print(f"\nCreated safespace at: {safespace_dir}")
            
            # Checkout the commit
            checkout_commit(commit_hash, safespace_dir)
            
            print(f"\nSuccessfully checked out commit: {commits[index][2]} ({commit_hash[:8]})")
            if safespace_dir:
                print(f"Your changes are saved in: {safespace_dir}")
                print("Use 'qgit last complete' when you want to clean up the safespace")
            
            return True
            
        except Exception as e:
            print(f"Error executing last: {str(e)}")
            return False


class ShoveCommand(QGitCommand):
    """Safely push to origin main after security checks.
    
    Performs security scan for risky files and handles them before pushing.
    Integrates with benedict functionality for comprehensive security.
    """
    
    def execute(self, args: argparse.Namespace) -> bool:
        """Execute the shove command.
        
        Runs security checks and pushes to origin main if safe.
        
        Args:
            args: Command arguments (unused for this command)
            
        Returns:
            True if push completed successfully, False otherwise
        """
        try:
            from .qgit_shove import execute_shove
            
            # Verify we're in a git repository
            self.verify_repository()
            
            # Execute shove workflow
            return execute_shove()
            
        except Exception as e:
            self.handle_error(e)
            return False


class GPGCommand(QGitCommand):
    """Configure GPG signing for Git commits.
    
    Sets up GPG key generation, pinentry configuration, and Git signing settings.
    Ensures secure commit signing is properly configured.
    """
    
    def execute(self, args: argparse.Namespace) -> bool:
        """Execute the GPG setup command.
        
        Args:
            args: Command arguments (unused for this command)
            
        Returns:
            True if GPG setup completed successfully, False otherwise
        """
        try:
            from .scripts.gpg_setup import run_gpg_setup
            run_gpg_setup()
            return True
        except Exception as e:
            self.handle_error(e)
            return False