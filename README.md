# Code Sergeant

<div align="center">

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

**An AI-powered productivity companion that keeps you focused during deep work.**

[Features](#features) | [Quick Start](#quick-start) | [Documentation](#documentation) | [Contributing](#contributing)

</div>

---

## What is Code Sergeant?

Code Sergeant is a macOS menu bar app that monitors your activity during work sessions and gives you real-time feedback when you drift off track. It's like having a (customizable) drill sergeant watching your screen—except this one actually understands context.

Simple website blockers can't tell the difference between "YouTube - Cat Videos" and "YouTube - Python Tutorial." Code Sergeant can. It uses local AI (Ollama) to judge whether what you're doing actually relates to your stated goal, and speaks up when you need a nudge back to work.

### Why I Built This

It started with a post on X about ADHD and body doubling—the idea that having someone physically present helps you focus. I thought, "What if I had an AI body double? One that actually watches what I'm doing and calls me out when I drift?"

I looked into existing solutions: body doubling apps, Zoom coworking sessions. But I didn't want strangers watching me. I like to think out loud, and honestly, they wouldn't even know if I was distracted—I was reading Twitter during Zoom classes all the time and nobody noticed.

So when I couldn't find what I needed, I built it myself.

Code Sergeant is what came out: a privacy-first AI companion that actually understands context. It knows the difference between "YouTube - Python Tutorial" (productive) and "YouTube - Cat Videos" (get back to work). It runs entirely on your machine, so your data stays yours. And it has enough personality to make getting yelled at almost fun.

### Key Features

- **Context-aware judgment** - Knows Stack Overflow is productive when you're coding
- **100% local processing** - Your data never leaves your machine
- **Multiple personalities** - From drill sergeant to supportive buddy
- **Voice interaction** - Say "Hey Sergeant" to chat hands-free
- **Native macOS integration** - Lightweight menu bar app using AppKit/Quartz

---

## Features

### Activity Monitoring
- **AI-Powered Judgment** - Uses Ollama (local LLM) to understand if your activity matches your goal
- **Smart Fallback** - Rule-based classification when AI is unavailable
- **Native macOS APIs** - Reads window titles directly via AppKit/Quartz, no external dependencies

### Pomodoro Timer
- Built-in timer with configurable work/break durations
- Voice announcements for transitions
- Track completed pomodoros per session

### Voice Interaction
- **Wake Word** - Say "Hey Sergeant" (or your personality's wake word) to interact
- **Voice Notes** - Capture thoughts hands-free, automatically transcribed
- **Text-to-Speech** - Hear warnings, encouragement, and session summaries

### Multiple Personalities
Choose your motivation style:
- **Sergeant** - Strict, commanding, no-nonsense
- **Buddy** - Friendly and supportive
- **Advisor** - Professional and thoughtful
- **Coach** - Energetic and motivational

### Privacy First
- All AI processing runs locally (Ollama)
- Session data stays on your machine
- Optional cloud integrations (OpenAI, ElevenLabs) for enhanced features

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SwiftUI Frontend                          │
│  (Menu Bar App + Dashboard Window)                           │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/JSON (Port 5050)
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Bridge Server (Flask)                       │
│  REST API for Swift ↔ Python communication                   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  AppController (Python)                      │
│  • Session lifecycle    • State management                   │
│  • Worker coordination  • Event processing                   │
└──────┬──────────┬──────────┬──────────┬─────────────────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Activity │ │  Judge   │ │   TTS    │ │  Voice   │
│ Monitor  │ │  (LLM)   │ │ Service  │ │  Worker  │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
       │          │
       ▼          ▼
┌──────────┐ ┌──────────┐
│ Native   │ │ Ollama / │
│ macOS    │ │ OpenAI   │
└──────────┘ └──────────┘
```

---

## Quick Start

### Requirements

- macOS 12 (Monterey) or later
- Python 3.10+
- [Ollama](https://ollama.ai/) (optional but recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/CuevaLabs/CodeSergeant.git
cd CodeSergeant

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Install Ollama for AI-powered judgment
# Download from https://ollama.ai/, then:
ollama pull llama3.2

# Run Code Sergeant
python main.py
```

The app appears in your menu bar. Click it, set a goal, and start your session.

---

## Documentation

| Document | Description |
|----------|-------------|
| [QUICKSTART.md](QUICKSTART.md) | Get started in 5 minutes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design and component details |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues and solutions |

---

## Configuration

Configuration is stored in `config.json`:

```json
{
  "poll_interval_sec": 0.5,
  "judge_interval_sec": 10,
  "cooldown_seconds": 30,
  "personality": {
    "name": "sergeant"
  },
  "ollama": {
    "model": "llama3.2",
    "base_url": "http://localhost:11434"
  },
  "pomodoro": {
    "work_duration_minutes": 25,
    "short_break_minutes": 5,
    "long_break_minutes": 15
  }
}
```

### Personality Profiles

| Profile | Description |
|---------|-------------|
| `sergeant` | Strict drill sergeant with firm, commanding tone |
| `buddy` | Friendly, supportive friend with casual encouragement |
| `advisor` | Professional consultant with thoughtful guidance |
| `coach` | Motivational coach with energetic positivity |

---

## Permissions

Code Sergeant needs these macOS permissions:

| Permission | Purpose |
|------------|---------|
| Accessibility | Reading window titles for activity monitoring |
| Microphone | Voice commands and note recording |

Grant via: System Settings → Privacy & Security

---

## Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=code_sergeant --cov-report=html
```

---

## Roadmap

**v1.0.0** (Current)
- Native macOS activity monitoring
- Local LLM integration (Ollama)
- Voice feedback and commands
- Pomodoro timer
- SwiftUI menu bar app

**Planned**
- Analytics dashboard
- Session history visualization

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Development setup
git clone https://github.com/CuevaLabs/CodeSergeant.git
cd CodeSergeant
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest  # Verify setup
```

---

## Community

Building something with Code Sergeant? Have ADHD productivity tips to share? Found a bug?


- **Twitter/X**: Follow [@cuevalabsdev](https://x.com/cuevalabsdev) for updates
- **GitHub Issues**: Bug reports and feature requests welcome

This started as a personal tool to solve my own focus problems. If it helps you too, I'd love to hear about it.

---

## About This Project

This project was developed with assistance from AI tools (Cursor) for code suggestions and rapid iteration. All architecture decisions, creative direction, and refinements were human-led. I believe in transparency about AI-assisted development—it's a tool that amplifies productivity, not a replacement for thoughtful engineering.

---

## License

AGPL-3.0 - see [LICENSE](LICENSE) for details.

**Why AGPL?** I want Code Sergeant to stay open and benefit the community. If you build something commercial with this code, you're required to share your improvements back. That way, everyone benefits.

## Acknowledgments

- [Ollama](https://ollama.ai/) - Local LLM inference
- [Flask](https://flask.palletsprojects.com/) - Bridge server
- [ElevenLabs](https://elevenlabs.io/) - AI voice synthesis
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Speech recognition

---

<div align="center">

**Stay focused. Ship code.**

Built by [Carlos Cueva](https://github.com/CuevaLabs)

</div>
