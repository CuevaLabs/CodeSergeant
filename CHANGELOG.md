# Changelog

All notable changes to Code Sergeant will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-07

First public release. An AI body double for developers who need accountability.

### Added
- Native macOS activity monitoring using AppKit/Quartz APIs
- AI-powered activity judgment (Ollama local or OpenAI cloud)
- Text-to-speech feedback (ElevenLabs premium or system voices)
- Pomodoro timer with configurable durations
- Voice interaction with wake word detection ("Hey Sergeant")
- Voice note capture with automatic transcription
- Multiple personality profiles (Sergeant, Buddy, Advisor, Coach)
- SwiftUI menu bar application
- Python-Swift bridge server (Flask)
- Session logging and statistics
- 157 tests passing

### Technical
- Self-contained monitoring (no external dependencies)
- Privacy-first architecture with local AI processing
- Thread-safe worker architecture with event queue
- Graceful fallback when AI services unavailable

### License
- Released under AGPL-3.0 to keep the project open and community-focused

---

## Contributing to the Changelog

When contributing, add entries to an `[Unreleased]` section using these categories:

- **Added** - New features
- **Changed** - Changes to existing functionality
- **Deprecated** - Features to be removed
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Vulnerability fixes
