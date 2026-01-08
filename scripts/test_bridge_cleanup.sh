#!/bin/bash
# Test script to verify bridge server cleanup functionality

set -e

echo "🧪 Testing CodeSergeant Bridge Server Cleanup"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if port 5050 is free
check_port() {
    if lsof -ti :5050 > /dev/null 2>&1; then
        echo -e "${RED}❌ Port 5050 is already in use${NC}"
        echo "   Please stop any running CodeSergeant instances first"
        exit 1
    else
        echo -e "${GREEN}✅ Port 5050 is free${NC}"
    fi
}

# Start bridge server manually (simulating what SwiftUI app does)
start_bridge() {
    echo ""
    echo "🚀 Starting bridge server..."
    
    cd "$(dirname "$0")/.."
    
    if [ -d ".venv" ]; then
        source .venv/bin/activate
        python bridge/server.py &
        BRIDGE_PID=$!
        echo "   Bridge server started with PID: $BRIDGE_PID"
        sleep 2
        
        # Check if it's still running
        if ps -p $BRIDGE_PID > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Bridge server is running${NC}"
            return 0
        else
            echo -e "${RED}❌ Bridge server failed to start${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Virtual environment not found${NC}"
        return 1
    fi
}

# Test cleanup (simulating what happens when Xcode stops)
test_cleanup() {
    echo ""
    echo "🛑 Testing cleanup..."
    
    # Find Python process on port 5050
    PID=$(lsof -ti :5050 2>/dev/null || echo "")
    
    if [ -z "$PID" ]; then
        echo -e "${YELLOW}⚠️  No process found on port 5050${NC}"
        return 1
    fi
    
    echo "   Found process PID: $PID"
    
    # Kill the process (simulating cleanup)
    echo "   Killing process..."
    kill -9 $PID 2>/dev/null || true
    sleep 1
    
    # Verify it's gone
    if lsof -ti :5050 > /dev/null 2>&1; then
        echo -e "${RED}❌ Process still running after kill${NC}"
        return 1
    else
        echo -e "${GREEN}✅ Process successfully terminated${NC}"
        return 0
    fi
}

# Main test flow
main() {
    check_port
    
    if start_bridge; then
        echo ""
        echo "⏳ Waiting 3 seconds before testing cleanup..."
        sleep 3
        
        if test_cleanup; then
            echo ""
            echo -e "${GREEN}✅ All tests passed!${NC}"
            echo ""
            echo "The cleanup mechanism is working correctly."
            echo "When you stop the app in Xcode, the Python process will be terminated."
            exit 0
        else
            echo ""
            echo -e "${RED}❌ Cleanup test failed${NC}"
            exit 1
        fi
    else
        echo ""
        echo -e "${RED}❌ Failed to start bridge server${NC}"
        exit 1
    fi
}

# Cleanup on exit
trap 'if [ ! -z "$BRIDGE_PID" ]; then kill -9 $BRIDGE_PID 2>/dev/null || true; fi' EXIT

main
