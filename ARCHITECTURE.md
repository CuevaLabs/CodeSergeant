# Code Sergeant Architecture

This document describes the system architecture, component responsibilities, data flows, and design decisions for Code Sergeant.

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Component Details](#component-details)
- [Data Flow](#data-flow)
- [Design Decisions](#design-decisions)
- [Security Considerations](#security-considerations)

---

## Overview

Code Sergeant is a productivity application with a hybrid architecture:

- **SwiftUI Frontend**: Native macOS menu bar application
- **Python Backend**: Core logic, AI integration, and services
- **Bridge Server**: HTTP API connecting frontend and backend

This architecture enables:
- Native macOS look and feel
- Rich Python ecosystem for AI/ML
- Clean separation of concerns
- Easy testing and development

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         macOS System                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                 SwiftUI Application                         │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │    │
│  │  │ Menu Bar    │  │ Dashboard   │  │ Settings    │        │    │
│  │  │ View        │  │ Window      │  │ View        │        │    │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │    │
│  │         │                 │                 │               │    │
│  │         └─────────────────┼─────────────────┘               │    │
│  │                           ▼                                 │    │
│  │                 ┌─────────────────┐                         │    │
│  │                 │  PythonBridge   │                         │    │
│  │                 │     Actor       │                         │    │
│  │                 └────────┬────────┘                         │    │
│  └──────────────────────────┼──────────────────────────────────┘    │
│                             │                                        │
│                             │ HTTP/JSON (localhost:5050)             │
│                             │                                        │
│  ┌──────────────────────────▼──────────────────────────────────┐    │
│  │                  Bridge Server (Flask)                       │    │
│  │  ┌───────────────────────────────────────────────────────┐  │    │
│  │  │                    REST API                            │  │    │
│  │  │  /api/health    /api/status    /api/session/*         │  │    │
│  │  │  /api/timer     /api/tts/*     /api/config            │  │    │
│  │  └───────────────────────────────────────────────────────┘  │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                             │                                        │
│  ┌──────────────────────────▼──────────────────────────────────┐    │
│  │                   AppController                              │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │    │
│  │  │ Session │ │ State   │ │ Worker  │ │ Event   │           │    │
│  │  │ Manager │ │ Manager │ │ Registry│ │ Queue   │           │    │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                             │                                        │
│         ┌───────────────────┼───────────────────┐                   │
│         │                   │                   │                    │
│         ▼                   ▼                   ▼                    │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │   Native    │    │  Activity   │    │    TTS      │             │
│  │   Monitor   │    │   Judge     │    │   Service   │             │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘             │
│         │                  │                   │                    │
│         ▼                  ▼                   ▼                    │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │   macOS     │    │   Ollama    │    │ ElevenLabs/ │             │
│  │   APIs      │    │   (Local)   │    │  pyttsx3    │             │
│  └─────────────┘    └─────────────┘    └─────────────┘             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### SwiftUI Frontend

**Purpose**: Native macOS user interface

**Components**:

| Component | Responsibility |
|-----------|----------------|
| `CodeSergeantApp` | Application entry point, app delegate |
| `ContentView` | Main menu bar popover content |
| `DashboardView` | Detailed session dashboard window |
| `SettingsView` | User preferences and configuration |
| `PythonBridge` | Actor for backend communication |

**Key Design Points**:
- Menu bar app (no dock icon)
- SwiftUI for modern, responsive UI
- Actor-based concurrency for thread safety
- Auto-starts Python backend on launch

### Bridge Server (Flask)

**Purpose**: REST API connecting Swift frontend to Python backend

**Endpoints**:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/status` | GET | Application status |
| `/api/session/start` | POST | Start focus session |
| `/api/session/end` | POST | End focus session |
| `/api/session/pause` | POST | Pause session |
| `/api/session/resume` | POST | Resume session |
| `/api/timer` | GET | Pomodoro timer state |
| `/api/tts/speak` | POST | Speak text |
| `/api/config` | GET/PATCH | Configuration |

**Key Design Points**:
- Runs on localhost:5050
- CORS enabled for development
- Thread-safe request handling
- Auto-kills stale processes on startup

### AppController

**Purpose**: Central orchestrator for all backend services

**Responsibilities**:
- Session lifecycle management
- State synchronization
- Worker thread coordination
- Event queue processing

**State Management**:

```python
@dataclass
class ControllerState:
    session_active: bool = False
    goal: Optional[str] = None
    current_activity: Optional[str] = None
    last_judgment: Optional[str] = None
    stats: Optional[SessionStats] = None
    pomodoro_state: Optional[PomodoroState] = None
    personality_name: str = "sergeant"
    wake_word: str = "hey sergeant"
```

### Activity Judge

**Purpose**: Classify user activity as on-task/off-task

**Classification Pipeline**:

```
1. Check if AFK → Return "idle"
2. Check if thinking → Return "thinking"
3. Try AI classification (OpenAI/Ollama)
4. Fallback to rule-based classifier
5. Determine action (none/warn/yell)
6. Return Judgment
```

**Fallback Hierarchy**:
1. OpenAI GPT (if API key available)
2. Ollama local LLM (if running)
3. Rule-based classifier (always available)

### TTS Service

**Purpose**: Text-to-speech output

**Providers**:
- **ElevenLabs**: High-quality AI voices (requires API key)
- **pyttsx3**: Local system voices (always available)

**Queue Management**:
- Thread-safe speak queue
- Cancel/pause support
- Rate limiting

### Native Monitor

**Purpose**: Access macOS system information

**Capabilities**:
- Get frontmost application
- Get active window title
- Get idle time (keyboard/mouse)
- Detect system sleep/wake

### Pomodoro Timer

**Purpose**: Work/break interval management

**States**:
- `stopped` - No active timer
- `work` - Focus period
- `short_break` - Short break (5 min default)
- `long_break` - Long break after 4 pomodoros

**Callbacks**:
- `on_tick` - Every second
- `on_state_change` - State transitions
- `on_complete` - Period completion

---

## Data Flow

### Session Start Flow

```
User clicks "Start"
        │
        ▼
SwiftUI sends POST /api/session/start
        │
        ▼
Bridge Server receives request
        │
        ▼
controller.start_session(goal)
        │
        ├──► Start activity polling worker
        ├──► Start judgment worker
        ├──► Start Pomodoro timer
        └──► Announce session start (TTS)
        │
        ▼
Return success to SwiftUI
        │
        ▼
SwiftUI updates UI state
```

### Activity Judgment Flow

```
Poll worker detects activity change
        │
        ▼
Create ActivityEvent
        │
        ▼
Queue for judgment worker
        │
        ▼
Judge worker processes:
        │
        ├──► Is AFK? → "idle"
        ├──► Is thinking? → "thinking"
        └──► Call AI classifier
               │
               ├──► OpenAI available? → Use GPT
               ├──► Ollama available? → Use local LLM
               └──► Use rule-based fallback
        │
        ▼
Return Judgment (classification, confidence, say, action)
        │
        ▼
Process action:
        │
        ├──► none → Log only
        ├──► warn → Speak warning
        └──► yell → Speak urgent warning
        │
        ▼
Update stats (focus/off-task seconds)
```

### State Sync Flow

```
SwiftUI polls /api/status every 1s
        │
        ▼
Bridge returns ControllerState
        │
        ▼
SwiftUI updates:
        ├──► Timer display
        ├──► Focus time
        ├──► Current goal
        └──► Session status
```

---

## Design Decisions

### Why Hybrid Architecture?

**Decision**: Use Python backend + SwiftUI frontend

**Rationale**:
- Python has better AI/ML ecosystem (Ollama, OpenAI, Whisper)
- SwiftUI provides native macOS experience
- Clean separation enables independent testing
- Bridge pattern is well-established

**Alternatives Considered**:
- Pure Swift: Limited AI library support
- Pure Python: Non-native UI, limited system integration
- Electron: Performance and resource concerns

### Why Local AI First?

**Decision**: Prioritize Ollama over cloud APIs

**Rationale**:
- Privacy: All data stays on user's machine
- Cost: No API charges for heavy users
- Reliability: Works offline
- Latency: Local inference is often faster

### Why Event Queue?

**Decision**: Use queue-based worker communication

**Rationale**:
- Thread safety without complex locking
- Decoupled components
- Easy to add/remove workers
- Testable in isolation

### Why HTTP Bridge?

**Decision**: HTTP API instead of IPC/sockets

**Rationale**:
- Standard, well-understood protocol
- Easy to debug (curl, browser)
- Good tooling (Flask, requests)
- Cross-language compatibility

---

## Security Considerations

### API Keys

- Stored in `.env` file (gitignored)
- Never logged or returned in API responses
- Environment variable fallbacks

### Network

- Bridge server binds to localhost only
- No external network access required
- All AI processing can be local

### Permissions

- Microphone: Required for voice features
- Accessibility: Required for window title monitoring
- Neither is required for core functionality

### Data Storage

- Session logs stored locally in `logs/`
- No telemetry or analytics
- User can delete all data easily

---

## Performance Considerations

### Memory

- Activity history limited to recent entries
- TTS queue bounded
- Periodic cleanup of old logs

### CPU

- AI classification rate-limited
- Idle detection reduces unnecessary work
- Background workers are pausable

### Startup Time

- Services initialized lazily where possible
- SwiftUI auto-starts backend
- Health check before full initialization

---

## Extension Points

### Adding New Personalities

1. Add profile to `PersonalityProfile.get_predefined()`
2. Add wake word to config
3. Add phrase patterns to `phrases.py`

### Adding New AI Backends

1. Implement `classify()` method in `AIClient`
2. Add availability check
3. Update fallback hierarchy in `ActivityJudge`

### Adding New API Endpoints

1. Add route in `bridge/server.py`
2. Implement handler logic
3. Add corresponding method in `PythonBridge.swift`
4. Add tests

---

## Testing Architecture

```
tests/
├── unit/                  # Isolated component tests
│   ├── test_judge.py      # Activity judge logic
│   ├── test_controller.py # Controller state
│   ├── test_pomodoro.py   # Timer logic
│   └── test_tts.py        # TTS queue
├── integration/           # Component interaction tests
│   ├── test_bridge_server.py
│   ├── test_session_flow.py
│   └── test_ai_fallback.py
└── conftest.py            # Shared fixtures and mocks
```

**Testing Strategy**:
- Unit tests: Fast, isolated, no external dependencies
- Integration tests: Component interactions, mocked externals
- E2E tests: Full system (manual, pre-release)

---

## Future Considerations

### Scalability

Current design supports:
- Single user
- Local execution
- Moderate session lengths (8+ hours tested)

Future scaling may require:
- Session data compression
- Distributed logging
- Cloud sync (opt-in)

### Platform Expansion

Architecture supports:
- iOS companion app (shared backend)
- Web dashboard (Bridge server + React)
- Windows/Linux (replace native monitor)

---

## Glossary

| Term | Definition |
|------|------------|
| **AFK** | Away From Keyboard - user idle |
| **Bridge** | HTTP server connecting Swift and Python |
| **Judgment** | AI classification of activity |
| **Pomodoro** | 25-minute focused work period |
| **Wake Word** | Voice activation phrase ("Hey Sergeant") |
| **Worker** | Background thread performing async tasks |

