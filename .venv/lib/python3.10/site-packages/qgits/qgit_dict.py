from typing import Any, Dict

# Dictionary containing help information and configuration for all qgit commands
# Each command has a description, usage pattern, and available options
QGIT_COMMANDS: Dict[str, Dict[str, Any]] = {
    "makegpg": {
        "description": "Configure GPG signing for Git commits",
        "usage": "qgit makegpg",
        "options": {},
    },
    "commit": {
        "description": "Stage and commit all modified files",
        "usage": "qgit commit [-m MESSAGE]",
        "options": {"-m, --message": "Specify a custom commit message"},
    },
    "sync": {
        "description": "Pull and push changes from/to the current branch",
        "usage": "qgit sync",
        "options": {},
    },
    "save": {
        "description": "Commit all changes and sync with remote in one step",
        "usage": "qgit save [-m MESSAGE]",
        "options": {"-m, --message": "Specify a custom commit message"},
    },
    "all": {
        "description": "Stage, commit, and optionally push all changes",
        "usage": "qgit all [-m MESSAGE] [-p]",
        "options": {
            "-m, --message": "Specify a custom commit message",
            "-p, --push": "Push changes after committing",
        },
    },
    "first": {
        "description": "Initialize a new git repository and set up GitHub remote",
        "usage": "qgit first",
        "options": {},
    },
    "reverse": {
        "description": "Untrack specified files from git while preserving them locally",
        "usage": "qgit reverse [--patterns PATTERN...]",
        "options": {"--patterns": "Specify custom file patterns to untrack"},
    },
    "benedict": {
        "description": "Scan codebase for potentially risky files and update .gitignore",
        "usage": "qgit benedict [--arnold]",
        "options": {
            "--arnold": "Automatically update .gitignore and reverse tracked files"
        },
    },
    "expel": {
        "description": "Untrack all currently tracked files while preserving them locally",
        "usage": "qgit expel",
        "options": {},
    },
    "undo": {
        "description": "Safely undo recent git operations",
        "usage": "qgit undo [n] [options]",
        "options": {
            "n": "Number of operations to undo (default: 1)",
            "--force, -f": "Skip safety checks and confirmations",
            "--dry-run, -d": "Show what would be undone without making changes",
            "--no-backup": "Skip creating backup branch",
            "--interactive, -i": "Choose which operations to undo interactively",
            "--keep-changes": "Preserve working directory changes during undo",
            "--remote-safe": "Fail if undo would affect remote branches",
        },
    },
    "snapshot": {
        "description": "Create a temporary commit of current changes",
        "usage": "qgit snapshot [options]",
        "options": {
            "-m, --message": "Optional snapshot description",
            "--no-tag": "Skip creating a reference tag",
            "--push": "Push snapshot to remote (useful for backups)",
            "--stash": "Create as stash instead of commit",
            "--branch NAME": "Create snapshot on new branch",
            "--expire DAYS": "Auto-expire snapshot after N days",
            "--include-untracked": "Include untracked files in snapshot",
        },
    },
    "stats": {
        "description": "Advanced repository analytics and team insights with interactive visualizations",
        "usage": "qgit stats [options]",
        "options": {
            "--author": "Filter stats for specific author",
            "--from": "Start date for analysis (YYYY-MM-DD)",
            "--to": "End date for analysis (YYYY-MM-DD)",
            "--format": "Output format (text/json)",
            "--team": "Show team collaboration insights",
            "--files": "Show file-level statistics",
            "--leaderboard": "Show interactive leaderboard of contributors",
            "--visualize": "Generate interactive visualizations",
            "--export": "Export stats to specified format (csv/json)",
            "--period": "Time period for analysis (day/week/month/year/all)"
        },
    },
    "doctor": {
        "description": "Perform a comprehensive health check of the Git repository",
        "usage": "qgit doctor",
        "options": {
            "--fix": "Attempt to automatically fix identified issues",
            "--verbose": "Show detailed diagnostic information",
            "--check-remote": "Include remote repository checks",
            "--check-lfs": "Include Git LFS configuration checks",
            "--check-hooks": "Include Git hooks validation",
        },
    },
    "author": {
        "description": "Display information about the author with an entertaining UI",
        "usage": "qgit author",
        "options": {},
    },
    "cancel": {
        "description": "Safely remove files from Git history while preserving local copies",
        "usage": "qgit cancel [--patterns PATTERN...] [--from COMMIT] [--verify]",
        "options": {
            "--patterns": 'File patterns to remove from history (e.g. "*.log", "target/")',
            "--from": "Starting commit to remove files from (default: beginning of history)",
            "--verify": "Verify operation will not affect local files before proceeding",
        },
    },
    "ancestry": {
        "description": "3D visualization of Git repository structure and history",
        "usage": "qgit tv [--focus PATH]",
        "options": {"--focus": "Focus visualization on specific directory or file"},
    },
    "last": {
        "description": "Checkout a previous commit with safespace integration",
        "usage": "qgit last [complete]",
        "options": {
            "complete": "Clean up the safespace after finishing with the old version"
        },
    },
    "shove": {
        "description": "Safely push to origin main after security checks",
        "usage": "qgit shove",
        "options": {},
    },
    "leaderboard": {
        "description": "Interactive leaderboard showing contributor statistics and achievements",
        "usage": "qgit leaderboard [options]",
        "options": {
            "--period": "Time period for leaderboard (day/week/month/year/all)",
            "--sort": "Sort by metric (commits/lines/impact)",
            "--limit": "Number of contributors to display",
            "--export": "Export leaderboard data (csv/json)",
            "--visualize": "Show interactive visualizations",
            "--achievements": "Show contributor achievements and badges"
        },
    },
}


def get_command_help(command: str) -> Dict[str, Any]:
    """Get help information for a specific command.

    Args:
        command: Name of the command to get help for

    Returns:
        Dictionary containing description, usage and options for the command.
        Returns empty dict if command not found.
    """
    return QGIT_COMMANDS.get(command, {})


def get_all_commands() -> Dict[str, Dict[str, Any]]:
    """Get all command definitions.

    Returns:
        Dictionary containing help information for all available commands.
        Each command entry includes description, usage pattern and options.
    """
    return QGIT_COMMANDS
