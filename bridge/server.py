"""
Python-Swift Bridge Server for Code Sergeant.

Provides HTTP/WebSocket API for the SwiftUI frontend to communicate
with the Python backend services.

Run with: python bridge/server.py
"""
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request
from flask_cors import CORS

# Import Code Sergeant modules
from code_sergeant.config import load_config, save_config, set_env_var
from code_sergeant.controller import AppController
from code_sergeant.ai_client import create_ai_client
from code_sergeant.native_monitor import NativeMonitor
from code_sergeant.tts import TTSService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("code_sergeant.bridge")

app = Flask(__name__)
CORS(app)

# Global state
controller: Optional[AppController] = None
config: Dict[str, Any] = {}
native_monitor: Optional[NativeMonitor] = None
tts_service: Optional[TTSService] = None


def initialize_services():
    """Initialize all backend services."""
    global controller, config, native_monitor, tts_service
    
    logger.info("Initializing Code Sergeant services...")
    
    # Load config
    config = load_config()
    
    # Initialize native monitor
    native_monitor = NativeMonitor()
    
    # Initialize TTS
    tts_service = TTSService(
        provider=config["tts"].get("provider", "pyttsx3"),
        api_key=config["tts"].get("elevenlabs_api_key") or os.getenv("ELEVENLABS_API_KEY"),
        voice_id=config["tts"].get("voice_id"),
        model_id=config["tts"].get("model_id", "eleven_turbo_v2_5"),
        rate=config["tts"].get("rate", 150),
        volume=config["tts"].get("volume", 0.8)
    )
    
    # Initialize controller (it loads its own config internally)
    controller = AppController()
    
    logger.info("Services initialized successfully")


