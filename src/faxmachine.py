#!/usr/bin/env python3
"""
Faxmachine - File Template Manager
A utility for storing and injecting commonly used files and templates.
"""

import os
import sys
import shutil
import argparse
import json
from pathlib import Path
import readline  # For better command line editing
import tempfile
import difflib
import subprocess
import re
from datetime import datetime

# Constants
VERSION = "1.1.0"
CONFIG_DIR = os.path.expanduser("~/.faxmachine")
DB_DIR = os.path.join(CONFIG_DIR, "db")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
METADATA_DIR = os.path.join(CONFIG_DIR, "metadata")

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_colored(text, color):
    """Print text with color"""
    print(f"{color}{text}{Colors.ENDC}")

def print_header(text):
    """Print a nicely formatted header"""
    try:
        width = min(os.get_terminal_size().columns, 80)
    except (OSError, AttributeError):
        width = 80  # Default width if not in a terminal
    print_colored("=" * width, Colors.BOLD)
    print_colored(f"{text.center(width)}", Colors.BOLD + Colors.BLUE)
    print_colored("=" * width, Colors.BOLD)

def create_default_config():
    """Create default configuration"""
    config = {
        "version": VERSION,
        "aliases": {},
        "last_accessed": [],
        "settings": {
            "default_editor": os.environ.get("EDITOR", "vi"),
            "search_content": True,
            "preview_before_inject": True
        }
    }
    return config

def load_config():
    """Load or create configuration"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print_colored("Config file corrupted, creating new one", Colors.RED)
            config = create_default_config()
            save_config(config)
            return config
    else:
        config = create_default_config()
        save_config(config)
        return config

def save_config(config):
    """Save configuration to file"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

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
        with open(example_gitignore, 'w') as f:
            f.write("""# Python gitignore
__pycache__/
*.py[cod]
*$py.class
.env
venv/
ENV/
.vscode/
""")
        
        # Add metadata for example file
        save_metadata("git/python-gitignore", {
            "description": "Standard gitignore for Python projects",
            "added_date": datetime.now().isoformat(),
            "tags": ["python", "git", "ignore"]
        })

def get_metadata_path(file_path):
    """Get the path to the metadata file for a given file"""
    rel_path = os.path.relpath(file_path, DB_DIR) if os.path.isabs(file_path) else file_path
    safe_path = rel_path.replace("/", "_").replace("\\", "_")
    return os.path.join(METADATA_DIR, f"{safe_path}.json")

def save_metadata(file_path, metadata):
    """Save metadata for a file"""
    os.makedirs(METADATA_DIR, exist_ok=True)
    metadata_path = get_metadata_path(file_path)
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

def load_metadata(file_path):
    """Load metadata for a file"""
    metadata_path = get_metadata_path(file_path)
    
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r') as f:
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
            prefix = "   " * (indent-1) + "└── " if is_last and indent > 0 else "   " * (indent-1) + "├── " if indent > 0 else ""
            print_colored(f"{prefix}{item}/", Colors.BLUE + Colors.BOLD)
            list_items(item_path, indent + 1)
        else:
            # Print file
            prefix = "   " * (indent-1) + "└── " if is_last and indent > 0 else "   " * (indent-1) + "├── " if indent > 0 else ""
            rel_path = os.path.relpath(item_path, DB_DIR)
            metadata = load_metadata(rel_path)
            description = metadata.get('description', '')
            description_text = f" - {description}" if description else ""
            print(f"{prefix}{item}{description_text}")

