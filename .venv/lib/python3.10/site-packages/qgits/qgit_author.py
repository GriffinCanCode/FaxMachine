#!/usr/bin/env python3
"""QGit author command implementation for displaying information about the author.

This module provides a fun and entertaining UI that displays information about
the author, Griffin, 'A programming God...'
"""

from typing import Any
import os
import sys

from qgits.qgit_commands import QGitCommand
from qgits.qgit_errors import format_error
from qgits.qgit_logger import logger
from qgits.qgit_author_data import get_random_facts, get_random_quote, get_random_advice

# Smaller ASCII art for Griffin logo (to fit smaller terminals)
GRIFFIN_LOGO = r"""
  _____       _  __  __ _       
 / ____|     (_)/ _|/ _(_)      
| |  __ _ __ _| |_| |_ _ _ __   
| | |_ | '__| |  _|  _| | '_ \  
| |__| | |  | | | | | | | | | | 
 \_____|_|  |_|_| |_| |_|_| |_| 
 The Programming God
"""

# Smaller ASCII art for "GOD MODE" text
GOD_MODE_TEXT = r"""
  ____  ____  ____    __  __  ____  ____  ____ 
 / ___||  _ \|  _ \  |  \/  ||  _ \|  _ \| ___|
| |  _ | |_) | | | | | |\/| || | | | | | |___ \
| |_| ||  _ <| |_| | | |  | || |_| | |_| |___) |
 \____||_| \_\____/  |_|  |_||____/|____/|____/ 
"""

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

class AuthorCommand(QGitCommand):
    """Command to display information about the author."""
    
    def execute(self, args: Any) -> bool:
        """Execute the author command."""
        try:
            # Log the command execution
            logger.log(
                level="info",
                command="author",
                message="Displaying author information",
                metadata={}
            )
            
            # Try to import and use the GUI module
            try:
                from qgits.qgit_gui import show_author_screen
                show_author_screen()
            except ImportError as e:
                logger.log(
                    level="warning",
                    command="author",
                    message=f"GUI module not available: {str(e)}",
                    metadata={"error_type": "ImportError"}
                )
                fallback_display()
            except Exception as e:
                logger.log(
                    level="error",
                    command="author",
                    message=f"GUI display failed: {str(e)}",
                    metadata={"error_type": type(e).__name__}
                )
                # If GUI fails, use fallback display
                fallback_display()
                
            return True
            
        except Exception as e:
            self.handle_error(e)
            # Ensure we still show something even if there's an error
            try:
                fallback_display()
            except:
                print("Error displaying author information. Please try again.")
            return False

def show_author() -> None:
    """Show information about the author."""
    command = AuthorCommand()
    command.execute(None)

if __name__ == "__main__":
    show_author() 