# ============================================================================
# Status & Health Endpoints
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current application status."""
    if not controller:
        return jsonify({"error": "Controller not initialized"}), 500
    
    # Get state snapshot
    state = controller.get_state_snapshot()
    
    # Calculate focus time from stats
    focus_time_minutes = 0
    if state.stats and state.stats.focus_seconds:
        focus_time_minutes = state.stats.focus_seconds // 60
    
    return jsonify({
        "session_active": state.session_active,
        "focus_time_minutes": focus_time_minutes,
        "current_goal": state.goal,
        "personality": state.personality_name,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/ai/status', methods=['GET'])
def get_ai_status():
    """Get AI backend status."""
    if not controller or not hasattr(controller, 'ai_client'):
        return jsonify({"error": "AI client not initialized"}), 500
    
    ai_status = controller.ai_client.get_status()
    ollama_available, ollama_msg = controller.ai_client.check_ollama_available()
    
    return jsonify({
        **ai_status,
        "ollama_server_message": ollama_msg
    })


# ============================================================================
# Session Management
# ============================================================================

@app.route('/api/session/start', methods=['POST'])
def start_session():
    """Start a new focus session."""
    if not controller:
        return jsonify({"error": "Controller not initialized"}), 500
    
    data = request.json or {}
    goal = data.get('goal', '')
    work_minutes = data.get('work_minutes', 25)
    break_minutes = data.get('break_minutes', 5)
    
    try:
        # Update pomodoro settings if provided
        if work_minutes and controller.pomodoro:
            controller.pomodoro.state.work_duration_minutes = work_minutes
        if break_minutes and controller.pomodoro:
            controller.pomodoro.state.short_break_minutes = break_minutes
        
        # Start session (only takes goal parameter)
        controller.start_session(goal=goal)
        
        logger.info(f"Session started: goal='{goal}', work={work_minutes}min, break={break_minutes}min")
        
        return jsonify({
            "success": True,
            "message": "Session started",
            "goal": goal,
            "work_minutes": work_minutes,
            "break_minutes": break_minutes
        })
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/session/end', methods=['POST'])
def end_session():
    """End current focus session."""
    if not controller:
        return jsonify({"error": "Controller not initialized"}), 500
    
    try:
        # Get stats before ending session
        state = controller.get_state_snapshot()
        stats = state.stats
        
        # End the session
        controller.end_session()
        logger.info("Session ended")
        
        # Build summary
        summary = {}
        if stats:
            focus_minutes = stats.focus_seconds // 60 if stats.focus_seconds else 0
            summary = {
                "focus_minutes": focus_minutes,
                "distractions": stats.distractions_count if stats.distractions_count else 0,
                "pomodoros_completed": stats.pomodoros_completed if stats.pomodoros_completed else 0
            }
        
        return jsonify({
            "success": True,
            "message": "Session ended",
            "summary": summary
        })
    except Exception as e:
        logger.error(f"Failed to end session: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/session/pause', methods=['POST'])
def pause_session():
    """Pause current session timer."""
    if not controller:
        return jsonify({"error": "Controller not initialized"}), 500
    
    try:
        controller.pause_session()
        return jsonify({"success": True, "message": "Session paused"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/session/resume', methods=['POST'])
def resume_session():
    """Resume paused session timer."""
    if not controller:
        return jsonify({"error": "Controller not initialized"}), 500
    
    try:
        controller.resume_session()
        return jsonify({"success": True, "message": "Session resumed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/session/skip-break', methods=['POST'])
def skip_break():
    """Skip current break."""
    if not controller:
        return jsonify({"error": "Controller not initialized"}), 500
    
    try:
        if controller.pomodoro and hasattr(controller.pomodoro, 'skip_break'):
            controller.pomodoro.skip_break()
        return jsonify({"success": True, "message": "Break skipped"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Timer & Pomodoro
# ============================================================================

@app.route('/api/timer', methods=['GET'])
def get_timer():
    """Get current timer state."""
    if not controller:
        return jsonify({"error": "Controller not initialized"}), 500
    
    pomodoro = getattr(controller, 'pomodoro', None)
    if not pomodoro or not pomodoro.state:
        return jsonify({
            "state": "stopped",
            "remaining_seconds": 0,
            "total_seconds": 0,
            "is_break": False,
            "work_minutes": 25,
            "break_minutes": 5
        })
    
    pomodoro_state = pomodoro.state
    is_break = pomodoro_state.current_state in ("short_break", "long_break")
    
    # Calculate total seconds based on current state
    if pomodoro_state.current_state == "work":
        total_seconds = pomodoro_state.work_duration_minutes * 60
    elif pomodoro_state.current_state == "short_break":
        total_seconds = pomodoro_state.short_break_minutes * 60
    elif pomodoro_state.current_state == "long_break":
        total_seconds = pomodoro_state.long_break_minutes * 60
    else:
        total_seconds = 0
    
    return jsonify({
        "state": pomodoro_state.current_state,
        "remaining_seconds": pomodoro_state.time_remaining_seconds,
        "total_seconds": total_seconds,
        "is_break": is_break,
        "work_minutes": pomodoro_state.work_duration_minutes,
        "break_minutes": pomodoro_state.short_break_minutes
    })


# ============================================================================
# Activity & Monitoring
# ============================================================================

@app.route('/api/activity/current', methods=['GET'])
def get_current_activity():
    """Get current activity."""
    if not native_monitor:
        return jsonify({"error": "Native monitor not initialized"}), 500
    
    return jsonify({
        "app": native_monitor.get_frontmost_app(),
        "window_title": native_monitor.get_active_window_title(),
        "idle_seconds": native_monitor.get_idle_seconds(),
        "is_idle": native_monitor.is_user_idle()
    })


@app.route('/api/screen-monitoring/status', methods=['GET'])
def get_screen_monitoring_status():
    """Get screen monitoring status."""
    if not controller or not hasattr(controller, 'screen_monitor'):
        return jsonify({"enabled": False, "status": "not_initialized"})
    
    sm = controller.screen_monitor
    return jsonify({
        "enabled": sm.is_enabled(),
        "use_local_vision": sm.use_local_vision,
        "backend_status": sm.get_vision_backend_status() if hasattr(sm, 'get_vision_backend_status') else "unknown",
        "check_interval_seconds": sm.check_interval,
        "last_analysis": sm.last_analysis.to_dict() if sm.last_analysis and hasattr(sm.last_analysis, 'to_dict') else None
    })


@app.route('/api/screen-monitoring/toggle', methods=['POST'])
def toggle_screen_monitoring():
    """Toggle screen monitoring."""
    data = request.json or {}
    enabled = data.get('enabled', True)
    
    if not controller or not hasattr(controller, 'screen_monitor'):
        return jsonify({"error": "Screen monitor not available"}), 500
    
    controller.screen_monitor.enable(enabled)
    
    return jsonify({
        "success": True,
        "enabled": controller.screen_monitor.is_enabled()
    })


# ============================================================================
# Settings & Config
# ============================================================================

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current config (sanitized - no API keys)."""
    sanitized = {**config}
    
    # Remove sensitive data
    if 'openai' in sanitized:
        sanitized['openai'] = {**sanitized['openai'], 'api_key': '***' if config.get('openai', {}).get('api_key') else None}
    if 'tts' in sanitized:
        sanitized['tts'] = {**sanitized['tts'], 'elevenlabs_api_key': '***' if config.get('tts', {}).get('elevenlabs_api_key') else None}
    
    return jsonify(sanitized)


