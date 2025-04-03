#!/bin/bash

# Faxmachine Test Script
# This script tests the basic functionality of the Faxmachine system

# ANSI colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Clear screen and print header
clear
echo -e "${BOLD}${BLUE}    Faxmachine Test Suite    ${NC}"
echo

# Create a temporary directory for testing
TEST_DIR=$(mktemp -d)
echo "Created temporary test directory: $TEST_DIR"
cd "$TEST_DIR" || { echo "Could not change to temporary directory"; exit 1; }

# Find the Faxmachine scripts - use the current working directory before changing to temp dir
ORIGINAL_DIR=$(pwd)

# Try to find the Faxmachine script
if [ -f "$ORIGINAL_DIR/src/faxmachine.sh" ]; then
    FAXMACHINE_SCRIPT="$ORIGINAL_DIR/src/faxmachine.sh"
    echo "Found script at: $FAXMACHINE_SCRIPT"
elif command -v faxmachine &> /dev/null; then
    FAXMACHINE_SCRIPT="faxmachine"
    echo "Using command: $FAXMACHINE_SCRIPT"
else
    echo -e "${RED}Error: Faxmachine script not found${NC}"
    echo "Make sure you run this test from the Faxmachine project root directory."
    exit 1
fi

# Test 1: Check if Faxmachine is runnable
echo -e "${BOLD}Test 1:${NC} Checking if Faxmachine is runnable"
$FAXMACHINE_SCRIPT --version
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Faxmachine is runnable${NC}"
else
    echo -e "${RED}✗ Faxmachine is not runnable${NC}"
    exit 1
fi

# Test 2: Initialize the database
echo -e "\n${BOLD}Test 2:${NC} Initializing the database"
$FAXMACHINE_SCRIPT init
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database initialized${NC}"
else
    echo -e "${RED}✗ Database initialization failed${NC}"
    exit 1
fi

# Test 3: Add a file
echo -e "\n${BOLD}Test 3:${NC} Adding a file"
echo "This is a test file for Faxmachine" > test_file.txt
$FAXMACHINE_SCRIPT add test_file.txt --category test --name test-file --description "Test file" --tags "test,example"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ File added${NC}"
else
    echo -e "${RED}✗ Failed to add file${NC}"
    exit 1
fi

# Test 4: Search for the file
echo -e "\n${BOLD}Test 4:${NC} Searching for the file"
SEARCH_RESULT=$($FAXMACHINE_SCRIPT search test --list-only)
if [ $? -eq 0 ] && [[ "$SEARCH_RESULT" == *"test-file"* ]]; then
    echo -e "${GREEN}✓ File found in search results${NC}"
    echo "$SEARCH_RESULT"
else
    echo -e "${RED}✗ File not found in search results${NC}"
    exit 1
fi

# Test 5: Inject the file
echo -e "\n${BOLD}Test 5:${NC} Injecting the file"
rm test_file.txt  # Remove original
$FAXMACHINE_SCRIPT inject test/test-file --no-preview
if [ $? -eq 0 ] && [ -f "test-file" ]; then
    echo -e "${GREEN}✓ File injected successfully${NC}"
else
    echo -e "${RED}✗ File injection failed${NC}"
    exit 1
fi

# Test 6: Delete the file from database
echo -e "\n${BOLD}Test 6:${NC} Deleting the file from database"
$FAXMACHINE_SCRIPT delete test/test-file
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ File deleted from database${NC}"
else
    echo -e "${RED}✗ Failed to delete file from database${NC}"
    exit 1
fi

# Clean up
echo -e "\n${BOLD}Cleaning up...${NC}"
cd "$ORIGINAL_DIR" || { echo "Could not return to original directory"; exit 1; }
rm -rf "$TEST_DIR"
echo "Removed temporary directory"

# Final results
echo -e "\n${BOLD}Test Results:${NC}"
echo -e "${BOLD}${GREEN}Faxmachine is working correctly.${NC}"
exit 0 