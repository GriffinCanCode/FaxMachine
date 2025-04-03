#!/bin/bash

# Faxmachine - File Template Manager
# Bash script wrapper for the faxmachine.py Python script

# ANSI colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Determine script location and Python script path, handling symlinks (macOS compatible)
get_script_path() {
    local source="${BASH_SOURCE[0]}"
    while [ -L "$source" ]; do # resolve $source until the file is no longer a symlink
        local dir="$( cd -P "$( dirname "$source" )" && pwd )"
        source="$(readlink "$source")"
        [[ $source != /* ]] && source="$dir/$source" # if $source was a relative symlink, we need to resolve it relative to the path where the symlink file was located
    done
    echo "$( cd -P "$( dirname "$source" )" && pwd )"
}

SCRIPT_DIR="$(get_script_path)"
PYTHON_SCRIPT="${SCRIPT_DIR}/faxmachine.py"

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "${RED}Error: Python script not found at ${PYTHON_SCRIPT}${NC}"
    echo -e "Make sure both faxmachine.sh and faxmachine.py are in the same directory."
    exit 1
fi

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed.${NC}"
    exit 1
fi

# Check if Python script is executable
if [ ! -x "$PYTHON_SCRIPT" ]; then
    echo -e "${YELLOW}Making Python script executable...${NC}"
    chmod +x "$PYTHON_SCRIPT"
fi

# Interactive mode (no arguments passed)
if [ $# -eq 0 ]; then
    clear
    echo -e "${BOLD}${BLUE}=======================================${NC}"
    echo -e "${BOLD}${BLUE}    Faxmachine - File Template Manager    ${NC}"
    echo -e "${BOLD}${BLUE}=======================================${NC}"
    echo ""
    echo -e "${BOLD}Select an option:${NC}"
    echo -e "1. ${CYAN}Browse files${NC} (interactive mode)"
    echo -e "2. ${CYAN}Add a file${NC} to the database"
    echo -e "3. ${CYAN}Find and inject${NC} a file"
    echo -e "4. ${CYAN}Show recent files${NC}"
    echo -e "5. ${CYAN}List all files${NC}"
    echo -e "6. ${CYAN}Delete a file${NC}"
    echo -e "7. ${CYAN}Show version${NC}"
    echo -e "h. ${CYAN}Help${NC}"
    echo -e "q. ${CYAN}Quit${NC}"
    echo ""
    read -p "Enter choice: " choice
    echo ""
    
    case $choice in
        1) python3 "$PYTHON_SCRIPT" browse ;;
        2) 
            read -p "Enter path to file: " file_path
            read -p "Enter category (leave blank to select interactively): " category
            
            if [ -z "$category" ]; then
                python3 "$PYTHON_SCRIPT" add "$file_path"
            else
                read -p "Enter subcategory (optional): " subcategory
                read -p "Enter name for file (leave blank for original filename): " name
                read -p "Enter description (optional): " description
                
                args=("add" "$file_path" "--category" "$category")
                
                if [ ! -z "$subcategory" ]; then
                    args+=("--subcategory" "$subcategory")
                fi
                
                if [ ! -z "$name" ]; then
                    args+=("--name" "$name")
                fi
                
                if [ ! -z "$description" ]; then
                    args+=("--description" "$description")
                fi
                
                python3 "$PYTHON_SCRIPT" "${args[@]}"
            fi
            ;;
        3) 
            read -p "Enter search term: " query
            
            if [ -z "$query" ]; then
                echo -e "${RED}Search term cannot be empty${NC}"
                exit 1
            fi
            
            # First show search results
            echo -e "${BOLD}Search results for '${query}':${NC}"
            results=$(python3 "$PYTHON_SCRIPT" search "$query" --list-only)
            
            if [ $? -ne 0 ] || [ -z "$results" ]; then
                echo -e "${YELLOW}No results found for '$query'${NC}"
                exit 0
            fi
            
            echo "$results"
            echo ""
            
            # Ask user to select a file
            read -p "Enter file number to inject, v+number to view, or q to quit: " choice
            
            if [ "$choice" == "q" ]; then
                exit 0
            elif [[ "$choice" =~ ^v[0-9]+$ ]]; then
                # View file
                number=${choice:1}
                python3 "$PYTHON_SCRIPT" search "$query" --show-index "$number"
                
                # After viewing, ask if they want to inject
                read -p "Inject this file? (y/n): " inject_choice
                if [ "$inject_choice" == "y" ]; then
                    read -p "Enter destination filename (leave blank for original): " dest_name
                    python3 "$PYTHON_SCRIPT" search "$query" --inject-index "$number" ${dest_name:+--name "$dest_name"}
                fi
            elif [[ "$choice" =~ ^[0-9]+$ ]]; then
                # Inject file
                read -p "Enter destination filename (leave blank for original): " dest_name
                python3 "$PYTHON_SCRIPT" search "$query" --inject-index "$choice" ${dest_name:+--name "$dest_name"}
            else
                echo -e "${RED}Invalid choice${NC}"
                exit 1
            fi
            ;;
        4) python3 "$PYTHON_SCRIPT" recent ;;
        5) python3 "$PYTHON_SCRIPT" list ;;
        6)
            echo -e "${BOLD}Select a file to delete:${NC}"
            read -p "Enter search term: " query
            
            if [ -z "$query" ]; then
                echo -e "${RED}Search term cannot be empty${NC}"
                exit 1
            fi
            
            # Show search results
            results=$(python3 "$PYTHON_SCRIPT" search "$query" --list-only)
            
            if [ $? -ne 0 ] || [ -z "$results" ]; then
                echo -e "${YELLOW}No results found for '$query'${NC}"
                exit 0
            fi
            
            echo "$results"
            echo ""
            
            # Ask user to select a file to delete
            read -p "Enter file number to delete or q to quit: " choice
            
            if [ "$choice" == "q" ]; then
                exit 0
            elif [[ "$choice" =~ ^[0-9]+$ ]]; then
                # Confirm deletion
                read -p "Are you sure you want to delete this file? (y/n): " confirm
                if [ "$confirm" == "y" ]; then
                    python3 "$PYTHON_SCRIPT" search "$query" --delete-index "$choice"
                else
                    echo -e "${YELLOW}Deletion cancelled${NC}"
                fi
            else
                echo -e "${RED}Invalid choice${NC}"
                exit 1
            fi
            ;;
        7) python3 "$PYTHON_SCRIPT" --version ;;
        h) python3 "$PYTHON_SCRIPT" --detailed-help ;;
        q) exit 0 ;;
        *) 
            echo -e "${RED}Invalid choice${NC}"
            exit 1
            ;;
    esac
else
    # Pass all arguments to the Python script
    python3 "$PYTHON_SCRIPT" "$@"
fi