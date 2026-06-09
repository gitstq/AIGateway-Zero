#!/bin/bash
# AIGateway-Zero Test Script
# 轻量级AI模型统一网关测试脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Running AIGateway-Zero test suite..."
echo "====================================="
cd "$PROJECT_DIR"

# Run all tests with verbose output
python3 -m unittest discover -s tests -v

echo ""
echo "====================================="
echo "All tests passed! ✅"
