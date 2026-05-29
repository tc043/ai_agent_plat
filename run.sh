#!/usr/bin/env bash

# AI Agent Platform Startup Script
# Set up a Python virtual environment, install dependencies, and run the FastAPI server.

# Exit immediately if a command exits with a non-zero status
set -e

# Define colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0;37m' # No Color

echo -e "${BLUE}=== AI Agent Platform & Sandbox Startup ===${NC}"

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed or not in PATH.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "Found Python ${GREEN}${PYTHON_VERSION}${NC}"

# Define virtual environment directory
VENV_DIR=".venv"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Creating virtual environment in $VENV_DIR...${NC}"
    
    # Try standard python3 -m venv first
    if python3 -m venv "$VENV_DIR" >/dev/null 2>&1; then
        echo -e "${GREEN}Virtual environment created via python3 -m venv.${NC}"
    else
        echo -e "${YELLOW}Standard python3 -m venv failed (ensurepip issue). Falling back to virtualenv...${NC}"
        
        # Install virtualenv using pip3 if not available
        if ! command -v virtualenv &> /dev/null && [ ! -f "$HOME/.local/bin/virtualenv" ]; then
            echo -e "${YELLOW}Installing virtualenv package under user directory...${NC}"
            pip3 install --user virtualenv >/dev/null 2>&1 || true
        fi
        
        # Determine virtualenv executable path
        VIRTUALENV_CMD="virtualenv"
        if [ -f "$HOME/.local/bin/virtualenv" ]; then
            VIRTUALENV_CMD="$HOME/.local/bin/virtualenv"
        fi
        
        # Run virtualenv creation
        if $VIRTUALENV_CMD "$VENV_DIR"; then
            echo -e "${GREEN}Virtual environment created via virtualenv.${NC}"
        else
            echo -e "${RED}Error: Failed to create virtual environment using both venv and virtualenv.${NC}"
            exit 1
        fi
    fi
else
    echo -e "Using existing virtual environment ${GREEN}$VENV_DIR${NC}"
fi

# Activate virtual environment
echo -e "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install/upgrade dependencies
echo -e "${YELLOW}Installing/updating requirements...${NC}"
pip install --upgrade pip
pip install -r backend/requirements.txt

# Run FastAPI app
echo -e "${GREEN}Starting FastAPI server on http://localhost:8000 ...${NC}"
echo -e "${BLUE}Press Ctrl+C to stop the server.${NC}"

# Run FastAPI via backend.main
python3 -m backend.main
