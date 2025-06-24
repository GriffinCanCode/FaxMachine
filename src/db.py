import os
import sys
import csv
from datetime import datetime
import importlib.util
import json
import shutil
import subprocess


# Constants
CONFIG_DIR = os.path.expanduser("~/.faxmachine")
DB_DIR = os.path.join(CONFIG_DIR, "db")
METADATA_DIR = os.path.join(CONFIG_DIR, "metadata")


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    BG_GREEN = "\033[42m"  # Green background
    BG_BLUE = "\033[44m"  # Blue background
    BG_YELLOW = "\033[43m"  # Yellow background
    BG_GREY = "\033[47m"  # Grey background
    BLACK = "\033[30m"  # Black text


def print_colored(text, color) -> None:
    """Print colored text"""
    print(f"{color}{text}{Colors.ENDC}")


def init_db():
    """Initialize the database directory structure"""
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(METADATA_DIR, exist_ok=True)

    # Create some default categories
    for category in ["git", "web", "python", "config", "other"]:
        os.makedirs(os.path.join(DB_DIR, category), exist_ok=True)

    # Add some example files if db is empty
    if not os.listdir(os.path.join(DB_DIR, "git")):
        example_gitignore = os.path.join(DB_DIR, "git", "python-gitignore")
        with open(example_gitignore, "w") as f:
            f.write(
                """# Python gitignore
__pycache__/
*.py[cod]
*$py.class
.env
venv/
ENV/
.vscode/
"""
            )

        # Add metadata for example file
        save_metadata(
            "git/python-gitignore",
            {
                "description": "Standard gitignore for Python projects",
                "added_date": datetime.now().isoformat(),
                "tags": ["python", "git", "ignore"],
            },
        )


def get_metadata_path(file_path):
    """Get the path to the metadata file for a given file"""
    rel_path = (
        os.path.relpath(file_path, DB_DIR) if os.path.isabs(file_path) else file_path
    )
    safe_path = rel_path.replace("/", "_").replace("\\", "_")
    return os.path.join(METADATA_DIR, f"{safe_path}.json")


def save_metadata(file_path, metadata):
    """Save metadata for a file"""
    os.makedirs(METADATA_DIR, exist_ok=True)
    metadata_path = get_metadata_path(file_path)

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)


def load_metadata(file_path):
    """Load metadata for a file"""
    metadata_path = get_metadata_path(file_path)

    if os.path.exists(metadata_path):
        try:
            with open(metadata_path) as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def list_items(path=None, indent=0):
    """List items in the database with tree-like structure"""
    if path is None:
        path = DB_DIR

    items = sorted(os.listdir(path))
    for i, item in enumerate(items):
        item_path = os.path.join(path, item)
        is_last = i == len(items) - 1

        if os.path.isdir(item_path):
            # Print directory
            prefix = (
                "   " * (indent - 1) + "└── "
                if is_last and indent > 0
                else "   " * (indent - 1) + "├── " if indent > 0 else ""
            )
            print_colored(f"{prefix}{item}/", Colors.BLUE + Colors.BOLD)
            list_items(item_path, indent + 1)
        else:
            # Print file
            prefix = (
                "   " * (indent - 1) + "└── "
                if is_last and indent > 0
                else "   " * (indent - 1) + "├── " if indent > 0 else ""
            )
            rel_path = os.path.relpath(item_path, DB_DIR)
            metadata = load_metadata(rel_path)
            description = metadata.get("description", "")
            description_text = f" - {description}" if description else ""
            print(f"{prefix}{item}{description_text}")