def add_file(source, category=None, name=None, subcategory=None, description=None, tags=None):
    """Add a file to the database"""
    if not os.path.exists(source):
        print_colored(f"Error: Source file '{source}' not found", Colors.RED)
        return False
    
    # Handle relative paths
    source = os.path.abspath(source)
    
    # If no name provided, use source filename
    if name is None:
        name = os.path.basename(source)
    
    # If no category provided, ask user
    if category is None:
        print_header("Select Category")
        categories = [d for d in os.listdir(DB_DIR) 
                    if os.path.isdir(os.path.join(DB_DIR, d))]
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
    
    # Copy the file
    try:
        shutil.copy2(source, dest_path)
        rel_path = os.path.relpath(dest_path, DB_DIR)
        
        # Create metadata
        metadata = {
            "description": description or "",
            "source_path": source,
            "added_date": datetime.now().isoformat(),
            "tags": tags or []
        }
        
        save_metadata(rel_path, metadata)
        
        print_colored(f"Added file '{name}' to {category}" + 
                     (f"/{subcategory}" if subcategory else ""), Colors.GREEN)
        if description:
            print_colored(f"Description: {description}", Colors.GREEN)
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
            if metadata.get('description') and query.lower() in metadata.get('description').lower():
                results.append((rel_path, "Description match"))
                continue
                
            # Check tags
            if metadata.get('tags') and query.lower() in [tag.lower() for tag in metadata.get('tags')]:
                results.append((rel_path, "Tag match"))
                continue
                
            # If requested, search in content
            if content_search:
                try:
                    with open(file_path, 'r', errors='ignore') as f:
                        content = f.read()
                        if query.lower() in content.lower():
                            results.append((rel_path, "Content match"))
                except Exception:
                    # Skip files that can't be read as text
                    pass
    
    # If tags are specified, filter results by tags
    if tags:
        tag_list = [t.strip().lower() for t in tags.split(',')]
        filtered_results = []
        for rel_path, match_type in results:
            metadata = load_metadata(rel_path)
            file_tags = [t.lower() for t in metadata.get('tags', [])]
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
        
        # Delete metadata
        metadata_path = get_metadata_path(file_path)
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
            
        # Update last accessed in config
        config = load_config()
        rel_path = os.path.relpath(source_path, DB_DIR) if os.path.isabs(source_path) else file_path
        if rel_path in config["last_accessed"]:
            config["last_accessed"].remove(rel_path)
        save_config(config)
        
        print_colored(f"Deleted '{os.path.basename(source_path)}' from database", Colors.GREEN)
        return True
    except Exception as e:
        print_colored(f"Error deleting file: {e}", Colors.RED)
        return False

def preview_diff(source_path, dest_path):
    """Show a preview diff between source and destination files"""
    if os.path.exists(dest_path):
        with open(source_path, 'r', errors='ignore') as f:
            source_lines = f.readlines()
        with open(dest_path, 'r', errors='ignore') as f:
            dest_lines = f.readlines()
            
        diff = difflib.unified_diff(
            dest_lines, source_lines,
            fromfile=f'current: {os.path.basename(dest_path)}',
            tofile=f'template: {os.path.basename(source_path)}',
        )
        
        # Convert diff to string and colorize it
        diff_text = ""
        for line in diff:
            if line.startswith('+'):
                diff_text += Colors.GREEN + line + Colors.ENDC
            elif line.startswith('-'):
                diff_text += Colors.RED + line + Colors.ENDC
            elif line.startswith('^'):
                diff_text += Colors.BLUE + line + Colors.ENDC
            else:
                diff_text += line
                
        return diff_text
    else:
        # If destination doesn't exist, show the full source content
        with open(source_path, 'r', errors='ignore') as f:
            content = f.read()
        return f"New file: {os.path.basename(dest_path)}\n\n{content}"

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
    
    # Determine destination filename
    if dest_name is None:
        dest_name = os.path.basename(source_path)
    
    dest_path = os.path.join(os.getcwd(), dest_name)
    
    # Show preview if requested and file exists
    if preview and os.path.exists(dest_path):
        print_header("File Comparison Preview")
        diff_text = preview_diff(source_path, dest_path)
        print(diff_text)
        
        confirm = input(f"File '{dest_name}' already exists. Overwrite? [y/N] ")
        if confirm.lower() != 'y':
            print_colored("Operation cancelled", Colors.YELLOW)
            return False
    elif os.path.exists(dest_path):
        confirm = input(f"File '{dest_name}' already exists. Overwrite? [y/N] ")
        if confirm.lower() != 'y':
            print_colored("Operation cancelled", Colors.YELLOW)
            return False
    
    # Copy the file
    try:
        shutil.copy2(source_path, dest_path)
        print_colored(f"Injected '{os.path.basename(source_path)}' to current directory", Colors.GREEN)
        
        # Update last accessed in config
        config = load_config()
        rel_path = os.path.relpath(source_path, DB_DIR)
        if rel_path in config["last_accessed"]:
            config["last_accessed"].remove(rel_path)
        config["last_accessed"].insert(0, rel_path)
        config["last_accessed"] = config["last_accessed"][:10]  # Keep only 10 most recent
        save_config(config)
        
        return True
    except Exception as e:
        print_colored(f"Error injecting file: {e}", Colors.RED)
        return False

