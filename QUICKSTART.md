# Quick Start Guide

Get Code Sergeant running in under 5 minutes.

## Step 1: Install Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Set Up AI (Choose Your Backend)

Code Sergeant can use local AI (Ollama) or cloud AI (OpenAI). Pick one or both.

### Option A: Ollama (Local, Free, Private)

Best for privacy. Everything runs on your machine.

1. Download from [ollama.ai](https://ollama.ai/)
2. Pull a model:

```bash
ollama pull llama3.2
```

### Option B: OpenAI (Cloud, Faster, Paid)

Better responses, requires API key.

1. Get an API key from [platform.openai.com](https://platform.openai.com/)
2. Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=sk-your-key-here
```

Or add it to `config.json`:

```json
{
  "openai": {
    "api_key": "sk-your-key-here",
    "model": "gpt-4o-mini"
  }
}
```

## Step 3: Set Up Voice (Optional)

Code Sergeant talks to you. Choose your voice backend.

### Default: System Voice (Free)

Works out of the box using macOS system voices. No setup needed.

### ElevenLabs (Premium AI Voices)

For high-quality, personality-matched voices:

1. Get an API key from [elevenlabs.io](https://elevenlabs.io/)
2. Add to `.env`:

```bash
ELEVENLABS_API_KEY=your-key-here
```

3. Configure voices in `config.json`:

```json
{
  "tts": {
    "provider": "elevenlabs",
    "voice_id": "YOUR_VOICE_ID",
    "model_id": "eleven_turbo_v2_5"
  }
}
```

**Personality Voice IDs** (placeholders - update with your preferred voices):
- Sergeant: `DGzg6RaUqxGRTHSBjfgF` (firm, commanding)
- Buddy: `TBD` (warm, friendly)
- Advisor: `TBD` (calm, professional)
- Coach: `TBD` (energetic, motivational)

## Step 4: Run Code Sergeant

```bash
python3 main.py
```

The app will:
- Appear in your menu bar with a sword icon
- Auto-generate `config.json` on first run
- Start monitoring using native macOS APIs

## Start Your First Session

1. Click the menu bar icon
2. Select "Start Session"
3. Enter your focus goal (e.g., "Build the login feature")
4. Code Sergeant monitors your activity and keeps you on track

## What to Expect

- **Native Monitoring**: Tracks your active app and window title using macOS APIs
- **Smart Judgment**: AI classifies whether your activity matches your goal
- **Voice Feedback**: Speaks warnings when you get distracted (system voice if no ElevenLabs)
- **Voice Commands**: Say "Hey Sergeant" to interact hands-free

## Permissions

Code Sergeant needs these macOS permissions:

| Permission | Purpose | How to Grant |
|------------|---------|--------------|
| Accessibility | Read window titles | System Settings → Privacy & Security → Accessibility |
| Microphone | Voice commands | System Settings → Privacy & Security → Microphone |

## Troubleshooting

**No AI responses?**
- Make sure Ollama is running (`ollama serve`) OR OpenAI key is set
- Check your `.env` file is in the project root
- The app works without AI using rule-based classification

**No voice output?**
- System voice works without setup - check your Mac volume
- For ElevenLabs, verify your API key is correct

**No window titles?**
- Grant Accessibility permission to Terminal or your IDE

**Microphone not working?**
- Grant Microphone permission when prompted
- Check System Settings → Privacy & Security → Microphone