def add_file(
    source,
    category=None,
    name=None,
    subcategory=None,
    description=None,
    tags=None,
    preview_content=True,
):
    """Add a file to the database"""
    if not os.path.exists(source):
        print_colored(f"Error: Source file '{source}' not found", Colors.RED)
        return False

    # Handle relative paths
    source = os.path.abspath(source)

    # Generate smart preview and tag suggestions if requested
    auto_summary = None
    suggested_tags = []

    if preview_content:
        file_ext = os.path.splitext(source)[1].lower()
        if (
            file_ext in [".pdf", ".csv", ".json"] or os.path.getsize(source) < 1000000
        ):  # Skip large files
            try:
                import faxmachine

                summary, suggested_tags, preview, error = faxmachine.smart_preview_file(
                    source
                )

                if error:
                    print_colored(f"Warning: {error}", Colors.YELLOW)

                if not description and summary:
                    auto_summary = summary

                if summary:
                    print_colored("\nFile Analysis:", Colors.BOLD)
                    print(f"Summary: {summary}")

                    if suggested_tags:
                        print(f"Suggested tags: {', '.join(suggested_tags)}")

                    # Ask if user wants to see content preview
                    if preview:
                        preview_choice = input("Show content preview? [y/N] ")
                        if preview_choice.lower() == "y":
                            print_colored("\nContent Preview:", Colors.BOLD)
                            print(preview)
            except Exception as e:
                print_colored(
                    f"Warning: Preview generation failed: {e!s}", Colors.YELLOW
                )

    # If no name provided, use source filename
    if name is None:
        name = os.path.basename(source)

    # If no category provided, ask user
    if category is None:
        print_colored("Select Category", Colors.HEADER)
        categories = [
            d for d in os.listdir(DB_DIR) if os.path.isdir(os.path.join(DB_DIR, d))
        ]
        categories.append("+ Create new category")

        for i, cat in enumerate(categories):
            print(f"{i+1}. {cat}")

        choice = input("\nEnter category number: ")
        try:
            idx = int(choice) - 1
            if idx == len(categories) - 1:
                category = input("Enter new category name: ")
            else:
                category = categories[idx]
        except (ValueError, IndexError):
            print_colored("Invalid selection", Colors.RED)
            return False

    # Create category if it doesn't exist
    category_path = os.path.join(DB_DIR, category)
    os.makedirs(category_path, exist_ok=True)

    # Handle subcategory if provided
    if subcategory:
        category_path = os.path.join(category_path, subcategory)
        os.makedirs(category_path, exist_ok=True)

    # Determine destination path
    dest_path = os.path.join(category_path, name)

    # Ask for description if not provided
    if description is None:
        if auto_summary:
            description = input(f"Enter description (suggested: '{auto_summary}'): ")
            if not description:
                description = auto_summary
        else:
            description = input("Enter description (optional): ")

    # Ask for tags if not provided
    if tags is None:
        if suggested_tags:
            tags_input = input(f"Enter tags (suggested: {', '.join(suggested_tags)}): ")
            if not tags_input:
                tags = suggested_tags
            else:
                tags = [t.strip() for t in tags_input.split(",")]
        else:
            tags_input = input("Enter tags (comma-separated, optional): ")
            tags = [t.strip() for t in tags_input.split(",")] if tags_input else []

    # Copy the file
    try:
        shutil.copy2(source, dest_path)
        rel_path = os.path.relpath(dest_path, DB_DIR)

        # Create metadata
        metadata = {
            "description": description or "",
            "source_path": source,
            "added_date": datetime.now().isoformat(),
            "tags": tags or [],
        }

        save_metadata(rel_path, metadata)

        print_colored(
            f"Added file '{name}' to {category}"
            + (f"/{subcategory}" if subcategory else ""),
            Colors.GREEN,
        )
        if description:
            print_colored(f"Description: {description}", Colors.GREEN)
        if tags and len(tags) > 0:
            print_colored(f"Tags: {', '.join(tags)}", Colors.GREEN)
        return True
    except Exception as e:
        print_colored(f"Error adding file: {e}", Colors.RED)
        return False


def find_file(query, content_search=False, tags=None):
    """Find files in the database that match the query"""
    results = []

    # First search by filename
    for root, dirs, files in os.walk(DB_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, DB_DIR)

            # Check if filename matches
            if query.lower() in file.lower():
                results.append((rel_path, "Filename match"))
                continue

            # Check if metadata matches
            metadata = load_metadata(rel_path)

            # Check description
            if (
                metadata.get("description")
                and query.lower() in metadata.get("description").lower()
            ):
                results.append((rel_path, "Description match"))
                continue

            # Check tags
            if metadata.get("tags") and query.lower() in [
                tag.lower() for tag in metadata.get("tags")
            ]:
                results.append((rel_path, "Tag match"))
                continue

            # If requested, search in content
            if content_search:
                try:
                    with open(file_path, errors="ignore") as f:
                        content = f.read()
                        if query.lower() in content.lower():
                            results.append((rel_path, "Content match"))
                except Exception:
                    # Skip files that can't be read as text
                    pass

    # If tags are specified, filter results by tags
    if tags:
        tag_list = [t.strip().lower() for t in tags.split(",")]
        filtered_results = []
        for rel_path, match_type in results:
            metadata = load_metadata(rel_path)
            file_tags = [t.lower() for t in metadata.get("tags", [])]
            if any(tag in file_tags for tag in tag_list):
                filtered_results.append((rel_path, match_type))
        results = filtered_results

    return results


