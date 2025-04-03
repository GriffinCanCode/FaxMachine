#!/usr/bin/env python3
"""QGit shove command implementation for safely pushing to origin main."""

from typing import Tuple, Dict, Any, List
from datetime import datetime

from qgits.qgit_core import run_command
from qgits.qgit_errors import GitCommandError, GitStateError
from qgits.qgit_logger import logger
from qgits.qgit_benedict import (
    scan_repository,
    update_gitignore,
    check_tracked_files,
    _format_header,
    _format_warning,
    _format_success,
    _format_error,
    COLORS,
)

def verify_branch() -> bool:
    """Verify we're on main branch and up to date.
    
    Returns:
        True if branch is valid for push
        
    Raises:
        GitStateError: If branch verification fails
    """
    try:
        # Check current branch
        current = run_command("git rev-parse --abbrev-ref HEAD").strip()
        if current != "main":
            raise GitStateError(
                f"Not on main branch. Currently on: {current}\n"
                "Please switch to main branch first with: git checkout main"
            )
        
        # Fetch to ensure we have latest
        run_command("git fetch origin main")
        
        # Check if we're behind
        behind = run_command("git rev-list HEAD..origin/main --count").strip()
        if int(behind) > 0:
            raise GitStateError(
                "Local main is behind origin/main.\n"
                "Please pull latest changes first with: git pull origin main"
            )
        
        return True
        
    except GitCommandError as e:
        raise GitStateError(f"Branch verification failed: {str(e)}")

def check_security() -> Tuple[bool, Dict[str, List[Dict[str, Any]]]]:
    """Run security checks for risky files.
    
    Returns:
        Tuple of (is_safe, scan_results)
        
    Raises:
        GitStateError: If security check fails
    """
    print(_format_header("🔒 Security Check"))
    print("Running security scan before push...")
    
    try:
        # Run repository scan
        scan_results, total_files = scan_repository()
        
        # Check if any risky files were found
        has_risky_files = any(files for files in scan_results.values())
        
        if not has_risky_files:
            print(_format_success("\nNo risky files detected! Ready to push."))
            return True, scan_results
            
        print(_format_warning("\nRisky files detected in repository."))
        return False, scan_results
        
    except Exception as e:
        raise GitStateError(f"Security check failed: {str(e)}")

def handle_risky_files(scan_results: Dict[str, List[Dict[str, Any]]]) -> bool:
    """Handle detected risky files by prompting for action.
    
    Args:
        scan_results: Results from security scan
        
    Returns:
        True if files were handled successfully
        
    Raises:
        GitStateError: If file handling fails
    """
    print("\nWould you like to:")
    print(f"{COLORS['CYAN']}1. Update .gitignore and untrack risky files{COLORS['ENDC']}")
    print(f"{COLORS['CYAN']}2. Cancel push{COLORS['ENDC']}")
    
    choice = input("\nEnter choice (1/2): ").strip()
    
    if choice != "1":
        print("\nPush cancelled.")
        return False
        
    try:
        # Update .gitignore and untrack files
        print("\nUpdating .gitignore and untracking risky files...")
        if not update_gitignore(scan_results, auto_commit=True):
            raise GitStateError("Failed to update .gitignore")
            
        # Verify no risky files remain tracked
        remaining = check_tracked_files()
        if remaining:
            raise GitStateError(
                "Some risky files are still tracked. Please remove them manually or use 'qgit benedict --arnold'"
            )
            
        print(_format_success("\nRepository secured successfully!"))
        return True
        
    except Exception as e:
        raise GitStateError(f"Failed to handle risky files: {str(e)}")

def push_to_main() -> bool:
    """Push current branch to origin main.
    
    Returns:
        True if push successful
        
    Raises:
        GitStateError: If push fails
    """
    try:
        print(_format_header("\n🚀 Pushing to origin/main"))
        run_command("git push origin main")
        print(_format_success("\nSuccessfully pushed to origin/main!"))
        
        logger.log(
            level="info",
            command="shove",
            message="Successfully pushed to origin/main",
            metadata={
                "timestamp": datetime.now().isoformat(),
                "branch": "main"
            }
        )
        
        return True
        
    except GitCommandError as e:
        raise GitStateError(f"Push failed: {str(e)}")

def execute_shove() -> bool:
    """Execute the shove command workflow.
    
    Returns:
        True if operation was successful
    """
    try:
        # Step 1: Verify branch status
        if not verify_branch():
            return False
            
        # Step 2: Run security checks
        is_safe, scan_results = check_security()
        
        # Step 3: Handle any risky files if found
        if not is_safe:
            if not handle_risky_files(scan_results):
                return False
                
        # Step 4: Push to origin main
        return push_to_main()
        
    except GitStateError as e:
        print(_format_error(f"\nError: {str(e)}"))
        return False
    except Exception as e:
        logger.log(
            level="error",
            command="shove",
            message="Unexpected error during shove",
            metadata={
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )
        print(_format_error(f"\nUnexpected error: {str(e)}"))
        return False 