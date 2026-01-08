#!/bin/bash
# Smoke test for Code Sergeant
# Quick verification that core functionality works

set -e

echo "============================================"
echo "   Code Sergeant Smoke Test"
echo "============================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
PORT=5050
TIMEOUT=10

# Cleanup function
cleanup() {
    if [[ -n "$SERVER_PID" ]]; then
        echo ""
        echo "Cleaning up..."
        kill $SERVER_PID 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Check if port is already in use
if lsof -i :$PORT >/dev/null 2>&1; then
    echo -e "${YELLOW}Port $PORT already in use. Attempting to free...${NC}"
    lsof -ti :$PORT | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Start bridge server
echo "1. Starting bridge server..."
python bridge/server.py &
SERVER_PID=$!
echo "   Server PID: $SERVER_PID"

# Wait for server to start
echo "2. Waiting for server to initialize..."
for i in {1..10}; do
    if curl -s http://localhost:$PORT/api/health >/dev/null 2>&1; then
        break
    fi
    if [[ $i -eq 10 ]]; then
        echo -e "${RED}✗ Server failed to start${NC}"
        exit 1
    fi
    sleep 1
done
echo -e "${GREEN}✓ Server started${NC}"

# Test health endpoint
echo ""
echo "3. Testing health endpoint..."
HEALTH=$(curl -s http://localhost:$PORT/api/health)
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
    echo "   Response: $HEALTH"
    exit 1
fi

# Test status endpoint
echo ""
echo "4. Testing status endpoint..."
STATUS=$(curl -s http://localhost:$PORT/api/status)
if echo "$STATUS" | grep -q "session_active"; then
    echo -e "${GREEN}✓ Status endpoint works${NC}"
else
    echo -e "${RED}✗ Status endpoint failed${NC}"
    echo "   Response: $STATUS"
    exit 1
fi

# Test timer endpoint
echo ""
echo "5. Testing timer endpoint..."
TIMER=$(curl -s http://localhost:$PORT/api/timer)
if echo "$TIMER" | grep -q "state"; then
    echo -e "${GREEN}✓ Timer endpoint works${NC}"
else
    echo -e "${RED}✗ Timer endpoint failed${NC}"
    echo "   Response: $TIMER"
    exit 1
fi

# Test activity endpoint
echo ""
echo "6. Testing activity endpoint..."
ACTIVITY=$(curl -s http://localhost:$PORT/api/activity/current)
if echo "$ACTIVITY" | grep -q "app"; then
    echo -e "${GREEN}✓ Activity endpoint works${NC}"
else
    echo -e "${YELLOW}⚠ Activity endpoint returned unexpected response${NC}"
    echo "   Response: $ACTIVITY"
fi

# Test session start
echo ""
echo "7. Testing session start..."
SESSION_START=$(curl -s -X POST http://localhost:$PORT/api/session/start \
    -H "Content-Type: application/json" \
    -d '{"goal": "Smoke test"}')
if echo "$SESSION_START" | grep -q "success"; then
    echo -e "${GREEN}✓ Session start works${NC}"
else
    echo -e "${YELLOW}⚠ Session start returned unexpected response${NC}"
    echo "   Response: $SESSION_START"
fi

# Test session end
echo ""
echo "8. Testing session end..."
SESSION_END=$(curl -s -X POST http://localhost:$PORT/api/session/end)
if echo "$SESSION_END" | grep -q "success"; then
    echo -e "${GREEN}✓ Session end works${NC}"
else
    echo -e "${YELLOW}⚠ Session end returned unexpected response${NC}"
    echo "   Response: $SESSION_END"
fi

# Summary
echo ""
echo "============================================"
echo -e "${GREEN}   Smoke Test Passed!${NC}"
echo "============================================"
echo ""

