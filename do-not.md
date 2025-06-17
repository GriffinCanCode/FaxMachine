# Faxmachine - Technical Documentation

This document provides a comprehensive technical overview of the Faxmachine codebase, its architecture, modules, and implementation details. It is intended for developers who want to understand how Faxmachine works internally, contribute to the project, or extend its functionality.

## Codebase Architecture

Faxmachine is structured as a Python application with a Bash wrapper for improved user experience. The codebase consists of these main components:

1. `faxmachine.py`: The core Python implementation
2. `faxmachine.sh`: Bash wrapper script for improved CLI experience
3. `db.py`: Database operations module

### Directory Structure

```
faxmachine/
├── src/
│   ├── faxmachine.py      # Core Python implementation
│   ├── faxmachine.sh      # Bash wrapper script
│   └── db.py              # Database operations
├── templates/             # Built-in templates
├── tests/                 # Unit and integration tests
└── add_templates_to_faxmachine.sh  # Helper script for template installation
```

## Module Descriptions

### 1. faxmachine.py

The main Python module containing the core functionality. Key components include:

#### Core Functions

- `main()`: Entry point for the application
- `init_db()`: Initialize database structure
- `print_header()`: Utility for formatted output
- `display_help()`: Show detailed help information

#### File Management Functions

- `add_file()`: Add a file to the database with metadata
- `delete_file()`: Remove a file from the database
- `find_file()`: Search for files using various criteria
- `inject_file()`: Copy a file from the database to the current directory
- `show_file()`: Display file contents with optional highlighting

#### Interactive Browser

- `interactive_file_browser()`: Main file browser implementation
- `_curses_file_browser()`: Enhanced curses-based UI when available
- `vim_view_with_preview()`: View files with Vim-like interface and smart preview

#### Smart Analysis

- `smart_preview_file()`: Generate an intelligent preview with content analysis
- `_extract_keywords()`: Extract key terms from text content
- `_get_all_json_keys()`: Recursively analyze JSON structures

#### Command Line Interface

- `process_search_command()`: Handle search command with all its options
- `mass_add_files()`: Implementation for batch file addition
- A comprehensive argument parser with subcommands for all functionality

### 2. faxmachine.sh

Bash wrapper that provides:

- Interactive menu system for common operations
- Command-line argument handling
- Environment checking (Python availability, script permissions)
- Execution of the Python script with appropriate arguments
- User-friendly error handling and output formatting

Key functions:
- `get_script_path()`: Resolves script location even with symlinks
- Interactive menu handling with options for all main features
- Command argument forwarding to the Python script

### 3. db.py

Database module containing core functions for file storage and metadata management:

#### Database Functions

- `init_db()`: Initialize the database directory structure
- `get_metadata_path()`: Get the path to a file's metadata
- `save_metadata()`: Store metadata for a file
- `load_metadata()`: Retrieve a file's metadata

#### File Operations

- `list_items()`: List database contents in a tree structure
- `add_file()`: Add a file to the database
- `find_file()`: Search for files in the database
- `delete_file()`: Delete a file from the database
- `inject_file()`: Copy a file to the current directory
- `show_file()`: Display file contents with highlighting

## Data Structures

### Configuration

Stored in `~/.faxmachine/config/config.json`:

```json
{
  "version": "1.1.0",
  "aliases": {},
  "last_accessed": ["recently accessed file paths"],
  "settings": {
    "default_editor": "vi",
    "search_content": true,
    "preview_before_inject": true
  }
}
```

### Metadata

Stored in `~/.faxmachine/metadata/{filename}.json`:

```json
{
  "description": "Description of the file",
  "source_path": "Original path when added",
  "added_date": "ISO format date when added",
  "tags": ["tag1", "tag2", "tag3"]
}
```

## Key Algorithms

### Smart Document Analysis

Faxmachine uses a multi-tiered approach to analyze documents:

1. **File Type Detection**:
   - Examines file extensions and content patterns
   - Uses content sampling to identify binary vs text files

2. **Content Analysis**:
   - For PDF files: Extracts text, identifies titles, sections, and key topics
   - For JSON: Analyzes structure and key patterns
   - For CSV: Extracts headers and data patterns
   - For code files: Identifies language and important constructs

3. **NLP Processing**:
   - Uses a cascading strategy for NLP with multiple fallbacks:
     1. First attempts to use YAKE (lightweight keyword extraction)
     2. Falls back to spaCy (medium-weight NLP) if available
     3. Further fallback to NLTK for basic NLP capabilities
     4. Final fallback to simple frequency analysis if no NLP libraries available

### Search Implementation

The search function uses a multi-criteria approach:

1. **Filename Matching**: First pass to match against filenames
2. **Metadata Matching**: Searches descriptions and tags
3. **Content Matching**: When requested, performs full-text search
4. **Tag Filtering**: Additional filtering based on user-specified tags

### Interactive Browser Logic

The interactive browser uses either:

1. **Curses-based UI** when available:
   - Handles keyboard navigation
   - Manages visual state (selection, expansion, etc.)
   - Implements dropdown views and multi-select functionality

2. **Fallback Simple UI** when curses is unavailable:
   - Uses simple text-based interface
   - Provides similar functionality through numbered menu options

## Performance Considerations

1. **Lazy Loading**:
   - NLP libraries are only installed when needed
   - Resource-intensive operations only run on demand

