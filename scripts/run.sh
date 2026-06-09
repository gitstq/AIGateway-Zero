#!/bin/bash
# AIGateway-Zero Startup Script
# 轻量级AI模型统一网关启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$PROJECT_DIR/src"

# Default configuration
HOST="${AIGATEWAY_HOST:-0.0.0.0}"
PORT="${AIGATEWAY_PORT:-8080}"
CONFIG="${AIGATEWAY_CONFIG:-$PROJECT_DIR/aigateway.yaml}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║   🤖 AIGateway-Zero v1.0.0                                    ║"
    echo "║   Lightweight AI Model Unified Gateway                        ║"
    echo "║   轻量级AI模型统一网关                                          ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --host HOST       Server host (default: $HOST)"
    echo "  -p, --port PORT       Server port (default: $PORT)"
    echo "  -c, --config PATH     Config file path"
    echo "  --init-config         Create demo config file"
    echo "  --test                Run unit tests"
    echo "  --help                Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  AIGATEWAY_HOST        Server host"
    echo "  AIGATEWAY_PORT        Server port"
    echo "  AIGATEWAY_CONFIG      Config file path"
}

run_tests() {
    echo -e "${YELLOW}Running unit tests...${NC}"
    cd "$PROJECT_DIR"
    python3 -m unittest discover -s tests -v
    echo -e "${GREEN}Tests completed!${NC}"
}

init_config() {
    echo -e "${YELLOW}Creating demo configuration...${NC}"
    cd "$PROJECT_DIR"
    python3 "$SRC_DIR/main.py" --init-config
    echo -e "${GREEN}Config file created: $PROJECT_DIR/aigateway.yaml${NC}"
    echo -e "${YELLOW}Please edit the config file and add your API keys.${NC}"
}

start_server() {
    print_banner
    echo -e "${GREEN}Starting AIGateway-Zero...${NC}"
    echo -e "Host: ${YELLOW}$HOST${NC}"
    echo -e "Port: ${YELLOW}$PORT${NC}"
    if [ -f "$CONFIG" ]; then
        echo -e "Config: ${YELLOW}$CONFIG${NC}"
    else
        echo -e "Config: ${YELLOW}Using defaults (no config file)${NC}"
    fi
    echo ""

    cd "$PROJECT_DIR"
    if [ -f "$CONFIG" ]; then
        exec python3 "$SRC_DIR/main.py" -c "$CONFIG" -H "$HOST" -p "$PORT"
    else
        exec python3 "$SRC_DIR/main.py" -H "$HOST" -p "$PORT"
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG="$2"
            shift 2
            ;;
        --init-config)
            init_config
            exit 0
            ;;
        --test)
            run_tests
            exit 0
            ;;
        --help)
            print_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_help
            exit 1
            ;;
    esac
done

start_server