def delete_file(file_path):
    """Delete a file from the database"""
    # Handle full paths and relative paths within the database
    if os.path.isabs(file_path):
        source_path = file_path
    else:
        source_path = os.path.join(DB_DIR, file_path)

    if not os.path.exists(source_path):
        print_colored(f"Error: File '{file_path}' not found in database", Colors.RED)
        return False

    try:
        # Delete the file
        os.remove(source_path)

        # Delete its metadata
        rel_path = (
            os.path.relpath(source_path, DB_DIR)
            if os.path.isabs(source_path)
            else file_path
        )
        metadata_path = get_metadata_path(rel_path)
        if os.path.exists(metadata_path):
            os.remove(metadata_path)

        print_colored(
            f"Deleted '{os.path.basename(source_path)}' from database", Colors.GREEN
        )
        return True
    except Exception as e:
        print_colored(f"Error deleting file: {e}", Colors.RED)
        return False


def inject_file(file_path, dest_name=None, preview=True):
    """Inject a file from the database to the current directory"""
    # Handle full paths and relative paths within the database
    if os.path.isabs(file_path):
        source_path = file_path
    else:
        source_path = os.path.join(DB_DIR, file_path)

    if not os.path.exists(source_path):
        print_colored(f"Error: File '{file_path}' not found in database", Colors.RED)
        return False

    # Determine destination name
    if dest_name is None:
        dest_name = os.path.basename(source_path)

    dest_path = os.path.join(os.getcwd(), dest_name)

    # Check if destination already exists
    if os.path.exists(dest_path):
        overwrite = input(f"File '{dest_name}' already exists. Overwrite? [y/N] ")
        if overwrite.lower() != "y":
            return False

    try:
        # If preview is requested, show file contents
        if preview:
            rel_path = os.path.relpath(source_path, DB_DIR)
            metadata = load_metadata(rel_path)

            print_colored(
                f"\nInjecting file: {os.path.basename(source_path)}", Colors.BOLD
            )

            if metadata.get("description"):
                print(f"Description: {metadata.get('description')}")

            if metadata.get("tags"):
                print(f"Tags: {', '.join(metadata.get('tags'))}")

            # Show file preview for smaller text files
            if os.path.getsize(source_path) < 10000:
                try:
                    with open(source_path, errors="ignore") as f:
                        content = f.read()

                    # Only show preview for what appears to be text files
                    if "\0" not in content:  # Simple binary check
                        print_colored("\nPreview:", Colors.BOLD)
                        preview_lines = content.split("\n")[:10]
                        for line in preview_lines:
                            print(line)
                        if len(preview_lines) < content.count("\n"):
                            print("...")
                except Exception:
                    pass  # Skip preview if it fails

        # Copy the file
        shutil.copy2(source_path, dest_path)
        print_colored(f"Injected '{dest_name}' to current directory", Colors.GREEN)
        return True
    except Exception as e:
        print_colored(f"Error injecting file: {e}", Colors.RED)
        return False


def show_file(file_path):
    """Display file contents with syntax highlighting if available"""
    # Handle full paths and relative paths within the database
    if os.path.isabs(file_path):
        source_path = file_path
    else:
        source_path = os.path.join(DB_DIR, file_path)

    if not os.path.exists(source_path):
        print_colored(f"Error: File '{file_path}' not found in database", Colors.RED)
        return False

    # Get metadata
    rel_path = (
        os.path.relpath(source_path, DB_DIR)
        if os.path.isabs(source_path)
        else file_path
    )
    metadata = load_metadata(rel_path)

    # Display file info
    print_colored(f"\nFile: {os.path.basename(source_path)}", Colors.BOLD)
    if metadata.get("description"):
        print(f"Description: {metadata.get('description')}")
    if metadata.get("tags"):
        print(f"Tags: {', '.join(metadata.get('tags'))}")
    print(f"Path: {rel_path}")
    print(f"Size: {os.path.getsize(source_path)} bytes")
    print(f"Modified: {datetime.fromtimestamp(os.path.getmtime(source_path))}")

    # Try to use syntax highlighting if pygments is available
    pygments_available = importlib.util.find_spec("pygments") is not None

    if not pygments_available:
        try:
            print_colored("\nInstalling syntax highlighting...", Colors.YELLOW)
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pygments"])
            pygments_available = True
        except Exception:
            pass

    print_colored("\nContents:", Colors.BOLD)

    if pygments_available:
        try:
            from pygments import highlight
            from pygments.formatters import TerminalFormatter
            from pygments.lexers import (
                get_lexer_for_filename,
                TextLexer,
            )

            with open(source_path, errors="ignore") as f:
                content = f.read()

            try:
                lexer = get_lexer_for_filename(source_path)
            except Exception:
                lexer = TextLexer()

            print(highlight(content, lexer, TerminalFormatter()))
            return True
        except Exception:
            # Fallback to basic display if highlighting fails
            pygments_available = False

    if not pygments_available:
        try:
            with open(source_path, errors="ignore") as f:
                print(f.read())
            return True
        except UnicodeDecodeError:
            print_colored("Cannot display binary content", Colors.YELLOW)
            return False

    return True
