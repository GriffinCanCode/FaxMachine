"""
Faxmachine - File Template Manager
A utility for storing and injecting commonly used files and templates.
"""

from .db import (
    DB_DIR, METADATA_DIR, CONFIG_DIR, 
    init_db, get_metadata_path, save_metadata, load_metadata, 
    list_items, add_file, find_file, delete_file, inject_file, show_file,
    print_colored, Colors
)
