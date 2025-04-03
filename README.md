# Faxmachine - File Template Manager

Faxmachine is a powerful utility for storing, organizing, and injecting commonly used files and templates across your projects.

## Features

- **Simple Command Line Interface**: Easy to use commands for managing your file templates
- **Interactive Browser**: Navigate your template collection with a user-friendly interface
- **Smart Search**: Find templates by filename, contents, tags, or description
- **File Preview**: See what you're getting before injecting files
- **Metadata Support**: Add descriptions and tags to better organize your templates
- **Category Organization**: Keep templates neatly arranged in categories and subcategories
- **Built-in Templates**: Comes with pre-built templates for React, Python, Vue, Next.js, and FastAPI

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

## Usage

### Interactive Mode

The easiest way to use Faxmachine is in interactive mode, which you can access by running `faxmachine` or `fm` with no arguments:

```bash
faxmachine
# or
fm
```

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
```

## Database Structure

Faxmachine stores your templates in `~/.faxmachine/db/` organized in categories. Metadata is stored in `~/.faxmachine/metadata/`.

## Built-in Templates

Faxmachine comes with pre-built templates for various frameworks and languages:

- **React**: Component and custom hook templates
- **Python**: SQLAlchemy models and Flask routes
- **FastAPI**: Router templates
- **Vue**: Component templates
- **Next.js**: Page templates

To use these templates:

1. Add them to your faxmachine database:
```bash
./add_templates_to_faxmachine.sh
```

2. Browse and use them:
```bash
faxmachine search react
faxmachine inject react/Component.tsx
```

For more information about the built-in templates, see the [templates/README.md](templates/README.md).

## Advanced Usage

### Tags

Tags can be added to templates for better organization and easier searching:

```bash
faxmachine add myfile.txt --tags "important,example,reference"
```

You can then search by tags:

```bash
faxmachine search reference --tags "important"
```

### File Preview

Before injecting a file, Faxmachine can show a preview, including a diff if you're overwriting an existing file:

```bash
faxmachine inject config/package.json
```

### Configuration

Faxmachine configuration is stored in `~/.faxmachine/config.json`. You can edit this file to customize behavior.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 