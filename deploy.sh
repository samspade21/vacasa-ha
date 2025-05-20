#!/bin/bash

# Configuration
SERVER_IP="192.168.1.67"
SERVER_USER="root"
HA_CONFIG_DIR="/homeassistant"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo "Deploying Vacasa integration to Home Assistant server..."

# Create the destination directory if it doesn't exist
ssh ${SERVER_USER}@${SERVER_IP} "mkdir -p ${HA_CONFIG_DIR}/custom_components"

# Remove existing Vacasa files if they exist
echo "Removing any existing Vacasa files..."
ssh ${SERVER_USER}@${SERVER_IP} "rm -rf ${HA_CONFIG_DIR}/custom_components/vacasa"

# Copy the custom component
echo "Copying files to server..."
scp -r custom_components/vacasa ${SERVER_USER}@${SERVER_IP}:${HA_CONFIG_DIR}/custom_components/

# Check if the copy was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Deployment successful!${NC}"

    # Restart Home Assistant
    echo "Restarting Home Assistant..."
    ssh ${SERVER_USER}@${SERVER_IP} "ha core restart"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Home Assistant restart initiated successfully!${NC}"
        echo "Home Assistant will be available again shortly."
    else
        echo -e "${RED}Failed to restart Home Assistant.${NC}"
        echo "Please restart Home Assistant manually to apply changes."
    fi
else
    echo -e "${RED}Deployment failed!${NC}"
    exit 1
fi
