#!/bin/bash
# Run full test suite for Code Sergeant

set -e

echo "============================================"
echo "   Code Sergeant Test Suite"
echo "============================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment is active
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}Warning: Virtual environment not detected${NC}"
    if [[ -d ".venv" ]]; then
        echo "Activating .venv..."
        source .venv/bin/activate
    fi
fi

# Install dependencies if needed
echo "1. Checking dependencies..."
pip install -q -r requirements.txt
pip install -q -r requirements-dev.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Run unit tests
echo ""
echo "2. Running unit tests..."
if pytest tests/unit/ -v --tb=short; then
    echo -e "${GREEN}✓ Unit tests passed${NC}"
else
    echo -e "${RED}✗ Unit tests failed${NC}"
    exit 1
fi

# Run integration tests
echo ""
echo "3. Running integration tests..."
if pytest tests/integration/ -v --tb=short; then
    echo -e "${GREEN}✓ Integration tests passed${NC}"
else
    echo -e "${RED}✗ Integration tests failed${NC}"
    exit 1
fi

# Run coverage
echo ""
echo "4. Running coverage analysis..."
pytest --cov=code_sergeant --cov=bridge --cov-report=term-missing --cov-fail-under=70

# Run linting
echo ""
echo "5. Running linting checks..."

echo "   - Black (formatting)..."
if black --check code_sergeant/ bridge/ tests/ 2>/dev/null; then
    echo -e "${GREEN}   ✓ Black passed${NC}"
else
    echo -e "${YELLOW}   ⚠ Black formatting issues found. Run 'black code_sergeant/ bridge/ tests/' to fix.${NC}"
fi

echo "   - isort (import sorting)..."
if isort --check-only code_sergeant/ bridge/ tests/ 2>/dev/null; then
    echo -e "${GREEN}   ✓ isort passed${NC}"
else
    echo -e "${YELLOW}   ⚠ Import sorting issues found. Run 'isort code_sergeant/ bridge/ tests/' to fix.${NC}"
fi

echo "   - flake8 (code quality)..."
if flake8 code_sergeant/ bridge/ tests/ --count --select=E9,F63,F7,F82 --show-source 2>/dev/null; then
    echo -e "${GREEN}   ✓ flake8 passed (critical errors)${NC}"
fi

# Summary
echo ""
echo "============================================"
echo -e "${GREEN}   All Tests Passed!${NC}"
echo "============================================"
echo ""
echo "Coverage report: htmlcov/index.html"
echo ""

