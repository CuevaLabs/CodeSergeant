# Code Sergeant Python Bridge

HTTP/WebSocket bridge server for communication between SwiftUI frontend and Python backend.

## Quick Start

### Option 1: Use the startup script (Recommended)

```bash
cd /Users/cuevalabs/Desktop/Projects/CodeSergeant
./start_bridge.sh
```

### Option 2: Manual start

```bash
cd /Users/cuevalabs/Desktop/Projects/CodeSergeant
source .venv/bin/activate
python bridge/server.py
```

### Option 3: Auto-start from SwiftUI app

The SwiftUI app will automatically start the bridge server when launched.

## Configuration

### Port

Default port is `5050`. To change it:

```bash
export BRIDGE_PORT=8080
python bridge/server.py
```

### Debug Mode

Enable debug logging:

```bash
export DEBUG=true
python bridge/server.py
```

## API Endpoints

### Health Check
```
GET /api/health
```

### Session Management
```
GET  /api/status
POST /api/session/start
POST /api/session/end
POST /api/session/pause
POST /api/session/resume
POST /api/session/skip-break
```

### Timer
```
GET /api/timer
```

### AI Status
```
GET /api/ai/status
POST /api/openai-key
```

### Screen Monitoring
```
GET  /api/screen-monitoring/status
POST /api/screen-monitoring/toggle
```

### TTS
```
POST /api/tts/speak
POST /api/tts/stop
```

### Configuration
```
GET   /api/config
PATCH /api/config
```

## Troubleshooting

### Port Already in Use

If you see "Address already in use":
1. Check if another instance is running: `lsof -i :5050`
2. Kill the process: `kill -9 <PID>`
3. Or use a different port: `BRIDGE_PORT=8080 python bridge/server.py`

### Services Not Initializing

Make sure:
1. You're in the project root directory
2. Virtual environment is activated: `source .venv/bin/activate`
3. Dependencies are installed: `pip install -r requirements.txt`
4. Config file exists: `config.json`

### SwiftUI App Can't Connect

1. Verify bridge is running: `curl http://127.0.0.1:5050/api/health`
2. Check firewall settings
3. Ensure bridge started before SwiftUI app

## Development

The bridge server runs Flask in threaded mode for concurrent requests. For production, consider using:
- Gunicorn
- uWSGI
- Or a proper ASGI server