def show_file(file_path):
    """Show the contents of a file"""
    # Handle full paths and relative paths within the database
    if os.path.isabs(file_path):
        source_path = file_path
    else:
        source_path = os.path.join(DB_DIR, file_path)
    
    if not os.path.exists(source_path):
        print_colored(f"Error: File '{file_path}' not found in database", Colors.RED)
        return False
    
    try:
        # Show metadata if available
        rel_path = os.path.relpath(source_path, DB_DIR) if os.path.isabs(source_path) else file_path
        metadata = load_metadata(rel_path)
        
        print_header(f"File: {os.path.basename(source_path)}")
        
        if metadata:
            print_colored("Metadata:", Colors.BOLD)
            if metadata.get('description'):
                print(f"Description: {metadata['description']}")
            if metadata.get('added_date'):
                print(f"Added on: {metadata['added_date'].split('T')[0]}")
            if metadata.get('tags'):
                print(f"Tags: {', '.join(metadata['tags'])}")
            print()
        
        print_colored("Content:", Colors.BOLD)
        with open(source_path, 'r') as f:
            content = f.read()
        print(content)
        return True
    except Exception as e:
        print_colored(f"Error reading file: {e}", Colors.RED)
        return False

def interactive_browser():
    """Interactive file browser"""
    print_header("Faxmachine File Browser")
    current_path = DB_DIR
    breadcrumb = []
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_header("Faxmachine File Browser")
        
        # Show breadcrumb
        if breadcrumb:
            print("Location:", " > ".join(breadcrumb))
        else:
            print("Location: (root)")
        
        # Get items in current directory
        items = sorted(os.listdir(current_path))
        dirs = [d for d in items if os.path.isdir(os.path.join(current_path, d))]
        files = [f for f in items if os.path.isfile(os.path.join(current_path, f))]
        
        # Show directories
        print_colored("\nDirectories:", Colors.BOLD)
        if not dirs:
            print("  (No directories)")
        else:
            for i, d in enumerate(dirs):
                print(f"  {i+1}. {d}/")
        
        # Show files
        print_colored("\nFiles:", Colors.BOLD)
        if not files:
            print("  (No files)")
        else:
            for i, f in enumerate(files):
                file_path = os.path.join(current_path, f)
                rel_path = os.path.relpath(file_path, DB_DIR)
                metadata = load_metadata(rel_path)
                desc = f" - {metadata.get('description')}" if metadata.get('description') else ""
                print(f"  {i+1+len(dirs)}. {f}{desc}")
        
        # Show options
        print_colored("\nActions:", Colors.BOLD)
        print("  a. Add new file")
        print("  s. Search")
        print("  d. Delete file")
        print("  e. Edit file metadata")
        if breadcrumb:
            print("  u. Up one level")
        print("  q. Quit browser")
        
        choice = input("\nEnter your choice: ")
        
        if choice == 'q':
            break
        elif choice == 'u' and breadcrumb:
            breadcrumb.pop()
            current_path = DB_DIR
            for b in breadcrumb:
                current_path = os.path.join(current_path, b)
        elif choice == 'a':
            source = input("Enter path to file: ")
            category = breadcrumb[0] if breadcrumb else None
            subcategory = "/".join(breadcrumb[1:]) if len(breadcrumb) > 1 else None
            name = input("Enter name for the file (leave blank for original filename): ")
            if not name:
                name = None
            description = input("Enter description (optional): ")
            tags = input("Enter tags (comma-separated, optional): ")
            tag_list = [t.strip() for t in tags.split(',')] if tags else None
            add_file(source, category, name, subcategory, description, tag_list)
            input("Press Enter to continue...")
        elif choice == 's':
            query = input("Enter search term: ")
            content_search = input("Search in file contents? [y/N] ").lower() == 'y'
            tags = input("Filter by tags (comma-separated, optional): ")
            
            results = find_file(query, content_search, tags)
            
            if results:
                print_colored(f"\nFound {len(results)} matches:", Colors.GREEN)
                for i, (result, match_type) in enumerate(results):
                    print(f"  {i+1}. {result} ({match_type})")
                
                file_choice = input("\nEnter number to inject file, v+number to view, or Enter to cancel: ")
                
                if file_choice.startswith('v') and file_choice[1:].isdigit():
                    idx = int(file_choice[1:]) - 1
                    if 0 <= idx < len(results):
                        show_file(results[idx][0])
                        input("Press Enter to continue...")
                elif file_choice.isdigit():
                    idx = int(file_choice) - 1
                    if 0 <= idx < len(results):
                        dest_name = input("Enter destination filename (leave blank for original): ")
                        if not dest_name:
                            dest_name = None
                        inject_file(results[idx][0], dest_name)
            else:
                print_colored("No matches found", Colors.YELLOW)
                input("Press Enter to continue...")
        elif choice == 'd':
            if files:
                file_idx = input("Enter file number to delete: ")
                try:
                    idx = int(file_idx) - 1 - len(dirs)
                    if 0 <= idx < len(files):
                        file_path = os.path.join(current_path, files[idx])
                        rel_path = os.path.relpath(file_path, DB_DIR)
                        
                        confirm = input(f"Are you sure you want to delete '{files[idx]}'? [y/N] ")
                        if confirm.lower() == 'y':
                            delete_file(rel_path)
                    else:
                        print_colored("Invalid file number", Colors.RED)
                except ValueError:
                    print_colored("Invalid input", Colors.RED)
                input("Press Enter to continue...")
            else:
                print_colored("No files to delete", Colors.YELLOW)
                input("Press Enter to continue...")
        elif choice == 'e':
            if files:
                file_idx = input("Enter file number to edit metadata: ")
                try:
                    idx = int(file_idx) - 1 - len(dirs)
                    if 0 <= idx < len(files):
                        file_path = os.path.join(current_path, files[idx])
                        rel_path = os.path.relpath(file_path, DB_DIR)
                        metadata = load_metadata(rel_path)
                        
                        print_colored(f"\nEditing metadata for '{files[idx]}'", Colors.GREEN)
                        description = input(f"Description [{metadata.get('description', '')}]: ")
                        current_tags = ', '.join(metadata.get('tags', []))
                        tags = input(f"Tags (comma-separated) [{current_tags}]: ")
                        
                        if description or description == '':
                            metadata['description'] = description
                        if tags or tags == '':
                            metadata['tags'] = [t.strip() for t in tags.split(',')] if tags else []
                        
                        save_metadata(rel_path, metadata)
                        print_colored("Metadata updated", Colors.GREEN)
                    else:
                        print_colored("Invalid file number", Colors.RED)
                except ValueError:
                    print_colored("Invalid input", Colors.RED)
                input("Press Enter to continue...")
            else:
                print_colored("No files to edit", Colors.YELLOW)
                input("Press Enter to continue...")
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(dirs):
                    breadcrumb.append(dirs[idx])
                    current_path = os.path.join(current_path, dirs[idx])
                elif len(dirs) <= idx < len(dirs) + len(files):
                    file_idx = idx - len(dirs)
                    file_path = os.path.join(current_path, files[file_idx])
                    rel_path = os.path.relpath(file_path, DB_DIR)
                    
                    print_colored(f"\nSelected: {files[file_idx]}", Colors.GREEN)
                    print("i. Inject to current directory")
                    print("v. View file contents")
                    print("e. Edit metadata")
                    print("d. Delete file")
                    print("c. Cancel")
                    
                    action = input("\nEnter action: ")
                    
                    if action == 'i':
                        dest_name = input("Enter destination filename (leave blank for original): ")
                        if not dest_name:
                            dest_name = None
                        inject_file(rel_path, dest_name)
                        input("Press Enter to continue...")
                    elif action == 'v':
                        show_file(rel_path)
                        input("Press Enter to continue...")
                    elif action == 'e':
                        metadata = load_metadata(rel_path)
                        
                        print_colored(f"\nEditing metadata for '{files[file_idx]}'", Colors.GREEN)
                        description = input(f"Description [{metadata.get('description', '')}]: ")
                        current_tags = ', '.join(metadata.get('tags', []))
                        tags = input(f"Tags (comma-separated) [{current_tags}]: ")
                        
                        if description or description == '':
                            metadata['description'] = description
                        if tags or tags == '':
                            metadata['tags'] = [t.strip() for t in tags.split(',')] if tags else []
                        
                        save_metadata(rel_path, metadata)
                        print_colored("Metadata updated", Colors.GREEN)
                        input("Press Enter to continue...")
                    elif action == 'd':
                        confirm = input(f"Are you sure you want to delete '{files[file_idx]}'? [y/N] ")
                        if confirm.lower() == 'y':
                            delete_file(rel_path)
                        input("Press Enter to continue...")
            except (ValueError, IndexError):
                print_colored("Invalid choice", Colors.RED)
                input("Press Enter to continue...")

