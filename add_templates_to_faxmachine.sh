#!/bin/bash

# Colors for better output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}    Adding Templates to FaxMachine DB     ${NC}"
echo -e "${BLUE}===========================================${NC}"

# Function to add a template to faxmachine
add_to_faxmachine() {
  local file_path=$1
  local category=$2
  local description=$3
  local tags=$4
  
  echo -e "${YELLOW}Adding: ${file_path}${NC}"
  
  # Use the faxmachine.py script to add the file
  python src/faxmachine.py add "${file_path}" -c "${category}" -d "${description}" -t "${tags}"
  
  echo ""
}

echo -e "${BLUE}Checking if faxmachine database exists...${NC}"
# Initialize faxmachine if needed
if [ ! -d ~/.faxmachine/db ]; then
  echo -e "${YELLOW}Initializing faxmachine database...${NC}"
  python src/faxmachine.py init
fi

# Create categories for our templates
echo -e "${BLUE}Adding templates to faxmachine database...${NC}"
echo ""

# React templates
add_to_faxmachine "templates/react/Component.tsx" "react" "React functional component template with TypeScript" "react,typescript,component,frontend"
add_to_faxmachine "templates/react/useCustomHook.ts" "react" "React custom hook template with TypeScript" "react,typescript,hook,frontend"

# Python templates
add_to_faxmachine "templates/python/model.py" "python" "SQLAlchemy model template" "python,sqlalchemy,model,backend"
add_to_faxmachine "templates/python/flask_route.py" "python" "Flask route blueprint template" "python,flask,route,api,backend"

# FastAPI templates
add_to_faxmachine "templates/fastapi/router.py" "python/fastapi" "FastAPI router template" "python,fastapi,router,api,backend"

# Vue templates
add_to_faxmachine "templates/vue/Component.vue" "vue" "Vue component template" "vue,component,frontend"

# Next.js templates
add_to_faxmachine "templates/nextjs/page.tsx" "nextjs" "Next.js page template with TypeScript" "react,nextjs,typescript,page,frontend"

echo -e "${GREEN}All templates have been added to the faxmachine database.${NC}"
echo -e "${BLUE}You can now use them with:${NC}"
echo "  python src/faxmachine.py search <template-name>"
echo "  python src/faxmachine.py browse"
echo "" 