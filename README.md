# Faxmachine - File Template Manager

Faxmachine is a powerful utility for storing, organizing, and injecting commonly used files and templates across your projects. It serves as a centralized repository for your frequently used code snippets, configuration files, boilerplate templates, and documentation.

## Features

- **Simple Command Line Interface**: Easy to use commands for managing your file templates
- **Interactive Browser**: Navigate your template collection with a user-friendly interface featuring:
  - Tree-like visualization of categories and files
  - Smart dropdowns showing file summaries
  - Multi-select capability for batch operations
  - Vim-like navigation options for power users
- **Smart Search**: Find templates by filename, contents, tags, or description
- **File Preview**: See what you're getting before injecting files, with:
  - Syntax highlighting for code files
  - Content analysis for quick understanding
  - Diff preview when overwriting existing files
- **Metadata Support**: Add descriptions and tags to better organize your templates
  - Automatic tag suggestion based on file content
  - Smart file summarization for better organization
- **Category Organization**: Keep templates neatly arranged in categories and subcategories
- **Smart Document Analysis**: Automatic content analysis that:
  - Extracts key information from PDFs, JSON, CSV and code files
  - Suggests relevant tags based on content
  - Provides summary of file structure and purpose
- **Batch Operations**: Add, view, or inject multiple files at once
- **Recent Files Tracking**: Quick access to your most recently used templates

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/faxmachine.git
```

2. Add the `src` directory to your PATH, or create a symlink to `faxmachine.sh` in a directory that's already in your PATH:
```bash
ln -s /path/to/faxmachine/src/faxmachine.sh /usr/local/bin/faxmachine
# Optional: Create shorter alias
ln -s /path/to/faxmachine/src/faxmachine.sh /usr/local/bin/fm
```

3. Make sure both scripts are executable:
```bash
chmod +x /path/to/faxmachine/src/faxmachine.sh
chmod +x /path/to/faxmachine/src/faxmachine.py
```

4. Initialize the database:
```bash
faxmachine init
```

5. (Optional) Add built-in templates to your faxmachine database:
```bash
./add_templates_to_faxmachine.sh
```

## Dependencies

- Python 3.6 or higher
- Bash shell
- Optional dependencies (automatically installed when needed):
  - NLTK, spaCy, or YAKE for intelligent keyword extraction
  - pdfplumber for PDF analysis
  - pygments for syntax highlighting

## Usage

### Interactive Mode

The easiest way to use Faxmachine is in interactive mode, which you can access by running `faxmachine` or `fm` with no arguments:

```bash
faxmachine
# or
fm
```

This presents a menu with options to:
1. Browse files (interactive mode)
2. Add a file to the database
3. Find and inject a file
4. Show recent files
5. List all files
6. Delete a file
7. Mass add files
8. File browser (with shortcuts & smart preview)
9. Show version
h. Help
q. Quit

### Interactive File Browser

The interactive file browser (`faxmachine browse`) offers a powerful way to navigate your templates:

- View files organized by category
- Navigate with cursor keys (j/k/h/l in Vim mode)
- Toggle file summaries with 'd'
- Select multiple files with space bar in multi-select mode
- Perform batch operations on selected files
- View smart previews of files before opening them
- Quick access to system shortcuts and recent files

### Common Commands

```bash
# Browse files with interactive browser
faxmachine browse

# Add a file to the database
faxmachine add path/to/your/file.txt

# Add a file with metadata
faxmachine add config.json --category config --description "My config template" --tags "json,config,template"

# Search for templates
faxmachine search gitignore

# Search in file contents as well
faxmachine search "import os" --content-search

# List all available templates
faxmachine list

# Inject a template into your current directory
faxmachine inject git/gitignore

# Show template contents
faxmachine show git/gitignore

# Show recently used templates
faxmachine recent

# Delete a template
faxmachine delete git/gitignore

# Mass add multiple files at once
faxmachine mass-add

