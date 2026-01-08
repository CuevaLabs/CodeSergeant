"""Code Sergeant - macOS menu bar focus assistant.

A self-contained productivity app with:
- Native macOS activity monitoring (no external dependencies)
- AI-powered judgment (OpenAI + Ollama fallback)
- ElevenLabs text-to-speech
- Privacy-focused screen monitoring
- PyObjC dashboard with animations
"""

__version__ = "1.0.0"

from .ai_client import AIClient, create_ai_client
from .controller import AppController
from .dashboard import DashboardWindow, create_dashboard
from .menu_bar import CodeSergeantApp
from .motivation_monitor import MotivationMonitor
from .native_monitor import NativeMonitor
from .screen_monitor import ScreenMonitor, create_screen_monitor

__all__ = [
    "CodeSergeantApp",
    "AppController",
    "NativeMonitor",
    "AIClient",
    "create_ai_client",
    "MotivationMonitor",
    "ScreenMonitor",
    "create_screen_monitor",
    "DashboardWindow",
    "create_dashboard",
]
