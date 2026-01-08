"""Configuration management for Code Sergeant."""
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip
    pass

logger = logging.getLogger("code_sergeant.config")

SENSITIVE_CONFIG_KEYS = [
    ("openai", "api_key"),
    ("tts", "elevenlabs_api_key"),
    ("tts", "api_key"),
]


def _scrub_secrets(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a copy of config with known secrets removed.

    This prevents API keys from being written to disk and from leaking into logs/session dumps.
    """
    clean = deep_merge({}, config) if isinstance(config, dict) else {}
    for section, key in SENSITIVE_CONFIG_KEYS:
        if isinstance(clean.get(section), dict) and key in clean[section]:
            clean[section][key] = None
    return clean


def set_env_var(env_key: str, value: str, env_path: str = ".env") -> None:
    """
    Persist an environment variable to .env securely.

    - Creates the file if missing
    - Ensures permissions are 0600
    - Replaces existing key, otherwise appends
    - Never logs the secret value
    """
    if not env_key:
        raise ValueError("env_key is required")

    value = (value or "").strip()
    env_file = Path(env_path)

    # Read existing lines (if any)
    lines: list[str] = []
    if env_file.exists():
        try:
            lines = env_file.read_text().splitlines()
        except Exception:
            lines = []

    # Update or append
    new_line = f"{env_key}={value}"
    found = False
    updated_lines: list[str] = []
    for line in lines:
        if line.startswith(f"{env_key}="):
            updated_lines.append(new_line)
            found = True
        else:
            updated_lines.append(line)

    if not found:
        updated_lines.append(new_line)

    env_file.write_text("\n".join(updated_lines) + "\n")

    # Lock down permissions (best-effort)
    try:
        os.chmod(env_file, 0o600)
    except Exception:
        pass

    # Also update current process env
    os.environ[env_key] = value



DEFAULT_CONFIG = {
    "poll_interval_sec": 0.5,  # 500ms for real-time activity detection
    "judge_interval_sec": 10,
    "cooldown_seconds": 30,
    "reminder_intervals_sec": [300, 600, 900],  # 5, 10, 15 minutes
    "voice": {
        "record_seconds": 3,
        "sample_rate": 16000,
        "note_record_seconds": 120
    },
    "openai": {
        "api_key": None,  # Stored in .env as OPENAI_API_KEY (never in config.json)
        "model": "gpt-4o-mini"
    },
    "ollama": {
        "model": "llama3.2",
        "base_url": "http://localhost:11434"
    },
    "tts": {
        "provider": "pyttsx3",
        "rate": 150,
        "volume": 0.8,
        "elevenlabs_api_key": None,  # Stored in .env as ELEVENLABS_API_KEY (never in config.json)
        "voice_id": None,
        "model_id": "eleven_turbo_v2_5"
    },
    "personality": {
        "name": "sergeant",
        "wake_word_name": "sergeant",
        "description": "",
        "tone": ["strict", "firm", "commanding"]
    },
    "voice_activation": {
        "enabled": False,
        "sensitivity": 0.5
    },
    "pomodoro": {
        "work_duration_minutes": 25,
        "short_break_minutes": 5,
        "long_break_minutes": 15,
        "auto_start_with_session": False,
        "pomodoros_until_long_break": 4
    },
    "screen_monitoring": {
        "enabled": False,
        "app_blocklist": [
            "1Password", "Keychain Access", "LastPass", "Bitwarden",
            "PayPal", "Venmo", "Cash App",
            "Chase", "Bank of America", "Wells Fargo", "Citibank",
            "Capital One", "US Bank", "PNC", "TD Bank"
        ],
        "blur_regions": [],
        "use_local_vision": True,
        "check_interval_seconds": 120
    },
    "motivation": {
        "enabled": True,
        "check_interval_minutes": 3
    }
}


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """
    Load configuration from file, creating defaults if missing.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        logger.info(f"Config file not found at {config_path}, creating defaults")
        save_config(DEFAULT_CONFIG, config_path)
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Validate and merge with defaults (deep merge)
        validated_config = deep_merge(DEFAULT_CONFIG.copy(), config)

        # SECURITY: Never keep secrets in config dict (prevents leaking into session logs)
        validated_config = _scrub_secrets(validated_config)
        
        logger.info(f"Config loaded from {config_path}")
        return validated_config
        
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in config file: {e}. Using defaults.")
        save_config(DEFAULT_CONFIG, config_path)
        return DEFAULT_CONFIG.copy()
    except Exception as e:
        logger.error(f"Error loading config: {e}. Using defaults.")
        return DEFAULT_CONFIG.copy()


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.
    
    Args:
        base: Base dictionary
        override: Dictionary to merge on top
        
    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def save_config(config: Dict[str, Any], config_path: str = "config.json") -> None:
    """
    Save configuration to file.
    
    Args:
        config: Configuration dictionary
        config_path: Path to save config file
    """
    try:
        # SECURITY: Never write secrets to disk
        config_to_write = _scrub_secrets(config)
        with open(config_path, 'w') as f:
            json.dump(config_to_write, f, indent=2)
        logger.info(f"Config saved to {config_path}")
    except Exception as e:
        logger.error(f"Error saving config: {e}")


def get_wake_word(config: Dict[str, Any]) -> str:
    """
    Get the wake word based on personality settings.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Wake word string (e.g., "hey sergeant")
    """
    personality = config.get("personality", {})
    wake_word_name = personality.get("wake_word_name", "sergeant")
    return f"hey {wake_word_name}"


def get_personality_name(config: Dict[str, Any]) -> str:
    """
    Get the current personality name.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Personality name
    """
    return config.get("personality", {}).get("name", "sergeant")


def update_personality(config: Dict[str, Any], personality_name: str, 
                       custom_description: str = None, custom_wake_word: str = None,
                       config_path: str = "config.json") -> Dict[str, Any]:
    """
    Update personality settings.
    
    Args:
        config: Current configuration
        personality_name: Name of personality (sergeant, buddy, advisor, coach, custom)
        custom_description: Custom description (only for custom personality)
        custom_wake_word: Custom wake word name (only for custom personality)
        config_path: Path to config file
        
    Returns:
        Updated configuration
    """
    from .models import PersonalityProfile
    
    if personality_name == "custom":
        config["personality"] = {
            "name": "custom",
            "wake_word_name": custom_wake_word or "assistant",
            "description": custom_description or "",
            "tone": []
        }
    else:
        profile = PersonalityProfile.get_predefined(personality_name)
        config["personality"] = {
            "name": profile.name,
            "wake_word_name": profile.wake_word_name,
            "description": profile.description,
            "tone": profile.tone
        }
    
    save_config(config, config_path)
    return config