# Smart document browsing with previews
faxmachine browser
```

## Detailed Command Reference

### add

```bash
faxmachine add [FILE] [--category CATEGORY] [--subcategory SUBCATEGORY] [--name NAME] [--description DESC] [--tags TAGS]
```

When adding files, Faxmachine offers smart content analysis that:
- Automatically extracts metadata from files (especially PDFs, CSVs, and JSON)
- Suggests descriptions based on file content
- Recommends tags based on content analysis
- Shows previews of content to help with organization

### search

```bash
faxmachine search [QUERY] [--content-search] [--tags TAGS] [--list-only] [--show-index INDEX] [--inject-index INDEX] [--delete-index INDEX]
```

The search command supports:
- Basic file name and description search
- Full-text content search with the `--content-search` flag
- Tag filtering to narrow down results
- Direct actions on search results without prompting

### inject

```bash
faxmachine inject [FILE] [--name NAME] [--no-preview]
```

When injecting files:
- Shows diff preview if overwriting existing files
- Option to rename files during injection
- Updates access history for quick access later

### browser

```bash
faxmachine browser [FILE]
```

The smart document browser provides:
- File system navigation with shortcuts
- Smart preview generation for files
- Automatic tag extraction
- Dropdown summaries of file content
- Multi-select capability for batch operations

### mass-add

```bash
faxmachine mass-add
```

For adding multiple files at once:
- Select destination category/subcategory
- Batch select files via dialog or manual input
- Apply common metadata to all files
- Smart content analysis for quick categorization

## Database Structure

Faxmachine stores your templates and metadata in the following locations:

```
~/.faxmachine/
│
├── db/                    # Main database directory containing actual files
│   ├── git/               # Example category
│   ├── python/            # Example category
│   ├── web/               # Example category
│   ├── config/            # Example category
│   └── other/             # Example category
│
├── metadata/              # Metadata storage directory
│   └── git_python-gitignore.json   # Example metadata file
│
├── config/                # Configuration directory
│   ├── config.json        # User configuration
│   └── cache/             # Cache directory
│
```

### Metadata Structure

Each file in the database has associated metadata stored as JSON with the following structure:

```json
{
  "description": "Description of the file",
  "source_path": "Original path when added",
  "added_date": "ISO format date when added",
  "tags": ["tag1", "tag2", "tag3"]
}
```

### Configuration

The main configuration file (`~/.faxmachine/config/config.json`) stores:

```json
{
  "version": "1.1.0",
  "aliases": {},
  "last_accessed": ["recently used file paths"],
  "settings": {
    "default_editor": "vi",
    "search_content": true,
    "preview_before_inject": true
  }
}
```

## Advanced Features

### Smart Document Analysis

Faxmachine includes intelligent document analysis capabilities:

1. **PDF Analysis**:
   - Extracts title, sections, and key topics
   - Identifies document type and purpose
   - Suggests tags based on content

2. **JSON Analysis**:
   - Identifies key structures and patterns
   - Extracts key fields for quick understanding
   - Recommends appropriate tags

3. **CSV Analysis**:
   - Identifies headers and data types
   - Provides row count and column summary
   - Suggests domain-specific tags

4. **Code Analysis**:
   - Identifies programming language
   - Extracts key identifiers and concepts
   - Suggests language-appropriate tags

### Vim-like Navigation

For users familiar with Vim, Faxmachine offers a Vim-like navigation mode in the browser:
- `j/k` to move up/down
- `h` to go to parent directory
- `l` to enter directory or view file
- `q` to exit Vim mode

### Multi-select Mode

The multi-select mode allows you to:
- Select multiple files with the space bar
- Perform batch operations (view, inject, add to database)
- Clear selections with 'c'
- Process selected files with 'a'

### Terminal UI

When available, Faxmachine uses a curses-based terminal UI for improved navigation and visualization, including:
- Color highlighting for better readability
- Dropdown summaries for quick information
- Visual selection indicators
- Directory tree visualization

## Use Cases

### Developer Workflows

1. **Project Bootstrapping**:
   - Store common project structures
   - Inject configuration files with one command
   - Maintain consistent project setups

2. **Configuration Management**:
   - Store configuration templates for different environments
   - Keep standardized config files for various services
   - Easily update configurations across projects

3. **Boilerplate Code**:
   - Store frequently used code patterns
   - Maintain language-specific utilities
   - Inject common functions and classes

4. **Documentation**:
   - Keep README templates
   - Store license files
   - Maintain consistent documentation formats

### DevOps Use Cases

1. **Infrastructure as Code**:
   - Store Terraform/CloudFormation templates
   - Maintain Docker/Kubernetes configurations
   - Organize deployment scripts

2. **CI/CD Templates**:
   - Store GitHub Actions workflows
   - Maintain Jenkins pipeline configurations
   - Keep standardized CI/CD setups

3. **Server Configurations**:
   - Store Nginx/Apache configurations
   - Maintain system initialization scripts
   - Keep monitoring configurations

### Team Collaboration

1. **Standardization**:
   - Maintain team-wide coding standards
   - Share common utilities and helpers
   - Ensure consistent project structures

2. **Onboarding**:
   - Provide new team members with standard templates
   - Share common project components
   - Enable quick access to team conventions

## Benefits

1. **Efficiency**:
   - Eliminate repetitive file creation
   - Reduce copy-paste errors
   - Streamline project setup and maintenance

2. **Consistency**:
   - Maintain standardized files across projects
   - Ensure all team members use the same templates
   - Reduce deviations from best practices

3. **Organization**:
   - Centralize all commonly used files
   - Categorize templates for easy access
   - Add metadata for better searchability

4. **Time Savings**:
   - Quick access to frequently used files
   - Reduce time spent recreating common structures
   - Batch operations for working with multiple files

5. **Smart Analysis**:
   - Automatic content understanding
   - Context-aware tag suggestions
   - File summarization for better organization

## Technical Implementation

Faxmachine is implemented as a combination of Python and Bash scripts:

1. **faxmachine.py**: The core Python implementation containing:
   - File management functions
   - Template database operations
   - Smart document analysis
   - Interactive browser implementation
   - Command processing logic

2. **faxmachine.sh**: A Bash wrapper providing:
   - Simple command line interface
   - Interactive menu for common operations
   - Input handling and environment setup
   - Python script execution

3. **db.py**: Database management module with:
   - Metadata handling functions
   - File storage operations
   - Search and retrieval logic
   - Category management

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 