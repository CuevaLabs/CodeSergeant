# Troubleshooting Guide

Common issues and their solutions.

## Permissions Issues

### No Window Titles Detected

Code Sergeant uses native macOS APIs to read window titles. If titles aren't appearing:

1. **Grant Accessibility Permission**
   - System Settings → Privacy & Security → Accessibility
   - Enable Terminal (or your IDE if running from there)
   - Restart the app

2. **Verify it's working**
   ```bash
   python3 main.py
   ```
   Check logs for "Current activity:" entries with window titles.

### Microphone Not Working

Voice commands require microphone access:

1. **Grant Microphone Permission**
   - System Settings → Privacy & Security → Microphone
   - Enable Terminal or your IDE
   
2. **Test voice**
   - Start a session
   - Click "Talk to Sergeant" or say "Hey Sergeant"
   - Speak clearly and wait for the response

## AI/LLM Issues

### Ollama Not Responding

If Ollama isn't available, Code Sergeant uses rule-based classification (still works, just less smart).

**To enable Ollama:**

1. Install from [ollama.ai](https://ollama.ai/)
2. Start the server:
   ```bash
   ollama serve
   ```
3. Pull a model:
   ```bash
   ollama pull llama3.2
   ```
4. Verify:
   ```bash
   ollama list
   ```

### OpenAI API Issues

If using OpenAI instead of Ollama:

1. Set your API key in `.env`:
   ```
   OPENAI_API_KEY=sk-...
   ```
2. Or set it in `config.json` under `openai.api_key`

## TTS Issues

### No Voice Output

1. **Check volume** - System volume might be muted
2. **Check TTS provider** in `config.json`:
   - `pyttsx3`: Uses system voices (always available)
   - `elevenlabs`: Requires API key

### ElevenLabs Not Working

1. Set API key in `.env`:
   ```
   ELEVENLABS_API_KEY=...
   ```
2. Or fall back to `pyttsx3` in config:
   ```json
   "tts": {
     "provider": "pyttsx3"
   }
   ```

## General Issues

### App Won't Start

```bash
# Check Python version (need 3.10+)
python3 --version

# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### Session Not Tracking

1. Make sure a session is active (menu shows "End Session" option)
2. Check logs for errors:
   ```bash
   tail -f logs/code_sergeant_*.log
   ```

### High CPU Usage

This can happen if the polling interval is too aggressive. Edit `config.json`:

```json
{
  "poll_interval_sec": 1.0,
  "judge_interval_sec": 15
}
```

