#!/bin/bash

# Vacasa Home Assistant Integration Log Viewer
#
# Setup Instructions:
# 1. Copy .env.example to .env: cp .env.example .env
# 2. Edit .env with your Home Assistant server details
# 3. Run this script: ./logs.sh [command]
#
# Alternatively, set environment variables:
# export HA_SERVER_IP="192.168.1.67"
# export HA_SERVER_USER="root"
# export HA_CONFIG_DIR="/homeassistant"

# Load configuration from .env file if it exists
if [ -f .env ]; then
    source .env
fi

# Configuration with environment variable fallbacks
SERVER_IP="${HA_SERVER_IP:-${SERVER_IP}}"
SERVER_USER="${HA_SERVER_USER:-${SERVER_USER}}"
HA_CONFIG_DIR="${HA_CONFIG_DIR:-/homeassistant}"
HA_LOG_FILE="${HA_CONFIG_DIR}/home-assistant.log"

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
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to check SSH connection
check_connection() {
    echo -e "${BLUE}Checking connection to Home Assistant server...${NC}"
    echo -e "${BLUE}Server: ${SERVER_USER}@${SERVER_IP}${NC}"
    echo -e "${BLUE}Log File: ${HA_LOG_FILE}${NC}"
    echo ""

    if ! ssh -o ConnectTimeout=5 ${SERVER_USER}@${SERVER_IP} "echo 'Connected'" > /dev/null 2>&1; then
        echo -e "${RED}❌ Failed to connect to ${SERVER_IP}${NC}"
        echo "Please check:"
        echo "  - Server is running and accessible"
        echo "  - SSH credentials are correct"
        echo "  - Network connectivity"
        echo "  - Configuration in .env file"
        exit 1
    fi
    echo -e "${GREEN}✅ Connected to Home Assistant server${NC}"
}

# Function to show recent Vacasa logs
show_recent_logs() {
    echo -e "${CYAN}📋 Recent Vacasa Integration Logs (last 50 lines)${NC}"
    echo "=================================================="
    ssh ${SERVER_USER}@${SERVER_IP} "tail -200 ${HA_LOG_FILE} | grep -i vacasa | tail -50" 2>/dev/null || {
        echo -e "${RED}❌ Error retrieving logs${NC}"
        return 1
    }
}

# Function to monitor live logs
monitor_live_logs() {
    echo -e "${CYAN}🔴 Live Vacasa Log Monitoring (Press Ctrl+C to stop)${NC}"
    echo "====================================================="
    echo -e "${YELLOW}Monitoring for Vacasa integration activity...${NC}"
    ssh ${SERVER_USER}@${SERVER_IP} "tail -f ${HA_LOG_FILE} | grep --line-buffered -i vacasa" 2>/dev/null || {
        echo -e "${RED}❌ Error starting live monitoring${NC}"
        return 1
    }
}

# Function to show debug logs only
show_debug_logs() {
    echo -e "${CYAN}🐛 Vacasa Debug Logs (last 30 lines)${NC}"
    echo "======================================"
    ssh ${SERVER_USER}@${SERVER_IP} "grep -i 'vacasa.*debug\|custom_components.vacasa.*debug' ${HA_LOG_FILE} | tail -30" 2>/dev/null || {
        echo -e "${RED}❌ Error retrieving debug logs${NC}"
        echo -e "${YELLOW}💡 Tip: Make sure debug logging is enabled in configuration.yaml${NC}"
        return 1
    }
}

# Function to show error logs only
show_error_logs() {
    echo -e "${CYAN}❌ Vacasa Error Logs (last 20 lines)${NC}"
    echo "===================================="
    ssh ${SERVER_USER}@${SERVER_IP} "grep -i 'vacasa.*error\|custom_components.vacasa.*error\|config_flow.*error\|500.*error' ${HA_LOG_FILE} | tail -20" 2>/dev/null || {
        echo -e "${RED}❌ Error retrieving error logs${NC}"
        return 1
    }
}

# Function to show config flow specific errors
show_config_flow_errors() {
    echo -e "${CYAN}⚙️ Config Flow Error Logs (last 30 lines)${NC}"
    echo "=========================================="
    ssh ${SERVER_USER}@${SERVER_IP} "grep -i 'config_flow\|flow.*error\|500.*error\|internal.*server.*error\|traceback\|exception' ${HA_LOG_FILE} | tail -30" 2>/dev/null || {
        echo -e "${RED}❌ Error retrieving config flow logs${NC}"
        return 1
    }
}