@app.route('/api/config', methods=['PATCH'])
def update_config():
    """Update config values."""
    global config
    
    data = request.json or {}
    
    # Deep merge config
    for key, value in data.items():
        if isinstance(value, dict) and key in config:
            config[key].update(value)
        else:
            config[key] = value
    
    # Save to disk
    save_config(config)
    
    return jsonify({"success": True, "message": "Config updated"})


@app.route('/api/openai-key', methods=['POST'])
def set_openai_key():
    """Set OpenAI API key securely."""
    data = request.json or {}
    api_key = data.get('api_key', '')
    
    if not api_key:
        return jsonify({"error": "API key required"}), 400
    
    try:
        # Save to .env file (secure)
        set_env_var("OPENAI_API_KEY", api_key)
        
        # Update AI client if available
        if controller and hasattr(controller, 'ai_client'):
            success = controller.ai_client.set_openai_key(api_key)
            if success:
                return jsonify({
                    "success": True,
                    "message": "OpenAI API key saved securely"
                })
        
        return jsonify({
            "success": True,
            "message": "OpenAI API key saved to .env (restart required)"
        })
    except Exception as e:
        logger.error(f"Failed to set OpenAI key: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# TTS & Voice
# ============================================================================

@app.route('/api/tts/speak', methods=['POST'])
def speak():
    """Speak text using TTS."""
    data = request.json or {}
    text = data.get('text', '')
    
    if not text:
        return jsonify({"error": "Text required"}), 400
    
    if not tts_service:
        return jsonify({"error": "TTS service not initialized"}), 500
    
    tts_service.speak(text)
    return jsonify({"success": True, "message": "Speaking..."})


@app.route('/api/tts/stop', methods=['POST'])
def stop_speaking():
    """Stop current TTS audio."""
    if tts_service:
        tts_service.cancel_all()
    return jsonify({"success": True, "message": "Audio stopped"})


# ============================================================================
# Personality
# ============================================================================

@app.route('/api/personality', methods=['GET'])
def get_personality():
    """Get current personality profile."""
    if not controller or not hasattr(controller, 'personality_manager'):
        return jsonify({"error": "Personality manager not available"}), 500
    
    pm = controller.personality_manager
    return jsonify({
        "name": pm.get_profile_name() if hasattr(pm, 'get_profile_name') else "unknown",
        "available_profiles": pm.get_available_profiles() if hasattr(pm, 'get_available_profiles') else []
    })


@app.route('/api/personality', methods=['POST'])
def set_personality():
    """Change personality profile."""
    data = request.json or {}
    profile_name = data.get('profile', 'drill_sergeant')
    
    if not controller or not hasattr(controller, 'personality_manager'):
        return jsonify({"error": "Personality manager not available"}), 500
    
    try:
        controller.personality_manager.set_profile(profile_name)
        return jsonify({"success": True, "profile": profile_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# WebSocket (for real-time updates)
# ============================================================================

# Note: For production, consider using flask-socketio for true WebSocket support
# This basic implementation uses polling, which works for the MVP

@app.route('/api/events/poll', methods=['GET'])
def poll_events():
    """Poll for events (simple alternative to WebSocket)."""
    if not controller:
        return jsonify({"events": []})
    
    events = []
    
    # Check session state
    if controller.is_session_active():
        events.append({
            "type": "session_active",
            "data": {
                "goal": getattr(controller, 'session_goal', ''),
                "elapsed_minutes": controller.get_focus_time_minutes() if hasattr(controller, 'get_focus_time_minutes') else 0
            }
        })
    
    return jsonify({"events": events, "timestamp": datetime.now().isoformat()})


# ============================================================================
# Main
# ============================================================================

def check_and_free_port(port: int) -> bool:
    """
    Check if port is in use and attempt to free it if it's a Python process.
    
    Returns:
        True if port is free or was freed, False otherwise
    """
    try:
        import subprocess
        # Find processes using the port
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True,
            timeout=2
        )
        
        if result.returncode != 0 or not result.stdout.strip():
            return True  # Port is free
        
        pids = result.stdout.strip().split('\n')
        
        # Check if any are Python processes (likely stale bridge servers)
        python_pids = []
        for pid in pids:
            try:
                # Check the command name
                cmd_result = subprocess.run(
                    ['ps', '-p', pid, '-o', 'comm='],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                if cmd_result.returncode == 0:
                    cmd = cmd_result.stdout.strip().lower()
                    if 'python' in cmd or 'python3' in cmd:
                        python_pids.append(pid)
            except Exception:
                pass
        
        if python_pids:
            logger.warning(f"Found Python process(es) using port {port}: {', '.join(python_pids)}")
            logger.info("Attempting to free the port...")
            
            # Try to kill Python processes
            for pid in python_pids:
                try:
                    subprocess.run(['kill', '-9', pid], timeout=2, check=False)
                    logger.info(f"Killed process {pid}")
                except Exception as e:
                    logger.warning(f"Failed to kill process {pid}: {e}")
            
            # Wait a moment for port to be released
            import time
            time.sleep(0.5)
            
            # Verify port is now free
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode != 0 or not result.stdout.strip():
                logger.info("Port is now free!")
                return True
            else:
                logger.warning("Port still in use after kill attempt")
                return False
        else:
            # Non-Python process using the port
            logger.error(f"Port {port} is in use by non-Python process(es): {', '.join(pids)}")
            return False
            
    except Exception as e:
        logger.debug(f"Error checking port: {e}")
        return False


def main():
    """Start the bridge server."""
    # Initialize services
    try:
        initialize_services()
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        logger.error("Make sure you're running from the project root and dependencies are installed")
        sys.exit(1)
    
    # Run server
    port = int(os.environ.get('BRIDGE_PORT', 5050))
    
    # Check if port is available, try to free it if it's a Python process
    if not check_and_free_port(port):
        logger.error(f"Port {port} is already in use!")
        logger.error("Another instance may be running, or another app is using this port.")
        logger.error(f"To use a different port, set BRIDGE_PORT environment variable:")
        logger.error(f"  export BRIDGE_PORT=5051")
        logger.error(f"  python bridge/server.py")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info(f"🚀 Code Sergeant Bridge Server")
    logger.info(f"   Listening on: http://127.0.0.1:{port}")
    logger.info(f"   Status: http://127.0.0.1:{port}/api/health")
    logger.info("=" * 60)
    
    try:
        app.run(
            host='127.0.0.1',  # Only local connections
            port=port,
            debug=os.environ.get('DEBUG', 'false').lower() == 'true',
            threaded=True,
            use_reloader=False  # Disable reloader for production
        )
    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(f"Port {port} is still in use after cleanup attempt!")
            logger.error("Please manually kill the process or use a different port.")
        else:
            logger.error(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

