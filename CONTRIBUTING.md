# Contributing to Code Sergeant

Thank you for your interest in contributing to Code Sergeant! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)

---

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. We expect all contributors to:

- Be respectful and considerate in discussions
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other community members

---

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- macOS 12 (Monterey) or later
- Python 3.10 or higher
- Git
- [Ollama](https://ollama.ai/) (optional, for AI features)

### Finding Issues to Work On

1. **Good First Issues**: Look for issues labeled [`good first issue`](https://github.com/CuevaLabs/CodeSergeant/labels/good%20first%20issue) - these are great for newcomers
2. **Help Wanted**: Issues labeled [`help wanted`](https://github.com/CuevaLabs/CodeSergeant/labels/help%20wanted) need community input
3. **Bug Fixes**: Issues labeled [`bug`](https://github.com/CuevaLabs/CodeSergeant/labels/bug) are always appreciated

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/CuevaLabs/CodeSergeant.git
cd CodeSergeant
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies
pip install -r requirements-dev.txt
```

### 4. Install Pre-commit Hooks

```bash
pre-commit install
```

### 5. Verify Setup

```bash
# Run tests
pytest

# Run linting
black --check code_sergeant/ bridge/ tests/
isort --check-only code_sergeant/ bridge/ tests/
flake8 code_sergeant/ bridge/ tests/
```

### 6. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

---

## Project Structure

```
CodeSergeant/
├── code_sergeant/          # Core Python backend
│   ├── __init__.py
│   ├── controller.py       # Main application controller
│   ├── native_monitor.py   # macOS activity monitoring
│   ├── judge.py            # Activity judgment logic
│   ├── models.py           # Data models
│   ├── pomodoro.py         # Pomodoro timer
│   ├── tts.py              # Text-to-speech service
│   └── voice.py            # Voice recognition
├── bridge/                 # Swift-Python bridge server
│   └── server.py           # Flask API server
├── CodeSergeantUI/         # SwiftUI frontend
│   ├── Models/
│   ├── Services/
│   └── Views/
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── conftest.py         # Test fixtures
└── main.py                 # Entry point
```

### Key Components

| Component | Responsibility |
|-----------|----------------|
| `AppController` | Orchestrates all services, manages session state |
| `NativeMonitor` | Monitors active app and window title via macOS APIs |
| `ActivityJudge` | Classifies activity as on-task/off-task using AI |
| `TTSService` | Text-to-speech output |
| `PomodoroTimer` | Work/break timer management |
| `Bridge Server` | HTTP API for SwiftUI communication |

---

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with these tools:

- **Black**: Code formatting (line length: 88)
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

### Code Formatting

```bash
# Format code
black code_sergeant/ bridge/ tests/
isort code_sergeant/ bridge/ tests/

# Check without modifying
black --check code_sergeant/ bridge/ tests/
isort --check-only code_sergeant/ bridge/ tests/
```

### Type Hints

Use type hints for all function signatures:

```python
# Good
def judge_activity(
    goal: str,
    activity: ActivityEvent,
    history: list[ActivityEvent]
) -> Judgment:
    ...

# Avoid
def judge_activity(goal, activity, history):
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_focus_time(sessions: list[Session]) -> int:
    """Calculate total focus time from sessions.
    
    Args:
        sessions: List of completed sessions.
        
    Returns:
        Total focus time in seconds.
        
    Raises:
        ValueError: If sessions list is empty.
    """
    ...
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add voice note transcription
fix: resolve memory leak in activity monitor
docs: update installation instructions
test: add tests for pomodoro edge cases
refactor: simplify judge fallback logic
```

---

## Testing Requirements

### Test Coverage

- **Minimum Coverage**: 70% for critical paths
- **New Features**: Must include tests
- **Bug Fixes**: Should include regression tests

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=code_sergeant --cov-report=html

# Run specific test file
pytest tests/unit/test_judge.py -v

# Run tests matching pattern
pytest -k "test_session" -v

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

### Writing Tests

```python
import pytest
from code_sergeant.models import ActivityEvent

@pytest.mark.unit
class TestActivityJudge:
    """Tests for ActivityJudge component."""
    
    def test_judge_returns_valid_classification(self, sample_activity):
        """Test that judge returns valid classification."""
        judge = ActivityJudge()
        result = judge.judge(
            goal="coding",
            activity=sample_activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result.classification in ["on_task", "off_task", "idle", "thinking"]
```

### Test Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.unit` | Unit tests (fast, isolated) |
| `@pytest.mark.integration` | Integration tests (component interactions) |
| `@pytest.mark.slow` | Slow tests (skip in quick runs) |

---

## Pull Request Process

### 1. Before Submitting

- [ ] Update documentation if needed
- [ ] Add/update tests for your changes
- [ ] Run the full test suite: `pytest`
- [ ] Run linting: `black --check . && isort --check-only .`
- [ ] Update CHANGELOG.md if applicable

### 2. PR Title Format

Use the same format as commit messages:

```
feat: add custom wake word support
fix: resolve timer pause issue (#42)
docs: improve API documentation
```

### 3. PR Description

Include:
- **What**: Summary of changes
- **Why**: Motivation and context
- **How**: Implementation approach
- **Testing**: How to verify the changes
- **Screenshots**: For UI changes

### 4. Review Process

1. Create PR against `main` branch
2. Ensure CI passes
3. Request review from maintainers
4. Address feedback
5. Merge after approval

### 5. After Merge

- Delete your feature branch
- Pull latest `main` for future work

---

## Issue Guidelines

### Bug Reports

Include:
- macOS version
- Python version
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs

### Feature Requests

Include:
- Use case description
- Proposed solution
- Alternative considerations
- Willingness to implement

### Questions

For general questions:
- Check existing documentation
- Search closed issues
- Use GitHub Discussions

---

## Development Tips

### Hot Reload for Bridge Server

```bash
FLASK_DEBUG=true python bridge/server.py
```

### Testing TTS Without Audio

```python
# In tests, use MockTTSService from conftest.py
def test_tts(mock_tts_service):
    mock_tts_service.speak("Hello")
    assert "Hello" in mock_tts_service.spoken_texts
```

### Debugging AI Judgments

```python
import logging
logging.getLogger("code_sergeant.judge").setLevel(logging.DEBUG)
```

---

## Getting Help

- **Discord**: [Join our server](#) (coming soon)
- **GitHub Discussions**: For questions and ideas
- **Email**: maintainer@example.com

---

## Recognition

Contributors are recognized in:
- README.md Contributors section
- Release notes
- GitHub contributors page

Thank you for contributing to Code Sergeant! 🎖️