def process_search_command(args):
    """Process the search command with additional flags"""
    if args.list_only:
        # List results without prompting
        results = find_file(args.query, args.content_search, args.tags)
        if results:
            for i, (result, match_type) in enumerate(results):
                print(f"{i+1}. {result} ({match_type})")
            return 0
        else:
            return 1
    elif args.show_index is not None:
        # Show specific file by index
        results = find_file(args.query, args.content_search, args.tags)
        try:
            idx = int(args.show_index) - 1
            if 0 <= idx < len(results):
                show_file(results[idx][0])
                return 0
            else:
                print_colored("Invalid index", Colors.RED)
                return 1
        except (ValueError, IndexError):
            print_colored("Invalid index", Colors.RED)
            return 1
    elif args.inject_index is not None:
        # Inject specific file by index
        results = find_file(args.query, args.content_search, args.tags)
        try:
            idx = int(args.inject_index) - 1
            if 0 <= idx < len(results):
                inject_file(results[idx][0], args.name)
                return 0
            else:
                print_colored("Invalid index", Colors.RED)
                return 1
        except (ValueError, IndexError):
            print_colored("Invalid index", Colors.RED)
            return 1
    elif args.delete_index is not None:
        # Delete specific file by index
        results = find_file(args.query, args.content_search, args.tags)
        try:
            idx = int(args.delete_index) - 1
            if 0 <= idx < len(results):
                delete_file(results[idx][0])
                return 0
            else:
                print_colored("Invalid index", Colors.RED)
                return 1
        except (ValueError, IndexError):
            print_colored("Invalid index", Colors.RED)
            return 1
    else:
        # Regular search with prompting
        results = find_file(args.query, args.content_search, args.tags)
        if results:
            print_header(f"Search Results for '{args.query}'")
            for i, (result, match_type) in enumerate(results):
                print(f"{i+1}. {result} ({match_type})")
            
            choice = input("\nEnter number to inject file, v+number to view, or Enter to cancel: ")
            
            if choice.startswith('v') and choice[1:].isdigit():
                idx = int(choice[1:]) - 1
                if 0 <= idx < len(results):
                    show_file(results[idx][0])
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(results):
                    dest_name = input("Enter destination filename (leave blank for original): ")
                    if not dest_name:
                        dest_name = None
                    inject_file(results[idx][0], dest_name)
        else:
            print_colored(f"No files matching '{args.query}' found", Colors.YELLOW)
            return 1
        return 0

