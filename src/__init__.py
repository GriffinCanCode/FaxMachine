"""
Faxmachine - File Template Manager
A utility for storing and injecting commonly used files and templates.
"""

from .db import (
    add_file,
    Colors,
    CONFIG_DIR,
    DB_DIR,
    delete_file,
    find_file,
    get_metadata_path,
    init_db,
    inject_file,
    list_items,
    load_metadata,
    METADATA_DIR,
    print_colored,
    save_metadata,
    show_file,
)
