# Testing Guide for Code Sergeant

This document provides a comprehensive guide to testing Code Sergeant, including manual testing checklists, automated tests, and pre-release verification.

## Table of Contents

- [Quick Start](#quick-start)
- [Automated Tests](#automated-tests)
- [Manual Testing Checklist](#manual-testing-checklist)
- [Pre-Release Checklist](#pre-release-checklist)
- [Performance Testing](#performance-testing)
- [Edge Case Testing](#edge-case-testing)

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=code_sergeant --cov-report=html

# View coverage report
open htmlcov/index.html
```

---

## Automated Tests

### Test Structure

```
tests/
├── unit/                    # Fast, isolated tests
│   ├── test_judge.py        # Activity judgment logic
│   ├── test_controller.py   # Controller state management
│   ├── test_pomodoro.py     # Timer functionality
│   └── test_tts.py          # TTS queue management
├── integration/             # Component interaction tests
│   ├── test_bridge_server.py
│   ├── test_session_flow.py
│   └── test_ai_fallback.py
└── conftest.py              # Shared fixtures
```

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Skip slow tests
pytest -m "not slow"

# Specific test file
pytest tests/unit/test_judge.py -v

# Specific test
pytest tests/unit/test_judge.py::TestActivityJudgeEdgeCases::test_judge_with_empty_goal -v

# With coverage
pytest --cov=code_sergeant --cov=bridge --cov-report=html

# Stop on first failure
pytest -x

# Verbose output
pytest -v --tb=long
```

### Test Markers

| Marker | Description | Example |
|--------|-------------|---------|
| `unit` | Unit tests | `pytest -m unit` |
| `integration` | Integration tests | `pytest -m integration` |
| `slow` | Slow tests | `pytest -m "not slow"` |

---

## Manual Testing Checklist

### Application Launch

- [ ] App appears in menu bar with ⚔️ icon
- [ ] Clicking icon shows popover
- [ ] No crash on startup
- [ ] Python bridge starts automatically
- [ ] Health check passes (`http://localhost:5050/api/health`)

### Session Management

- [ ] Can start session with goal
- [ ] Can start session without goal
- [ ] Can pause session
- [ ] Can resume session
- [ ] Can end session
- [ ] Session summary shows correct stats

### Pomodoro Timer

- [ ] Timer starts at correct duration
- [ ] Timer counts down correctly
- [ ] Pause works
- [ ] Resume works
- [ ] Break transition works
- [ ] Long break after 4 pomodoros

### Activity Monitoring

- [ ] Detects app changes
- [ ] Detects window title changes
- [ ] Detects idle state
- [ ] On-task apps show correct judgment
- [ ] Off-task apps trigger warning

### Voice Features

- [ ] TTS speaks warnings
- [ ] TTS can be stopped
- [ ] Wake word detection works ("Hey Sergeant")
- [ ] Voice notes can be recorded

### Settings

- [ ] Can change personality
- [ ] Can change work duration
- [ ] Can change break duration
- [ ] Settings persist after restart

---

## Pre-Release Checklist

### Code Quality

- [ ] All tests pass: `pytest`
- [ ] Coverage above 70%: `pytest --cov-fail-under=70`
- [ ] Black formatting: `black --check code_sergeant/ bridge/ tests/`
- [ ] isort sorting: `isort --check-only code_sergeant/ bridge/ tests/`
- [ ] flake8 linting: `flake8 code_sergeant/ bridge/ tests/`
- [ ] No critical security issues: `bandit -r code_sergeant/ bridge/ -ll`

### Documentation

- [ ] README.md is up to date
- [ ] CHANGELOG.md has release notes
- [ ] ARCHITECTURE.md reflects current design
- [ ] All public APIs are documented
- [ ] Installation instructions work on clean system

### Functionality

- [ ] Complete session workflow (start → work → break → end)
- [ ] All personalities work
- [ ] Ollama integration works
- [ ] Fallback to rule-based works when Ollama unavailable
- [ ] TTS works with pyttsx3
- [ ] No memory leaks in long sessions (2+ hours)

### Platform

- [ ] Works on macOS Monterey (12)
- [ ] Works on macOS Ventura (13)
- [ ] Works on macOS Sonoma (14)
- [ ] Works with Python 3.10
- [ ] Works with Python 3.11
- [ ] Works with Python 3.12

---

## Performance Testing

### Memory Usage

Monitor memory during a long session:

```bash
# Start Code Sergeant
python main.py &

# Monitor memory
while true; do
    ps aux | grep "[p]ython main.py" | awk '{print $6/1024 " MB"}'
    sleep 60
done
```

**Acceptable**: < 200MB for 2-hour session

### Response Time

Test judgment response time:

```python
import time
from code_sergeant.judge import ActivityJudge
from code_sergeant.models import ActivityEvent
from datetime import datetime

judge = ActivityJudge()
activity = ActivityEvent(ts=datetime.now(), app="Cursor", title="test.py")

times = []
for _ in range(100):
    start = time.time()
    judge.judge("coding", activity, [], None, 30)
    times.append(time.time() - start)

print(f"Average: {sum(times)/len(times)*1000:.2f}ms")
print(f"Max: {max(times)*1000:.2f}ms")
```

**Acceptable**: 
- Rule-based: < 10ms average
- Ollama: < 2000ms average

### CPU Usage

Monitor CPU during active session:

```bash
top -pid $(pgrep -f "python main.py")
```

**Acceptable**: < 10% CPU during idle, < 30% during active judgment

---

## Edge Case Testing

### Input Edge Cases

| Test Case | Input | Expected Behavior |
|-----------|-------|-------------------|
| Empty goal | `""` | Accept, use default behavior |
| Unicode goal | `"修复bug 🐛"` | Accept, judge correctly |
| Very long goal | 1000+ characters | Accept, may truncate for LLM |
| Special chars | `"Fix #123 & deploy!"` | Accept |
| Whitespace only | `"   "` | Treat as empty |

### State Edge Cases

| Test Case | Scenario | Expected Behavior |
|-----------|----------|-------------------|
| Rapid toggle | Start/stop 10x quickly | No crash, clean state |
| Pause at 0:01 | Pause when 1 second left | State preserved |
| Resume idle | Resume after 30+ min | Timer continues correctly |
| End during break | End session during break | Clean end, no crash |

### Network Edge Cases

| Test Case | Scenario | Expected Behavior |
|-----------|----------|-------------------|
| Ollama offline | Start without Ollama | Fall back to rule-based |
| Ollama timeout | Slow Ollama response | Timeout, use fallback |
| Port in use | Port 5050 already bound | Auto-kill stale process |

### Resource Edge Cases

| Test Case | Scenario | Expected Behavior |
|-----------|----------|-------------------|
| Long session | 8+ hours | No memory leak |
| Many judgments | 1000+ judgments | History limited, no slowdown |
| TTS queue flood | 100 speak requests | Queue bounded, graceful handling |

---

## Testing Scripts

### Run Full Test Suite

```bash
#!/bin/bash
# scripts/run_tests.sh

set -e

echo "=== Running Code Sergeant Test Suite ==="

echo "1. Unit Tests..."
pytest tests/unit/ -v --cov=code_sergeant --cov=bridge

echo "2. Integration Tests..."
pytest tests/integration/ -v --cov=code_sergeant --cov=bridge --cov-append

echo "3. Coverage Report..."
coverage report --fail-under=70

echo "4. Linting..."
black --check code_sergeant/ bridge/ tests/
isort --check-only code_sergeant/ bridge/ tests/
flake8 code_sergeant/ bridge/ tests/ --count --select=E9,F63,F7,F82

echo "=== All Tests Passed! ==="
```

### Smoke Test

```bash
#!/bin/bash
# scripts/smoke_test.sh

set -e

echo "Starting smoke test..."

# Start bridge server
python bridge/server.py &
SERVER_PID=$!
sleep 3

# Health check
curl -s http://localhost:5050/api/health | grep -q "healthy"
echo "✓ Health check passed"

# Status check
curl -s http://localhost:5050/api/status
echo "✓ Status endpoint works"

# Cleanup
kill $SERVER_PID

echo "Smoke test passed!"
```

---

## Troubleshooting Tests

### Common Issues

**Tests fail with import errors**:
```bash
pip install -e .
pip install -r requirements-dev.txt
```

**Coverage too low**:
```bash
# See what's not covered
pytest --cov=code_sergeant --cov-report=html
open htmlcov/index.html
```

**Flaky tests**:
```bash
# Run multiple times
pytest --count=5 tests/unit/test_specific.py
```

**Slow tests**:
```bash
# Profile test duration
pytest --durations=10
```

---

## Continuous Integration

Tests run automatically on:
- Every push to `main` or `develop`
- Every pull request

CI configuration: `.github/workflows/test.yml`

To run the same tests locally:
```bash
pytest -v --cov=code_sergeant --cov=bridge --cov-report=xml
```

---

## Adding New Tests

1. Create test file in appropriate directory
2. Use fixtures from `conftest.py`
3. Mark tests with `@pytest.mark.unit` or `@pytest.mark.integration`
4. Run tests to verify
5. Update coverage if needed

Example:
```python
import pytest
from code_sergeant.models import ActivityEvent

@pytest.mark.unit
class TestNewFeature:
    def test_basic_functionality(self, sample_activity):
        # Test implementation
        assert result is not None
```

