# Testing Bridge Server Cleanup

This guide helps you verify that the Python bridge server properly terminates when you stop the Xcode project.

## Prerequisites

- Xcode installed and configured
- Python virtual environment set up (`.venv` directory exists)
- Bridge server dependencies installed (`flask`, `flask-cors`)

## Manual Testing Steps

### Step 1: Verify No Existing Processes

Before starting, make sure no bridge server is running:

```bash
# Check for processes on port 5050
lsof -ti :5050

# If any processes are found, kill them:
kill -9 $(lsof -ti :5050)
```

### Step 2: Build and Run in Xcode

1. Open `CodeSergeantUI/CodeSergeantUI.xcodeproj` in Xcode
2. Select "My Mac" as the target
3. Build and Run (⌘R)

### Step 3: Verify Bridge Server Started

After the app launches, check the Xcode console output. You should see:

```
✅ Bridge server starting at /path/to/CodeSergeant
   Process ID: <PID>
```

Verify the process is running:

```bash
# Check if bridge server is running
lsof -ti :5050

# Verify it's a Python process
ps -p $(lsof -ti :5050) -o comm=
```

You should see a Python process running.

### Step 4: Test Cleanup - Stop the App

**Option A: Normal Stop (⌘.)**
1. In Xcode, press ⌘. (Command + Period) to stop the app
2. Check the console output - you should see:
   ```
   🛑 Stopping bridge server...
   ✅ Bridge server cleanup complete
   ```

**Option B: Force Quit**
1. Force quit the app (⌘Q or Activity Monitor)
2. The signal handlers should catch the termination

### Step 5: Verify Process Was Terminated

After stopping the app, verify the Python process is gone:

```bash
# Check port 5050 - should return nothing
lsof -ti :5050 || echo "✅ Port 5050 is free - cleanup successful!"

# Check for any CodeSergeant Python processes
pgrep -fl "bridge/server.py" || echo "✅ No bridge server processes found"
```

## Automated Test Script

You can also use the automated test script:

```bash
./scripts/test_bridge_cleanup.sh
```

This script:
1. Checks if port 5050 is free
2. Starts the bridge server manually
3. Tests the cleanup mechanism
4. Verifies the process was terminated

## Expected Behavior

### When App Starts:
- ✅ Bridge server process starts
- ✅ Process ID is logged to console
- ✅ Process reference is stored in AppDelegate

### When App Stops:
- ✅ HTTP shutdown attempted (may fail silently if endpoint doesn't exist)
- ✅ Process is terminated gracefully
- ✅ If still running, process is force-killed
- ✅ Port-based cleanup runs as fallback
- ✅ All Python processes on port 5050 are terminated

### Console Output Example:

```
🛑 Stopping bridge server...
🔄 Terminating bridge process (PID: 12345)...
✅ Bridge process terminated
🔍 Checking for Python processes on port 5050...
   No processes found on port 5050
✅ Bridge server cleanup complete
```

## Troubleshooting

### Process Still Running After Stop

If the Python process is still running after stopping the app:

1. **Check if signal handlers are working:**
   - Signal handlers may not work in all scenarios
   - The port-based cleanup should catch orphaned processes

2. **Manual cleanup:**
   ```bash
   # Kill by port
   kill -9 $(lsof -ti :5050)
   
   # Or kill all Python processes (be careful!)
   pkill -f "bridge/server.py"
   ```

3. **Check Xcode console:**
   - Look for error messages in the console
   - Verify `stopBridgeServer()` was called

### Bridge Server Won't Start

1. **Check virtual environment:**
   ```bash
   ls -la .venv/bin/python
   ```

2. **Check dependencies:**
   ```bash
   source .venv/bin/activate
   python -c "import flask, flask_cors"
   ```

3. **Check project root detection:**
   - The app searches for `bridge/server.py` starting from the bundle path
   - If running from Xcode, it searches up from `DerivedData`
   - Verify the path is correct in console output

## Success Criteria

✅ App builds without errors  
✅ Bridge server starts when app launches  
✅ Process ID is logged  
✅ Bridge server responds on port 5050  
✅ Process terminates when app stops  
✅ Port 5050 is free after app stops  
✅ No orphaned Python processes remain  

## Notes

- The cleanup uses multiple strategies to ensure termination
- Signal handlers provide backup cleanup if `applicationWillTerminate` doesn't run
- Port-based cleanup catches any orphaned processes
- The HTTP shutdown endpoint may not exist yet - that's okay, other methods will handle it
