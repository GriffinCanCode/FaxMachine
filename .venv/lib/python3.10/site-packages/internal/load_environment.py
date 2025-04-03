import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

# Registry of available environment variables with their descriptions and validation rules
ENV_REGISTRY = {
    "SUDO_PASSWORD": {
        "required": True,
        "description": "Password for sudo operations",
        "default": "",
    },
    "USER_PASSWORD": {
        "required": False,
        "description": "User account password",
        "default": "",
    },
    "NETWORK_RANGE": {
        "required": False,
        "description": "Local network range for scanning",
        "default": "192.168.1.0/24",
    },
    "REMOTE_USERNAME": {
        "required": False,
        "description": "Default username for remote connections",
        "default": "",
    },
    "SCAN_PORTS": {
        "required": False,
        "description": "Enable port scanning functionality",
        "default": "false",
    },
    "SCAN_TIMEOUT": {
        "required": False,
        "description": "Maximum time in seconds for network scan",
        "default": "30",
    },
    "PARALLEL_SCANS": {
        "required": False,
        "description": "Number of parallel network scans",
        "default": "100",
    },
    "KEEP_APPS": {
        "required": True,
        "description": "Comma-separated list of applications to keep running",
        "default": "Google Chrome,Cursor,Terminal" if platform.system() != "Windows" else "Google Chrome,Cursor,cmd.exe",
    },
    "DEBUG": {
        "required": False,
        "description": "Enable debug mode",
        "default": "false",
    },
    "LOG_LEVEL": {
        "required": False,
        "description": "Logging level configuration",
        "default": "INFO",
    },
    "ANTHROPIC_API_KEY": {
        "required": False,
        "description": "API key for Anthropic services",
        "default": "",
    },
    "GITHUB_TOKEN": {
        "required": False,
        "description": "GitHub personal access token",
        "default": "",
    },
}


def create_default_env_file(env_path: Path) -> None:
    """Create a default .env file with documented variables."""
    env_path.parent.mkdir(parents=True, exist_ok=True)
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("# Environment Configuration\n\n")
        for var_name, config in ENV_REGISTRY.items():
            f.write(f"# {config['description']}\n")
            if config["required"]:
                f.write("# Required: Yes\n")
            f.write(f"{var_name}={config['default']}\n\n")


def validate_environment(env_path: Path) -> List[str]:
    """Validate environment variables against registry."""
    missing_vars = []
    for var_name, config in ENV_REGISTRY.items():
        if config["required"] and not os.getenv(var_name):
            missing_vars.append(var_name)
    return missing_vars


def load_environment():
    """Load environment variables from .env file"""
    try:
        from dotenv.main import load_dotenv
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "python-dotenv==1.0.1"]
        )
        from dotenv.main import load_dotenv

    # Get the real path of the script, following symlinks
    script_path = Path(__file__).resolve()
    script_dir = script_path.parent.parent  # Go up one level to main directory

    # Look for .env in the internal directory
    env_path = script_dir / "internal" / ".env"

    if not env_path.exists():
        # If not found, create .env with documented default values
        create_default_env_file(env_path)
        print(f"Created new .env file at {env_path}")
        print("Please add your configuration to the .env file and run again")
        sys.exit(1)

    # Load the .env file
    load_dotenv(env_path)

    # Validate required environment variables
    missing_vars = validate_environment(env_path)

    if missing_vars:
        print("Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"- {var} ({ENV_REGISTRY[var]['description']})")
        print(f"\nPlease add them to: {env_path}")
        sys.exit(1)


def get_env_registry() -> Dict:
    """Return the environment variable registry."""
    return ENV_REGISTRY
