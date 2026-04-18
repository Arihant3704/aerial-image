#!/bin/bash

# DJI Aerial Georeferencing Startup Script
# This script automates the setup and execution of the project.

# Colors for logging
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}--- Starting DJI Aerial Georeferencing Setup ---${NC}"

# 1. Check for Node.js dependencies
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}Installing dependencies...${NC}"
    npm install
else
    echo -e "${GREEN}Dependencies already installed.${NC}"
fi

# 2. Build the project
# We use build:prod for a clean first start
echo -e "${BLUE}Performing initial production build...${NC}"
npm run build:prod

if [ $? -ne 0 ]; then
    echo -e "\033[0;31mBuild failed. Please check the logs above.\033[0m"
    exit 1
fi

# 3. Start the local server and the watcher in parallel
echo -e "${GREEN}Build successful! Launching local server and development watcher...${NC}"

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${BLUE}Stopping project...${NC}"
    kill $WATCHER_PID $SERVER_PID
    exit
}

trap cleanup SIGINT SIGTERM

# Start the Webpack watcher for development
npm run build:dev &
WATCHER_PID=$!

# Start the local server on port 3000
npx serve dist &
SERVER_PID=$!

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}  Project is running at: http://localhost:3000 ${NC}"
echo -e "${GREEN}  (Press Ctrl+C to stop)                       ${NC}"
echo -e "${GREEN}===============================================${NC}"

# Keep script running
wait
