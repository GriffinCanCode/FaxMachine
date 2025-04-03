"""Setup verification module for QGit."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Union, Tuple
import getpass

def install_dotenv() -> bool:
    """
    Attempt to install python-dotenv package.
    
    Returns:
        bool: True if installation was successful, False otherwise
    """
    try:
        print("Installing python-dotenv...")
        # First try to uninstall any existing version
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "python-dotenv", "dotenv"])
            print("✓ Removed existing dotenv packages")
        except subprocess.CalledProcessError:
            pass  # Ignore errors if packages aren't installed
        
        # Install the correct version
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "python-dotenv==1.0.1"])
        print("✓ python-dotenv installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Failed to install python-dotenv: {str(e)}")
        return False

def verify_dotenv_installation() -> bool:
    """
    Verify that python-dotenv is properly installed and accessible.
    
    Returns:
        bool: True if dotenv is properly installed and accessible, False otherwise
    """
    try:
        # Try importing dotenv
        import dotenv
        # Check if we can actually use the package
        test_env = dotenv.Dotenv()
        if not hasattr(dotenv, 'load_dotenv'):
            print("⚠️ Installed dotenv package is missing required functions")
            return False
        print(f"✓ python-dotenv version {dotenv.__version__} is installed and functional")
        return True
    except ImportError as e:
        print(f"⚠️ Error importing python-dotenv: {str(e)}")
        print(f"Python path: {sys.path}")
        return False
    except Exception as e:
        print(f"⚠️ Error verifying dotenv functionality: {str(e)}")
        return False

# Try to import dotenv, but don't fail if it's not available
try:
    from dotenv import load_dotenv, find_dotenv, set_key
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    load_dotenv = find_dotenv = set_key = None
    # Attempt to install dotenv if it's not available
    if install_dotenv():
        # Verify the installation
        if verify_dotenv_installation():
            try:
                from dotenv import load_dotenv, find_dotenv, set_key
                DOTENV_AVAILABLE = True
                print("✓ Successfully imported python-dotenv after installation")
            except ImportError as e:
                print(f"⚠️ Failed to import python-dotenv after installation: {str(e)}")
                DOTENV_AVAILABLE = False
        else:
            print("⚠️ python-dotenv installation verification failed")
            DOTENV_AVAILABLE = False

def get_env_path() -> Path:
    """Get the path to the .env file."""
    return Path(__file__).parent.parent / "internal" / ".env"

def configure_git_login() -> Tuple[bool, str]:
    """
    Configure Git login credentials interactively.
    
    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        print("\nGit Login Configuration:")
        print("----------------------")
        
        # Get GitHub token
        github_token = getpass.getpass("Enter your GitHub Personal Access Token (or press Enter to skip): ")
        if github_token and DOTENV_AVAILABLE:
            env_path = get_env_path()
            set_key(env_path, "GITHUB_TOKEN", github_token)
            print("✓ GitHub token configured")
        elif github_token and not DOTENV_AVAILABLE:
            print("⚠️ python-dotenv not installed. GitHub token will not be saved.")
        
        # Get Git user info
        user_name = input("Enter your Git username (or press Enter to skip): ").strip()
        user_email = input("Enter your Git email (or press Enter to skip): ").strip()
        
        if user_name and user_email:
            subprocess.check_call(["git", "config", "--global", "user.name", user_name])
            subprocess.check_call(["git", "config", "--global", "user.email", user_email])
            print("✓ Git user information configured")
        
        return True, "Git login configuration completed"
    except Exception as e:
        return False, f"Error configuring Git login: {str(e)}"

def configure_sudo_password() -> Tuple[bool, str]:
    """
    Configure sudo password interactively.
    
    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        print("\nSudo Password Configuration:")
        print("-------------------------")
        sudo_password = getpass.getpass("Enter your sudo password (or press Enter to skip): ")
        
        if sudo_password and DOTENV_AVAILABLE:
            env_path = get_env_path()
            set_key(env_path, "SUDO_PASSWORD", sudo_password)
            print("✓ Sudo password configured")
        elif sudo_password and not DOTENV_AVAILABLE:
            print("⚠️ python-dotenv not installed. Sudo password will not be saved.")
        
        return True, "Sudo password configuration completed"
    except Exception as e:
        return False, f"Error configuring sudo password: {str(e)}"

def verify_git_setup() -> Tuple[bool, str]:
    """
    Verify Git setup by checking for configured user and commit hash.
    
    Returns:
        Tuple[bool, str]: (is_valid, message)
    """
    try:
        # Load environment variables if dotenv is available
        env_path = get_env_path()
        if env_path.exists() and DOTENV_AVAILABLE:
            load_dotenv(env_path)
        elif env_path.exists() and not DOTENV_AVAILABLE:
            print("⚠️ python-dotenv not installed. Environment variables will not be loaded.")

        # Check for Git user configuration
        user_name = subprocess.check_output(
            ["git", "config", "--get", "user.name"],
            stderr=subprocess.PIPE,
            universal_newlines=True
        ).strip()
        
        user_email = subprocess.check_output(
            ["git", "config", "--get", "user.email"],
            stderr=subprocess.PIPE,
            universal_newlines=True
        ).strip()
        
        if not user_name or not user_email:
            return False, "Git user configuration is missing. Please set up your Git account with:\n" \
                        "git config --global user.name 'Your Name'\n" \
                        "git config --global user.email 'your.email@example.com'"
        
        # Check for Git commit hash
        try:
            commit_hash = subprocess.check_output(
                ["git", "rev-parse", "--git-dir"],
                stderr=subprocess.PIPE,
                universal_newlines=True
            ).strip()
            
            if not commit_hash:
                return False, "Git repository not initialized. Please run 'git init' in your project directory."
                
        except subprocess.CalledProcessError:
            return False, "Git repository not initialized. Please run 'git init' in your project directory."
        
        return True, f"Git setup verified successfully for user: {user_name} <{user_email}>"
        
    except subprocess.CalledProcessError as e:
        return False, f"Error verifying Git setup: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error during Git setup verification: {str(e)}"

def ensure_git_setup() -> bool:
    """
    Ensure Git setup is valid before proceeding with QGit operations.
    
    Returns:
        bool: True if setup is valid, False otherwise
    """
    is_valid, message = verify_git_setup()
    if not is_valid:
        print(f"Git setup verification failed: {message}")
        return False
    return True 