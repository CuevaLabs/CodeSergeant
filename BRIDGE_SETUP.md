# Python Bridge Setup Guide

## Quick Setup

The Python bridge connects your SwiftUI app to the Python backend. Here's how to set it up:

### 1. Install Dependencies

```bash
cd /Users/cuevalabs/Desktop/Projects/CodeSergeant
source .venv/bin/activate
pip install flask flask-cors
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

### 2. Start the Bridge Server

**Option A: Use the startup script**
```bash
./start_bridge.sh
```

**Option B: Manual start**
```bash
source .venv/bin/activate
python bridge/server.py
```

**Option C: Auto-start (recommended)**
The SwiftUI app will automatically start the bridge when you launch it.

### 3. Verify It's Running

Open a browser or use curl:
```bash
curl http://127.0.0.1:5050/api/health
```

You should see:
```json
{"status": "healthy", "timestamp": "..."}
```

## Running Both Apps

### Terminal 1: Python Bridge
```bash
cd /Users/cuevalabs/Desktop/Projects/CodeSergeant
source .venv/bin/activate
python bridge/server.py
```

### Terminal 2: SwiftUI App (or Xcode)
- Open `CodeSergeantUI.xcodeproj` in Xcode
- Press ⌘R to build and run

Or if you prefer, the SwiftUI app can auto-start the bridge (see CodeSergeantApp.swift).

## Troubleshooting

### "Port 5050 already in use"
```bash
# Find what's using the port
lsof -i :5050

# Kill it
kill -9 <PID>
```

### "Module not found: flask"
```bash
source .venv/bin/activate
pip install flask flask-cors
```

### Bridge starts but SwiftUI can't connect
1. Check bridge is running: `curl http://127.0.0.1:5050/api/health`
2. Make sure firewall allows localhost connections
3. Restart both bridge and SwiftUI app

## Configuration

The bridge server reads from:
- `config.json` - App configuration
- `.env` - API keys (OPENAI_API_KEY, etc.)

Default port: `5050` (change with `BRIDGE_PORT` env var)

