"""Unified AI client with OpenAI primary and Ollama fallback.

Provides a consistent interface for:
- Chat completions (judgment, conversation)
- Vision analysis (screen monitoring)
- Motivation detection
"""
import base64
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("code_sergeant.ai_client")

# Try to import OpenAI
try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
    logger.info("OpenAI SDK loaded successfully")
except ImportError as e:
    OPENAI_AVAILABLE = False
    logger.warning(f"OpenAI not installed: {e}. Install with: pip install openai")

# Try to import Ollama
try:
    import ollama

    OLLAMA_AVAILABLE = True
    logger.info("Ollama SDK loaded successfully")
except ImportError as e:
    OLLAMA_AVAILABLE = False
    logger.warning(f"Ollama not installed: {e}. Install with: pip install ollama")


class AIClient:
    """
    Unified AI client with OpenAI as primary and Ollama as fallback.

    Usage:
        client = AIClient(openai_api_key="sk-...")
        response = client.chat([{"role": "user", "content": "Hello"}])

        # For vision (uses local LLaVA for privacy)
        analysis = client.analyze_image(screenshot_bytes, "What is the user working on?")
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        openai_model: str = "gpt-4o-mini",
        ollama_model: str = "llama3.2",
        ollama_vision_model: str = "llava",
        ollama_base_url: str = "http://localhost:11434",
    ):
        """
        Initialize AI client.

        Args:
            openai_api_key: OpenAI API key (if provided, uses OpenAI as primary)
            openai_model: Model to use for OpenAI (default: gpt-4o-mini)
            ollama_model: Model to use for Ollama text (default: llama3.2)
            ollama_vision_model: Model for vision tasks (default: llava)
            ollama_base_url: Ollama server URL
        """
        # Prefer explicit key, otherwise fall back to environment (.env via python-dotenv in config)
        if not openai_api_key:
            openai_api_key = os.getenv("OPENAI_API_KEY")

        self.openai_api_key = openai_api_key
        self.openai_model = openai_model
        self.ollama_model = ollama_model
        self.ollama_vision_model = ollama_vision_model
        self.ollama_base_url = ollama_base_url

        self.openai_client: Optional[OpenAI] = None
        self.ollama_client = None

        # Initialize OpenAI if key provided
        if openai_api_key and OPENAI_AVAILABLE:
            try:
                self.openai_client = OpenAI(api_key=openai_api_key)
                logger.info(f"OpenAI client initialized with model: {openai_model}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
                self.openai_client = None

        # Always try to initialize Ollama as fallback
        if OLLAMA_AVAILABLE:
            try:
                self.ollama_client = ollama.Client(host=ollama_base_url)
                logger.info(f"Ollama client initialized at: {ollama_base_url}")
            except Exception as e:
                logger.warning(f"Failed to initialize Ollama: {e}")
                self.ollama_client = None

    def set_openai_key(self, api_key: str) -> bool:
        """
        Set or update OpenAI API key.

        Args:
            api_key: OpenAI API key

        Returns:
            True if successful
        """
        try:
            self.openai_api_key = api_key
            # Always set env for current process (persistence handled elsewhere)
            os.environ["OPENAI_API_KEY"] = api_key

            if OPENAI_AVAILABLE:
                self.openai_client = OpenAI(api_key=api_key)
                logger.info("OpenAI API key updated (client initialized)")
            else:
                # Key is stored, but SDK isn't available yet. App will use Ollama until installed.
                self.openai_client = None
                logger.warning(
                    "OpenAI API key saved, but OpenAI SDK is not installed (still using Ollama)"
                )
            return True
        except Exception as e:
            logger.error(f"Failed to set OpenAI key: {e}")
            return False

    def is_openai_available(self) -> bool:
        """Check if OpenAI is available and configured."""
        return self.openai_client is not None

    def is_ollama_available(self) -> bool:
        """Check if Ollama is available."""
        available, _ = self.check_ollama_available()
        return available

    def check_ollama_available(self) -> tuple:
        """
        Check if Ollama server is running and accessible.

        Returns:
            Tuple of (is_available: bool, message: str)
        """
        if not OLLAMA_AVAILABLE:
            return False, "Ollama SDK not installed. Install with: pip install ollama"

        if not self.ollama_client:
            return False, "Ollama client not initialized"

        try:
            # Quick health check - list available models
            self.ollama_client.list()
            return True, "Ollama is running and accessible"
        except Exception as e:
            error_msg = str(e)
            if "refused" in error_msg.lower() or "connect" in error_msg.lower():
                return (
                    False,
                    f"Ollama server not running. Start with: ollama serve (Download from https://ollama.com/download)",
                )
            return False, f"Ollama not accessible: {error_msg}"

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        json_mode: bool = False,
    ) -> str:
        """
        Send chat completion request.

        Uses OpenAI if available, falls back to Ollama.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Optional model override
            temperature: Response temperature (0-2)
            max_tokens: Maximum response tokens
            json_mode: Whether to request JSON output

        Returns:
            Response content string

        Raises:
            RuntimeError: If no AI backend is available
        """
        # Try OpenAI first
        if self.openai_client:
            try:
                return self._chat_openai(
                    messages,
                    model or self.openai_model,
                    temperature,
                    max_tokens,
                    json_mode,
                )
            except Exception as e:
                logger.warning(f"OpenAI chat failed: {e}, trying Ollama fallback")

        # Fallback to Ollama
        if self.ollama_client:
            try:
                return self._chat_ollama(
                    messages, model or self.ollama_model, temperature, json_mode
                )
            except Exception as e:
                logger.error(f"Ollama chat also failed: {e}")
                raise RuntimeError(f"All AI backends failed: {e}")

        raise RuntimeError("No AI backend available")

    def _chat_openai(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> str:
        """Send chat request to OpenAI."""
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.openai_client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content

        logger.debug(f"OpenAI response ({model}): {content[:100]}...")
        return content

    def _chat_ollama(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        json_mode: bool,
    ) -> str:
        """Send chat request to Ollama."""
        kwargs = {
            "model": model,
            "messages": messages,
            "options": {"temperature": temperature},
        }

        if json_mode:
            kwargs["format"] = "json"

        response = self.ollama_client.chat(**kwargs)
        content = response.get("message", {}).get("content", "")

        logger.debug(f"Ollama response ({model}): {content[:100]}...")
        return content

    def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        use_local: bool = True,
    ) -> str:
        """
        Analyze image using vision model.

        By default uses local LLaVA via Ollama for privacy.
        Set use_local=False to use OpenAI's GPT-4V.

        SMART FALLBACK: If local Ollama fails and OpenAI is available,
        automatically falls back to OpenAI with a warning.

        Args:
            image_bytes: PNG/JPEG image bytes
            prompt: Analysis prompt
            use_local: Use local model (default True for privacy)

        Returns:
            Analysis response string

        Raises:
            RuntimeError: If all vision backends fail
        """
        img_b64 = base64.b64encode(image_bytes).decode()

        # Try local LLaVA first if requested (privacy-first approach)
        if use_local:
            ollama_available, ollama_msg = self.check_ollama_available()

            if ollama_available and self.ollama_client:
                try:
                    return self._analyze_image_ollama(img_b64, prompt)
                except Exception as e:
                    logger.warning(f"Local vision (LLaVA) failed: {e}")
                    # Smart fallback: try OpenAI if available
                    if self.openai_client:
                        logger.info(
                            "⚡ Falling back to OpenAI GPT-4V for screen analysis (Ollama unavailable)"
                        )
                        try:
                            return self._analyze_image_openai(img_b64, prompt)
                        except Exception as openai_e:
                            logger.error(
                                f"OpenAI vision fallback also failed: {openai_e}"
                            )
                            raise RuntimeError(
                                f"All vision backends failed. Local: {e}, OpenAI: {openai_e}"
                            )
                    else:
                        raise RuntimeError(
                            f"Local vision failed and OpenAI not available: {e}"
                        )
            else:
                # Ollama not available - try OpenAI fallback
                logger.warning(f"Ollama not available: {ollama_msg}")
                if self.openai_client:
                    logger.info(
                        "⚡ Using OpenAI GPT-4V for screen analysis (Ollama unavailable)"
                    )
                    logger.info(
                        "💡 Install Ollama from https://ollama.com/download for local-only privacy"
                    )
                    try:
                        return self._analyze_image_openai(img_b64, prompt)
                    except Exception as e:
                        logger.error(f"OpenAI vision failed: {e}")
                        raise RuntimeError(f"Vision analysis failed: {e}")
                else:
                    raise RuntimeError(f"No vision backend available. {ollama_msg}")

        # Explicit OpenAI request (use_local=False)
        if self.openai_client:
            try:
                return self._analyze_image_openai(img_b64, prompt)
            except Exception as e:
                logger.error(f"OpenAI vision failed: {e}")
                raise RuntimeError(f"Vision analysis failed: {e}")

        raise RuntimeError(
            "No vision backend available. Set up OpenAI API key or install Ollama."
        )

    def _analyze_image_ollama(self, img_b64: str, prompt: str) -> str:
        """Analyze image using local LLaVA model."""
        response = self.ollama_client.chat(
            model=self.ollama_vision_model,
            messages=[{"role": "user", "content": prompt, "images": [img_b64]}],
        )
        content = response.get("message", {}).get("content", "")
        logger.debug(f"LLaVA analysis: {content[:100]}...")
        return content

    def _analyze_image_openai(self, img_b64: str, prompt: str) -> str:
        """Analyze image using OpenAI GPT-4V."""
        response = self.openai_client.chat.completions.create(
            model="gpt-4o",  # Vision capable model
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}",
                                "detail": "low",  # Use low detail for faster/cheaper
                            },
                        },
                    ],
                }
            ],
            max_tokens=500,
        )
        content = response.choices[0].message.content
        logger.debug(f"GPT-4V analysis: {content[:100]}...")
        return content

    def judge_activity(
        self,
        goal: str,
        app: str,
        title: str,
        history: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Judge whether activity matches goal.

        Args:
            goal: User's stated goal
            app: Current application name
            title: Current window title
            history: Recent activity history

        Returns:
            Judgment dict with classification, confidence, action, say
        """
        history_str = ""
        if history:
            history_str = f"\nRecent activities: {', '.join(history[-3:])}"

        prompt = f"""You are a focus assistant. Judge if the current activity matches the user's goal.

User's goal: {goal}

Current activity:
- App: {app}
- Window title: {title}
{history_str}

CLASSIFICATION RULES:
- "on_task": Activity is directly related to the goal
- "off_task": Entertainment, social media, games, unrelated browsing
- "thinking": Idle in productive app (user may be thinking)
- "idle": User is away
- "unknown": Ambiguous activity

ALWAYS classify these as "off_task":
- YouTube, Netflix, Twitch, streaming sites
- Twitter/X, Facebook, Instagram, TikTok, Reddit
- Games, shopping sites

Return JSON only:
{{
  "classification": "on_task" | "off_task" | "thinking" | "idle" | "unknown",
  "confidence": 0.0-1.0,
  "reason": "brief explanation",
  "say": "short phrase (max 15 words)",
  "action": "none" | "warn" | "yell"
}}
"""

        try:
            response = self.chat(
                [{"role": "user", "content": prompt}], temperature=0.3, json_mode=True
            )
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse judgment JSON: {e}")
            return {
                "classification": "unknown",
                "confidence": 0.5,
                "reason": "Failed to parse response",
                "say": "I'm having trouble judging this activity.",
                "action": "none",
            }

    def detect_motivation_state(
        self,
        goal: str,
        focus_minutes: int,
        idle_seconds: float,
        app_switches: int,
        recent_apps: List[str],
    ) -> Dict[str, Any]:
        """
        Detect user's motivation/mental state.

        Args:
            goal: Session goal
            focus_minutes: Minutes of focus time
            idle_seconds: Current idle time
            app_switches: Number of app switches in last 5 minutes
            recent_apps: List of recently used apps

        Returns:
            Dict with state and suggestion
        """
        prompt = f"""Analyze this user's current work state:

Goal: {goal}
Time on task: {focus_minutes} minutes
Idle time: {idle_seconds:.0f} seconds
App switches in last 5 min: {app_switches}
Recent apps: {', '.join(recent_apps[-5:])}

Classify their state as ONE of:
- "flow" - Deep focus, don't interrupt
- "productive" - Working well, light encouragement OK
- "struggling" - Stuck or frustrated, needs help
- "distracted" - Restless, frequent switching
- "fatigued" - Been working long, needs break

Return JSON only:
{{
  "state": "flow" | "productive" | "struggling" | "distracted" | "fatigued",
  "confidence": 0.0-1.0,
  "suggestion": "brief suggestion for the user"
}}
"""

        try:
            response = self.chat(
                [{"role": "user", "content": prompt}], temperature=0.3, json_mode=True
            )
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse motivation state: {e}")
            return {
                "state": "productive",
                "confidence": 0.5,
                "suggestion": "Keep up the good work!",
            }

    def get_status(self) -> Dict[str, Any]:
        """Get current AI client status."""
        return {
            "openai_available": self.is_openai_available(),
            "openai_model": self.openai_model,
            "ollama_available": self.is_ollama_available(),
            "ollama_model": self.ollama_model,
            "ollama_vision_model": self.ollama_vision_model,
            "primary_backend": "openai" if self.openai_client else "ollama",
        }


def create_ai_client(config: Dict[str, Any]) -> AIClient:
    """
    Factory function to create AI client from config.

    Args:
        config: Application config dict

    Returns:
        Configured AIClient instance
    """
    openai_config = config.get("openai", {})
    ollama_config = config.get("ollama", {})

    return AIClient(
        openai_api_key=os.getenv("OPENAI_API_KEY") or openai_config.get("api_key"),
        openai_model=openai_config.get("model", "gpt-4o-mini"),
        ollama_model=ollama_config.get("model", "llama3.2"),
        ollama_base_url=ollama_config.get("base_url", "http://localhost:11434"),
    )