def display_help():
    """Display detailed help information"""
    print_header(f"Faxmachine v{VERSION} - Help")
    
    print("\nCOMMANDS:")
    print("  browse       Browse and manage files with interactive browser")
    print("  add          Add a file to the database")
    print("  search       Search for files")
    print("  show         Display a file's contents")
    print("  inject       Insert a file into current directory")
    print("  list         List all files by category")
    print("  recent       Show recently accessed files")
    print("  delete       Remove a file from the database")
    print("  init         Initialize or reset the database\n")
    
    print("EXAMPLES:")
    print("  faxmachine browse                   # Interactive browser")
    print("  faxmachine add myfile.txt           # Add a file interactively")
    print("  faxmachine add config.yml -c config # Add to the 'config' category")
    print("  faxmachine search gitignore         # Search for 'gitignore'")
    print("  faxmachine inject git/gitignore     # Inject a file")
    print("  faxmachine print git/gitignore      # Same as inject (alias)")
    
    print("\nConfiguration:")
    print(f"  Config directory: {CONFIG_DIR}")
    print(f"  Database directory: {DB_DIR}")
    
    print("\nMetadata:")
    print("  Files can have descriptions and tags for better searchability.")
    print("  Add tags when adding files or edit metadata in the browser.")
    
    print("\nFeatures:")
    print("  - Content-based search: search inside files")
    print("  - File preview before injection")
    print("  - Metadata for better organization")
    print("  - Tagging system for classification")

