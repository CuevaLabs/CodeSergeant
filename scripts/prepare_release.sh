#!/bin/bash
# Prepare Code Sergeant for release

set -e

VERSION="0.1.0"

echo "============================================"
echo "   Preparing Code Sergeant v$VERSION"
echo "============================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Pre-release checks
echo "1. Running pre-release checks..."

# Check if virtual environment is active
if [[ -z "$VIRTUAL_ENV" ]]; then
    if [[ -d ".venv" ]]; then
        source .venv/bin/activate
    fi
fi

# Run tests
echo ""
echo "2. Running tests..."
if pytest tests/ -v --tb=short; then
    echo -e "${GREEN}✓ All tests passed${NC}"
else
    echo -e "${RED}✗ Tests failed. Fix issues before release.${NC}"
    exit 1
fi

# Check coverage
echo ""
echo "3. Checking coverage..."
if pytest --cov=code_sergeant --cov=bridge --cov-fail-under=70 --cov-report=term-missing; then
    echo -e "${GREEN}✓ Coverage meets threshold${NC}"
else
    echo -e "${YELLOW}⚠ Coverage below 70%. Consider adding more tests.${NC}"
fi

# Run linting
echo ""
echo "4. Running linting..."
black --check code_sergeant/ bridge/ tests/ 2>/dev/null || echo -e "${YELLOW}⚠ Black formatting issues${NC}"
isort --check-only code_sergeant/ bridge/ tests/ 2>/dev/null || echo -e "${YELLOW}⚠ Import sorting issues${NC}"
flake8 code_sergeant/ bridge/ tests/ --count --select=E9,F63,F7,F82 2>/dev/null || echo -e "${YELLOW}⚠ Flake8 issues${NC}"

# Check documentation
echo ""
echo "5. Checking documentation..."
for doc in README.md CHANGELOG.md CONTRIBUTING.md ARCHITECTURE.md; do
    if [[ -f "$doc" ]]; then
        echo -e "   ${GREEN}✓${NC} $doc exists"
    else
        echo -e "   ${RED}✗${NC} $doc missing"
    fi
done

# Check required files
echo ""
echo "6. Checking required files..."
for file in LICENSE requirements.txt requirements-dev.txt pyproject.toml; do
    if [[ -f "$file" ]]; then
        echo -e "   ${GREEN}✓${NC} $file exists"
    else
        echo -e "   ${RED}✗${NC} $file missing"
    fi
done

# Summary
echo ""
echo "============================================"
echo "   Pre-release Check Complete"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Review CHANGELOG.md"
echo "  2. Update version in pyproject.toml if needed"
echo "  3. Create git tag: git tag -a v$VERSION -m 'Release v$VERSION'"
echo "  4. Push tag: git push origin v$VERSION"
echo "  5. Create GitHub release with RELEASE_NOTES.md"
echo ""

