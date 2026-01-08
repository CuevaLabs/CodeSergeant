# Code Sergeant v1.0.0

**Release Date**: January 2025

---

## Your AI Body Double for Deep Work

If you've ever tried body doubling—having someone present while you work to help you focus—you know it works. But finding a consistent body double is hard, and Zoom coworking sessions with strangers feel weird.

Code Sergeant is an AI body double that actually pays attention. It watches what you're doing, understands context, and calls you out when you drift. No strangers. No judgment. Just accountability.

**Built for:**
- Developers who want to ship more and scroll less
- People with ADHD who need external accountability
- Vibe coders who work best with company (even artificial company)
- Anyone tired of losing hours to "just one quick Twitter check"

---

## What's New in v1.0.0

### Smart Activity Monitoring
Your AI companion knows the difference between productive work and distraction. Reading Stack Overflow while coding? That's fine. Scrolling Reddit? Time for a nudge.

- Native macOS integration (no external apps needed)
- Context-aware judgment powered by local AI
- Recognizes "thinking time" vs actual distraction

### Voice Interaction
Talk to your AI body double like it's actually there.

- **Wake word**: "Hey Sergeant" (customizable per personality)
- **Voice notes**: Capture thoughts without touching the keyboard
- **Spoken feedback**: Hear warnings, encouragement, session summaries

### Multiple Personalities
Not everyone responds to drill sergeant energy. Pick your vibe:

- **Sergeant** - Strict, no-nonsense, military motivation
- **Buddy** - Supportive friend who's got your back
- **Advisor** - Calm, professional guidance
- **Coach** - Energetic hype person

### Privacy First
Your focus struggles stay on your machine. All AI processing can run locally via Ollama—no data sent to the cloud unless you choose to use OpenAI or ElevenLabs.

---

## Quick Install

```bash
git clone https://github.com/CuevaLabs/CodeSergeant.git
cd CodeSergeant
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

For smarter AI, install [Ollama](https://ollama.ai/) and run `ollama pull llama3.2`.

---

## Requirements

- macOS 12+ (Monterey or later)
- Python 3.10+
- Ollama or OpenAI API key (optional but recommended)
- ElevenLabs API key (optional, for premium voices)

---

## Known Limitations

- macOS only for now (Windows/Linux on the roadmap)
- Wake word can false-trigger in noisy environments
- First launch takes a few seconds while models load

---

## What's Coming

- Analytics dashboard to track your focus patterns
- Session history visualization
- iOS companion app
- Cross-platform support
- Community-requested personalities

---

## Join the Community

Building something with Code Sergeant? Have focus tips that actually work? Found a bug?

- **Discord**: Coming soon
- **Twitter/X**: Share your wins with #CodeSergeant
- **GitHub Issues**: Bug reports and feature requests welcome

---

## Acknowledgments

- [Ollama](https://ollama.ai/) for making local AI accessible
- [ElevenLabs](https://elevenlabs.io/) for voices that don't sound like robots
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) for speech recognition
- Everyone in the ADHD productivity community who inspired this

---

**Stay focused. Ship code. You've got this.**