def main():
    """Main entry point for the application"""
    # Create argument parser
    parser = argparse.ArgumentParser(description='Faxmachine - File Template Manager')
    parser.add_argument('--version', action='store_true', help='Show version information')
    parser.add_argument('--detailed-help', action='store_true', dest='show_help', help='Show detailed help')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize the database')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available files')
    list_parser.add_argument('category', nargs='?', help='Category to list')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add a file to the database')
    add_parser.add_argument('file', help='File to add')
    add_parser.add_argument('-c', '--category', help='Category to add the file to')
    add_parser.add_argument('-s', '--subcategory', help='Subcategory to add the file to')
    add_parser.add_argument('-n', '--name', help='Name for the stored file')
    add_parser.add_argument('-d', '--description', help='Description of the file')
    add_parser.add_argument('-t', '--tags', help='Comma-separated tags')
    
    # Inject command with print alias
    inject_parser = subparsers.add_parser('inject', aliases=['print'], help='Inject a file from the database')
    inject_parser.add_argument('file', help='File path within the database')
    inject_parser.add_argument('-n', '--name', help='Name for the injected file')
    inject_parser.add_argument('--no-preview', action='store_true', help='Skip preview when injecting')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for files')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('-c', '--content-search', action='store_true', help='Search in file contents')
    search_parser.add_argument('-t', '--tags', help='Filter by comma-separated tags')
    search_parser.add_argument('--list-only', action='store_true', help='Only list results, no prompts')
    search_parser.add_argument('--show-index', help='Show file at specified index')
    search_parser.add_argument('--inject-index', help='Inject file at specified index')
    search_parser.add_argument('--delete-index', help='Delete file at specified index')
    search_parser.add_argument('-n', '--name', help='Name for injected file (with --inject-index)')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show file contents')
    show_parser.add_argument('file', help='File path within the database')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a file from the database')
    delete_parser.add_argument('file', help='File path within the database')
    
    # Interactive command
    interactive_parser = subparsers.add_parser('browse', help='Interactive browser')
    
    # Recent command
    recent_parser = subparsers.add_parser('recent', help='Show recently accessed files')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle version display
    if args.version:
        print(f"Faxmachine v{VERSION}")
        return 0
        
    # Handle detailed help
    if args.show_help:
        display_help()
        return 0
    
    # Ensure config directory exists
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    # Handle commands
    if args.command == 'init' or not os.path.exists(DB_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        os.makedirs(DB_DIR, exist_ok=True)
        os.makedirs(METADATA_DIR, exist_ok=True)
        init_db()
        print_colored("Faxmachine database initialized", Colors.GREEN)
        return 0
    elif args.command == 'list':
        print_header("Faxmachine Database Contents")
        list_items()
        return 0
    elif args.command == 'add':
        tags = [t.strip() for t in args.tags.split(',')] if args.tags else None
        success = add_file(args.file, args.category, args.name, args.subcategory, args.description, tags)
        return 0 if success else 1
    elif args.command == 'inject':
        preview = not args.no_preview
        success = inject_file(args.file, args.name, preview)
        return 0 if success else 1
    elif args.command == 'search':
        return process_search_command(args)
    elif args.command == 'show':
        success = show_file(args.file)
        return 0 if success else 1
    elif args.command == 'delete':
        success = delete_file(args.file)
        return 0 if success else 1
    elif args.command == 'browse':
        interactive_browser()
    elif args.command == 'recent':
        config = load_config()
        if config["last_accessed"]:
            print_header("Recently Accessed Files")
            for i, file in enumerate(config["last_accessed"]):
                print(f"{i+1}. {file}")
            
            choice = input("\nEnter number to inject file, v+number to view, or Enter to cancel: ")
            
            if choice.startswith('v') and choice[1:].isdigit():
                idx = int(choice[1:]) - 1
                if 0 <= idx < len(config["last_accessed"]):
                    show_file(config["last_accessed"][idx])
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(config["last_accessed"]):
                    dest_name = input("Enter destination filename (leave blank for original): ")
                    if not dest_name:
                        dest_name = None
                    inject_file(config["last_accessed"][idx], dest_name)
        else:
            print_colored("No recently accessed files", Colors.YELLOW)
    else:
        # Display a welcome message and brief help
        print_header(f"Faxmachine v{VERSION}")
        print("\nCommon Commands:")
        print("\nUsage: faxmachine <command> [options]")
        print("\nCOMMANDS:")
        print("  browse     Browse files interactively")
        print("  add        Add a file to the database")
        print("  search     Search for files")
        print("  inject     Insert a file into current directory")
        print("  list       List all files by category")
        print("  recent     Show recently accessed files")
        print("  delete     Remove a file")
        print("  init       Initialize the database")
        print("\nUse 'faxmachine <command> --help' for more information on a command")
        print("Use 'faxmachine --detailed-help' for detailed help information")
        
        # Offer to initialize if not yet initialized
        if not os.path.exists(DB_DIR):
            print_colored("\nDatabase not initialized. Initialize now? [Y/n] ", Colors.YELLOW)
            choice = input()
            if choice.lower() != 'n':
                init_db()
                print_colored("Database initialized", Colors.GREEN)
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print_colored(f"Error: {e}", Colors.RED)
        sys.exit(1)