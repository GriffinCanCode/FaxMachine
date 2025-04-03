#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting GPG setup for Git signing...${NC}"

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo -e "${RED}Homebrew is not installed. Please install Homebrew first.${NC}"
    echo "Visit https://brew.sh for installation instructions."
    exit 1
fi

# Install pinentry-mac if not already installed
if ! brew list pinentry-mac &> /dev/null; then
    echo -e "${YELLOW}Installing pinentry-mac...${NC}"
    brew install pinentry-mac
fi

# Create .gnupg directory if it doesn't exist
mkdir -p ~/.gnupg
chmod 700 ~/.gnupg

# Configure GPG agent
echo -e "${YELLOW}Configuring GPG agent...${NC}"
echo "pinentry-program /opt/homebrew/bin/pinentry-mac" > ~/.gnupg/gpg-agent.conf
chmod 600 ~/.gnupg/gpg-agent.conf

# Restart GPG agent
echo -e "${YELLOW}Restarting GPG agent...${NC}"
gpgconf --kill gpg-agent
gpg-agent --daemon

# Check if GPG key exists
if ! gpg --list-secret-keys --keyid-format=long | grep -q "sec"; then
    echo -e "${RED}No GPG key found.${NC}"
    echo -e "${YELLOW}Would you like to generate a new GPG key? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Generating new GPG key...${NC}"
        gpg --full-generate-key
    else
        echo -e "${RED}Please generate a GPG key manually using 'gpg --full-generate-key'${NC}"
        exit 1
    fi
fi

# Get the GPG key ID
GPG_KEY_ID=$(gpg --list-secret-keys --keyid-format=long | grep "sec" | head -n 1 | awk '{print $2}' | cut -d'/' -f2)

# Configure Git to use GPG signing
echo -e "${YELLOW}Configuring Git to use GPG signing...${NC}"
git config --global user.signingkey "$GPG_KEY_ID"
git config --global commit.gpgsign true

# Export GPG key for GitHub
echo -e "${YELLOW}Exporting GPG public key...${NC}"
echo -e "${GREEN}Your GPG public key (copy this and add it to GitHub):${NC}"
gpg --armor --export "$GPG_KEY_ID"

echo -e "${GREEN}Setup complete!${NC}"
echo -e "${YELLOW}Please add the exported GPG key to your GitHub account:${NC}"
echo "1. Go to GitHub Settings"
echo "2. Click on 'SSH and GPG keys'"
echo "3. Click 'New GPG key'"
echo "4. Paste the key above and save" 