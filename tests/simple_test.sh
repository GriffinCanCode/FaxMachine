#!/bin/bash

# Simple test script for Faxmachine
# Tests basic functionality directly with the Python script

# ANSI colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}${BLUE}====================================${NC}"
echo -e "${BOLD}${BLUE}    Faxmachine Simple Test    ${NC}"
echo -e "${BOLD}${BLUE}====================================${NC}"
echo ""

# Get the path to the Faxmachine Python script
SCRIPT_PATH="$(cd "$(dirname "$0")/.." && pwd)/src/faxmachine.py"
echo -e "${YELLOW}Testing script at: ${SCRIPT_PATH}${NC}"
echo ""

# Check if the script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo -e "${RED}Error: Script not found at $SCRIPT_PATH${NC}"
    exit 1
fi

# Make sure the script is executable
chmod +x "$SCRIPT_PATH"

# Create a temporary directory for testing
TEST_DIR=$(mktemp -d)
cd "$TEST_DIR" || exit 1
echo -e "${YELLOW}Testing in: $TEST_DIR${NC}"

# Test script version
echo -e "\n${BOLD}Testing version command:${NC}"
python3 "$SCRIPT_PATH" --version
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Version command works${NC}"
else
    echo -e "${RED}✗ Version command failed${NC}"
    exit 1
fi

# Initialize test directory
echo -e "\n${BOLD}Initializing database:${NC}"
python3 "$SCRIPT_PATH" init
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database initialized${NC}"
else
    echo -e "${RED}✗ Database initialization failed${NC}"
    exit 1
fi

# Create a test file
TEST_FILE="$TEST_DIR/test_file.txt"
echo "This is a test file for Faxmachine" > "$TEST_FILE"

# Add the test file
echo -e "\n${BOLD}Adding test file:${NC}"
python3 "$SCRIPT_PATH" add "$TEST_FILE" --category "test" --name "simple-test" --description "Simple test file"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ File added${NC}"
else
    echo -e "${RED}✗ Failed to add file${NC}"
    exit 1
fi

# Search for the file
echo -e "\n${BOLD}Searching for file:${NC}"
SEARCH_RESULT=$(python3 "$SCRIPT_PATH" search "simple-test" --list-only)
if [ $? -eq 0 ] && [[ "$SEARCH_RESULT" == *"simple-test"* ]]; then
    echo -e "${GREEN}✓ File found in search results${NC}"
else
    echo -e "${RED}✗ File not found in search results${NC}"
    echo "$SEARCH_RESULT"
    exit 1
fi

# Show file content
echo -e "\n${BOLD}Showing file content:${NC}"
python3 "$SCRIPT_PATH" show "test/simple-test"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ File content displayed${NC}"
else
    echo -e "${RED}✗ Failed to display file content${NC}"
    exit 1
fi

# Delete the file
echo -e "\n${BOLD}Deleting test file:${NC}"
python3 "$SCRIPT_PATH" delete "test/simple-test"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ File deleted${NC}"
else
    echo -e "${RED}✗ Failed to delete file${NC}"
    exit 1
fi

# Clean up
echo -e "\n${BOLD}Cleaning up:${NC}"
cd - > /dev/null
rm -rf "$TEST_DIR"
echo -e "${GREEN}✓ Temporary directory removed${NC}"

# Summary
echo -e "\n${BOLD}${GREEN}All tests passed!${NC}"
echo -e "${BOLD}${GREEN}Faxmachine is working correctly.${NC}"
exit 0 