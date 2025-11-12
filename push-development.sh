#!/bin/bash

# Vacasa Home Assistant Integration Deployment Script
#
# Setup Instructions:
# 1. Copy .env.example to .env: cp .env.example .env
# 2. Edit .env with your Home Assistant server details
# 3. Run this script: ./new-prod-release.sh
#
# Alternatively, set environment variables:
# export HA_SERVER_IP="192.168.1.67"
# export HA_SERVER_USER="root"
# export HA_CONFIG_DIR="/homeassistant"

# Load configuration from .env file if it exists
if [ -f .env ]; then
    echo "Loading configuration from .env file..."
    source .env
fi

# Configuration with environment variable fallbacks
SERVER_IP="${HA_SERVER_IP:-${SERVER_IP}}"
SERVER_USER="${HA_SERVER_USER:-${SERVER_USER}}"
HA_CONFIG_DIR="${HA_CONFIG_DIR:-/homeassistant}"

# Validate required configuration
if [ -z "$SERVER_IP" ]; then
    echo "❌ Error: HA_SERVER_IP not configured"
    echo "Please either:"
    echo "  1. Copy .env.example to .env and edit it"
    echo "  2. Set environment variable: export HA_SERVER_IP=your.server.ip"
    exit 1
fi

if [ -z "$SERVER_USER" ]; then
    echo "❌ Error: HA_SERVER_USER not configured"
    echo "Please either:"
    echo "  1. Copy .env.example to .env and edit it"
    echo "  2. Set environment variable: export HA_SERVER_USER=root"
    exit 1
fi

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏠 Deploying Vacasa integration to Home Assistant server...${NC}"
echo -e "${BLUE}Server: ${SERVER_USER}@${SERVER_IP}${NC}"
echo -e "${BLUE}Config Directory: ${HA_CONFIG_DIR}${NC}"
echo ""

# Test SSH connection first
echo "Testing SSH connection..."
if ! ssh -o ConnectTimeout=10 ${SERVER_USER}@${SERVER_IP} "echo 'SSH connection successful'" > /dev/null 2>&1; then
    echo -e "${RED}❌ Failed to connect to ${SERVER_IP}${NC}"
    echo "Please check:"
    echo "  - Server is running and accessible"
    echo "  - SSH credentials are correct"
    echo "  - Network connectivity"
    echo "  - Configuration in .env file"
    exit 1
fi
echo -e "${GREEN}✅ SSH connection successful${NC}"

# Create the destination directory if it doesn't exist
echo "Creating destination directory..."
ssh ${SERVER_USER}@${SERVER_IP} "mkdir -p ${HA_CONFIG_DIR}/custom_components"

# Remove existing Vacasa files if they exist
echo "Removing any existing Vacasa files..."
ssh ${SERVER_USER}@${SERVER_IP} "rm -rf ${HA_CONFIG_DIR}/custom_components/vacasa"

# Copy the custom component
echo "Copying files to server..."
scp -r custom_components/vacasa ${SERVER_USER}@${SERVER_IP}:${HA_CONFIG_DIR}/custom_components/

# Check if the copy was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Deployment successful!${NC}"

    # Automatically restart Home Assistant to apply changes
    echo ""
    echo "Restarting Home Assistant to apply changes..."
    ssh ${SERVER_USER}@${SERVER_IP} "ha core restart"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Home Assistant restart initiated successfully!${NC}"
        echo "Home Assistant will be available again shortly."
        echo ""
        echo -e "${YELLOW}💡 Tip: Use './logs.sh live' to monitor the restart process${NC}"
    else
        echo -e "${RED}❌ Failed to restart Home Assistant.${NC}"
        echo "Please restart Home Assistant manually to apply changes."
    fi

    echo ""
    echo -e "${GREEN}🎉 Integration deployment completed!${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Configure the integration in Home Assistant"
    echo "  2. Monitor logs: ./logs.sh recent"
    echo "  3. Check for errors: ./logs.sh errors"

else
    echo -e "${RED}❌ Deployment failed!${NC}"
    echo "Please check the error messages above and try again."
    exit 1
fi