2. **Content Limiting**:
   - Large files are sampled rather than fully processed
   - PDFs are analyzed page by page to limit memory usage

3. **Resource Management**:
   - TUI (Terminal UI) gracefully degrades based on terminal capabilities
   - Content previews adjust based on file size and type

## Error Handling

1. **Dependency Management**:
   - Optional dependencies are installed on demand
   - Cascading fallbacks for NLP and other advanced features

2. **File Operations**:
   - All file operations use try/except blocks
   - Permission errors are handled gracefully
   - Binary files are detected and handled appropriately

3. **User Input**:
   - Input validation for all interactive operations
   - Clear error messages with suggested next steps

## Extension Points

Faxmachine can be extended in several ways:

1. **New File Type Support**:
   - Extend the `smart_preview_file()` function to handle additional file types
   - Add type-specific processing in the content analysis logic

2. **Custom Commands**:
   - Add new subcommands to the argument parser in `main()`
   - Implement command handling functions

3. **Enhanced UI**:
   - Extend the curses-based UI with additional views or interactions
   - Add new navigation or selection modes

4. **Additional Metadata**:
   - Expand the metadata schema to store additional information
   - Add processing for the new metadata fields

## Internal APIs

### Database API

```python
# Initialize database
init_db()

# Metadata operations
metadata_path = get_metadata_path(file_path)
save_metadata(file_path, metadata_dict)
metadata = load_metadata(file_path)

# File operations
list_items(path=None, indent=0)
add_file(source, category, name, subcategory, description, tags)
find_file(query, content_search=False, tags=None)
delete_file(file_path)
inject_file(file_path, dest_name=None, preview=True)
show_file(file_path)
```

### Content Analysis API

```python
# Smart document analysis
summary, tags, preview, error = smart_preview_file(file_path)

# Helper functions
keywords = _extract_keywords(text, max_keywords=5)
all_keys = _get_all_json_keys(json_obj)
```

### UI Components

```python
# Interactive browser components
interactive_file_browser()
_curses_file_browser(in_db=False, shortcuts=None)
vim_view_with_preview(file_path)

# Display utilities
print_header(text)
print_colored(text, color)
preview_diff(source_path, dest_path)
```

## Dependencies

### Required Dependencies

- **Python 3.6+**: Core runtime environment
- **Bash**: For the shell wrapper script

### Optional Dependencies (auto-installed when needed)

- **NLP Libraries**:
  - YAKE: Lightweight keyword extraction
  - spaCy: More advanced NLP capabilities
  - NLTK: Fallback NLP functionality

- **Document Processing**:
  - pdfplumber: For PDF text extraction and analysis

- **Display Enhancement**:
  - pygments: For syntax highlighting
  - curses: For terminal UI (built into Python)

## Testing Strategy

The codebase follows these testing approaches:

1. **Unit Tests**:
   - Test individual functions in isolation
   - Mock file system operations
   - Test various content analysis scenarios

2. **Integration Tests**:
   - Test complete workflows across modules
   - Verify database operations work together correctly

3. **Error Handling Tests**:
   - Verify graceful degradation with missing dependencies
   - Test behavior with invalid inputs
   - Ensure appropriate error messages

## Future Enhancements

Potential areas for future development:

1. **Expanded File Type Support**:
   - Additional document formats (DOCX, XLSX, etc.)
   - Image file analysis and tagging

2. **Enhanced NLP**:
   - More sophisticated content understanding
   - Better semantic tagging
   - Domain-specific analysis

3. **Collaborative Features**:
   - Template sharing across users
   - Remote template repositories
   - Team-based template management

4. **Extended UI Options**:
   - Web interface
   - GUI desktop application
   - IDE integrations

## Known Limitations

1. **Large File Handling**:
   - Files over 1MB are not fully analyzed
   - Binary files have limited preview capability

2. **Performance**:
   - Initial content analysis can be slow for complex documents
   - Multiple file operations are not parallelized

3. **Dependencies**:
   - NLP features require internet connectivity for first-time installation
   - PDF processing requires additional libraries

## Debugging Tips

1. **Common Issues**:
   - Permission problems in config directory
   - Missing dependencies
   - Terminal compatibility issues with curses

2. **Debugging Approaches**:
   - Check logs in ~/.faxmachine/
   - Run with --verbose flag for additional output
   - Inspect metadata files directly for corruption

## Implementation Details

### Smart File Analysis

The file analysis system uses a layered approach:

1. **File Type Detection**:
   - Extension-based identification
   - Content sampling for binary detection
   - MIME type fallback when available

2. **Content Extraction**:
   - Text files: Direct reading with encoding detection
   - JSON: Structured parsing with schema detection
   - CSV: Header and data type analysis
   - PDF: Multi-stage text extraction and cleaning

3. **Content Analysis**:
   - Keyword extraction with multiple NLP backends
   - Structural analysis for structured data
   - Pattern matching for common file types
   - Frequency analysis for term importance

### Terminal UI Implementation

The terminal UI uses these techniques:

1. **Curses-based UI**:
   - Custom window management
   - Color pair definitions
   - Keyboard input handling
   - Dynamic content rendering

2. **Fallback UI**:
   - ANSI color codes for highlighting
   - Numbered menu system
   - Clear screen commands for "refresh"
   - ASCII art for visual structure