# Function to show import/module errors
show_import_errors() {
    echo -e "${CYAN}📦 Import/Module Error Logs (last 25 lines)${NC}"
    echo "============================================="
    ssh ${SERVER_USER}@${SERVER_IP} "grep -i 'import.*error\|module.*error\|cannot.*import\|no.*module\|typealias\|typing_extensions' ${HA_LOG_FILE} | tail -25" 2>/dev/null || {
        echo -e "${RED}❌ Error retrieving import error logs${NC}"
        return 1
    }
}

# Function to show Python/syntax errors
show_syntax_errors() {
    echo -e "${CYAN}🐍 Python Syntax Error Logs (last 25 lines)${NC}"
    echo "=============================================="
    ssh ${SERVER_USER}@${SERVER_IP} "grep -i 'syntax.*error\|invalid.*syntax\|python.*error\|traceback.*most.*recent' ${HA_LOG_FILE} | tail -25" 2>/dev/null || {
        echo -e "${RED}❌ Error retrieving syntax error logs${NC}"
        return 1
    }
}

# Function to show calendar-specific logs
show_calendar_logs() {
    echo -e "${CYAN}📅 Calendar Entity Related Logs (last 40 lines)${NC}"
    echo "==============================================="
    ssh ${SERVER_USER}@${SERVER_IP} "grep -i 'calendar.*vacasa\|vacasa.*calendar\|calendar.*mountain.*view\|binary_sensor.*vacasa' ${HA_LOG_FILE} | tail -40" 2>/dev/null || {
        echo -e "${RED}❌ Error retrieving calendar logs${NC}"
        return 1
    }
}

# Function to show entity registry logs
show_entity_logs() {
    echo -e "${CYAN}🏷️ Entity Registration Logs (last 30 lines)${NC}"
    echo "==========================================="
    ssh ${SERVER_USER}@${SERVER_IP} "grep -i 'vacasa.*entity\|entity.*vacasa\|Found.*calendar\|Searching.*calendar' ${HA_LOG_FILE} | tail -30" 2>/dev/null || {
        echo -e "${RED}❌ Error retrieving entity logs${NC}"
        return 1
    }
}

# Function to show startup logs
show_startup_logs() {
    echo -e "${CYAN}🚀 Integration Startup Logs (last 50 lines)${NC}"
    echo "============================================"
    ssh ${SERVER_USER}@${SERVER_IP} "grep -i 'vacasa.*setup\|setup.*vacasa\|Found.*units\|async_setup_entry' ${HA_LOG_FILE} | tail -50" 2>/dev/null || {
        echo -e "${RED}❌ Error retrieving startup logs${NC}"
        return 1
    }
}

# Function for custom search
custom_search() {
    echo -e "${CYAN}🔍 Custom Log Search${NC}"
    echo "==================="
    echo -n "Enter search pattern: "
    read -r pattern
    if [ -n "$pattern" ]; then
        echo -e "${YELLOW}Searching for: ${pattern}${NC}"
        ssh ${SERVER_USER}@${SERVER_IP} "grep -i '${pattern}' ${HA_LOG_FILE} | tail -30" 2>/dev/null || {
            echo -e "${RED}❌ Error performing search${NC}"
            return 1
        }
    else
        echo -e "${RED}❌ No search pattern provided${NC}"
    fi
}

# Function to show current status
show_status() {
    echo -e "${CYAN}📊 Current System Status${NC}"
    echo "========================"

    echo -e "${BLUE}Home Assistant Core:${NC}"
    ssh ${SERVER_USER}@${SERVER_IP} "ha core info" 2>/dev/null | grep -E "(version|state)" || echo "Unable to get HA status"

    echo -e "\n${BLUE}Recent Integration Activity:${NC}"
    ssh ${SERVER_USER}@${SERVER_IP} "tail -50 ${HA_LOG_FILE} | grep -i vacasa | tail -5" 2>/dev/null || echo "No recent Vacasa activity"

    echo -e "\n${BLUE}Log File Size:${NC}"
    ssh ${SERVER_USER}@${SERVER_IP} "ls -lh ${HA_LOG_FILE}" 2>/dev/null | awk '{print $5, $9}' || echo "Unable to check log size"
}

