# FaxMachine Code Templates

This directory contains code templates for various frameworks and technologies. These templates are designed to follow best practices and coding standards as defined in the MDC files.

## Available Templates

- **react**: Templates for React components and hooks
- **python**: Templates for Python code, including Flask routes and SQLAlchemy models
- **vue**: Templates for Vue.js components
- **nextjs**: Templates for Next.js pages and components
- **fastapi**: Templates for FastAPI routes and services

## How to Use

You can use these templates in three ways:

### 1. Using with faxmachine.py (Recommended)

The templates can be added to the faxmachine.py database, which allows you to search, browse, and inject templates easily.

To add all templates to the faxmachine database:

```bash
./add_templates_to_faxmachine.sh
```

Then you can use them with the faxmachine.py commands:

```bash
# Browse all templates interactively
python src/faxmachine.py browse

# Search for a specific template
python src/faxmachine.py search react

# Inject a template into your current directory
python src/faxmachine.py inject react/Component.tsx

# Show contents of a template
python src/faxmachine.py show python/model.py
```

### 2. Using the setup script

Run the setup script to copy templates to your project directory:

```bash
./setup_templates.sh
```

Follow the interactive prompts to select a template type and specify the target directory.

### 3. Manual copying

You can also manually copy template files to your project directory:

```bash
cp templates/react/Component.tsx your_project/components/
```

## Template Structure

Each template directory contains files that follow best practices for that specific framework or technology. The templates are based on the MDC (Machine-Directed Coding) files that define coding standards.

## Customizing Templates

Feel free to customize these templates to better suit your project's needs. To create new templates, simply add new files to the appropriate template directory.

To add a new template to the faxmachine database:

```bash
python src/faxmachine.py add path/to/your/template.ext -c category -d "Description" -t "tag1,tag2"
```

## Contributing

To contribute new templates:

1. Create a new directory under `templates/` for a new framework or add files to an existing directory
2. Ensure your template follows best practices as defined in the corresponding MDC file
3. Update this README.md with information about your new template
4. Add your template to faxmachine by running `./add_templates_to_faxmachine.sh` or manually using the faxmachine.py add command

## License

These templates are provided as-is under the MIT license. 