# Function to show help
show_help() {
    echo -e "${CYAN}📖 Log Viewer Help${NC}"
    echo "=================="
    echo "This script provides easy access to Home Assistant logs for debugging"
    echo "the Vacasa integration."
    echo ""
    echo -e "${YELLOW}Quick Commands:${NC}"
    echo "  ./logs.sh recent    - Show recent Vacasa logs"
    echo "  ./logs.sh live      - Monitor live logs"
    echo "  ./logs.sh errors    - Show error logs only"
    echo "  ./logs.sh debug     - Show debug logs only"
    echo "  ./logs.sh calendar  - Show calendar-related logs"
    echo ""
    echo -e "${YELLOW}Setup:${NC}"
    echo "  1. Copy .env.example to .env"
    echo "  2. Edit .env with your server details"
    echo "  3. Run ./logs.sh"
    echo ""
    echo -e "${YELLOW}Debug Tips:${NC}"
    echo "  1. Enable debug logging in configuration.yaml:"
    echo "     logger:"
    echo "       logs:"
    echo "         custom_components.vacasa: debug"
    echo ""
    echo "  2. Restart Home Assistant after config changes"
    echo "  3. Use 'live' monitoring when testing changes"
    echo "  4. Check 'errors' first for obvious issues"
}

# Main menu function
show_menu() {
    echo -e "${PURPLE}🏠 Home Assistant Vacasa Integration Log Viewer${NC}"
    echo "================================================="
    echo ""
    echo "Select an option:"
    echo -e "  ${GREEN}1)${NC} Recent logs (last 50 Vacasa entries)"
    echo -e "  ${GREEN}2)${NC} Live log monitoring"
    echo -e "  ${GREEN}3)${NC} Debug logs only"
    echo -e "  ${GREEN}4)${NC} Error logs only"
    echo -e "  ${GREEN}5)${NC} Calendar entity logs"
    echo -e "  ${GREEN}6)${NC} Entity registration logs"
    echo -e "  ${GREEN}7)${NC} Integration startup logs"
    echo -e "  ${GREEN}8)${NC} Current system status"
    echo -e "  ${GREEN}9)${NC} Custom search"
    echo -e "  ${RED}10)${NC} Config flow errors (500 errors)"
    echo -e "  ${RED}11)${NC} Import/module errors"
    echo -e "  ${RED}12)${NC} Python syntax errors"
    echo -e "  ${GREEN}h)${NC} Help"
    echo -e "  ${GREEN}q)${NC} Quit"
    echo ""
    echo -n "Enter choice: "
}

# Main execution
main() {
    # Handle command line arguments
    case "$1" in
        "recent")
            check_connection && show_recent_logs
            exit $?
            ;;
        "live")
            check_connection && monitor_live_logs
            exit $?
            ;;
        "debug")
            check_connection && show_debug_logs
            exit $?
            ;;
        "errors")
            check_connection && show_error_logs
            exit $?
            ;;
        "calendar")
            check_connection && show_calendar_logs
            exit $?
            ;;
        "status")
            check_connection && show_status
            exit $?
            ;;
        "config_flow"|"configflow")
            check_connection && show_config_flow_errors
            exit $?
            ;;
        "import"|"imports")
            check_connection && show_import_errors
            exit $?
            ;;
        "syntax")
            check_connection && show_syntax_errors
            exit $?
            ;;
        "help"|"-h"|"--help")
            show_help
            exit 0
            ;;
    esac

    # Interactive mode
    check_connection

    while true; do
        echo ""
        show_menu
        read -r choice
        echo ""

        case $choice in
            1)
                show_recent_logs
                ;;
            2)
                monitor_live_logs
                ;;
            3)
                show_debug_logs
                ;;
            4)
                show_error_logs
                ;;
            5)
                show_calendar_logs
                ;;
            6)
                show_entity_logs
                ;;
            7)
                show_startup_logs
                ;;
            8)
                show_status
                ;;
            9)
                custom_search
                ;;
            10)
                show_config_flow_errors
                ;;
            11)
                show_import_errors
                ;;
            12)
                show_syntax_errors
                ;;
            h|H)
                show_help
                ;;
            q|Q)
                echo -e "${BLUE}👋 Goodbye!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Invalid option. Please try again.${NC}"
                ;;
        esac

        echo ""
        echo -e "${YELLOW}Press Enter to continue...${NC}"
        read -r
    done
}

# Run main function with all arguments
main "$@"
