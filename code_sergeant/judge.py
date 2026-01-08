"""Activity judgment using LLM with fallback."""
import json
import logging
import random
import time
from typing import Optional, Dict, Any

from .models import ActivityEvent, Judgment, PersonalityProfile
from .phrases import (
    get_off_task_warnings, get_off_task_yells, 
    get_on_task_phrases, get_thinking_phrases
)

logger = logging.getLogger("code_sergeant.judge")


class ActivityJudge:
    """Judges whether activity matches the stated goal."""
    
    def __init__(
        self, 
        ai_client=None,
        model: str = "llama3.2", 
        base_url: str = "http://localhost:11434",
        personality_manager=None
    ):
        """
        Initialize judge.
        
        Args:
            ai_client: AIClient instance (preferred - uses OpenAI if available)
            model: Ollama model name (fallback if no ai_client)
            base_url: Ollama API base URL (fallback if no ai_client)
            personality_manager: Optional PersonalityManager for personality-aware phrases
        """
        self.ai_client = ai_client
        self.model = model
        self.base_url = base_url
        self.personality_manager = personality_manager
        
        # Legacy Ollama client (only if no ai_client provided)
        self.client = None
        if not ai_client:
            try:
                import ollama
                self.client = ollama.Client(host=base_url)
            except ImportError:
                logger.warning("Ollama not available and no AIClient provided")
        
        # Track activity patterns for deviation detection
        self.activity_pattern: list[str] = []
        self.consecutive_off_task_count: int = 0
        
        logger.info(f"ActivityJudge initialized with model={model}")
    
    def set_personality_manager(self, personality_manager):
        """Set the personality manager for phrase generation."""
        self.personality_manager = personality_manager
    
    def judge(
        self,
        goal: str,
        activity: ActivityEvent,
        history: list[ActivityEvent],
        last_yell_time: Optional[float] = None,
        cooldown_seconds: int = 30
    ) -> Judgment:
        """
        Judge if activity matches goal.
        
        Args:
            goal: User's stated goal
            activity: Current activity event
            history: Recent activity history
            last_yell_time: Timestamp of last yell (for cooldown)
            cooldown_seconds: Cooldown period in seconds
            
        Returns:
            Judgment object
        """
        # Handle AFK/idle case
        if activity.is_afk:
            return Judgment(
                classification="idle",
                confidence=1.0,
                reason="User is away from keyboard",
                say="",
                action="none"
            )
        
        # Handle thinking state (detected by NativeMonitor)
        if activity.is_thinking:
            say = self._get_phrase("thinking")
            return Judgment(
                classification="thinking",
                confidence=0.8,
                reason=f"User appears to be thinking (idle {activity.idle_duration_seconds:.0f}s in productive app)",
                say=say,
                action="none"  # Don't warn for thinking
            )
        
        # Try LLM judgment first
        try:
            judgment = self._judge_with_llm(goal, activity, history)
            
            # Track patterns for deviation detection
            self._track_activity_pattern(activity, judgment)
            
            # Apply cooldown logic
            if judgment.action == "yell" and last_yell_time:
                time_since_yell = time.time() - last_yell_time
                if time_since_yell < cooldown_seconds:
                    logger.debug(f"Suppressing yell due to cooldown ({time_since_yell:.1f}s < {cooldown_seconds}s)")
                    judgment.action = "warn"
                    judgment.say = self._get_phrase("off_task_warning")
            
            # Use personality-aware phrases if available
            if judgment.action != "none" and self.personality_manager:
                judgment.say = self.personality_manager.get_judgment_phrase(judgment)
            
            return judgment
            
        except Exception as e:
            logger.warning(f"LLM judgment failed: {e}, using fallback")
            return self._judge_fallback(goal, activity)
    
    def _track_activity_pattern(self, activity: ActivityEvent, judgment: Judgment):
        """Track activity patterns for deviation detection."""
        pattern_entry = f"{activity.app}:{judgment.classification}"
        self.activity_pattern.append(pattern_entry)
        
        # Keep only last 20 entries
        if len(self.activity_pattern) > 20:
            self.activity_pattern.pop(0)
        
        # Track consecutive off-task
        if judgment.classification == "off_task":
            self.consecutive_off_task_count += 1
        else:
            self.consecutive_off_task_count = 0
    
    def detect_goal_drift(self) -> bool:
        """
        Detect if user is gradually drifting from their goal.
        
        Returns:
            True if goal drift detected
        """
        if len(self.activity_pattern) < 5:
            return False
        
        # Check if more than 60% of recent activity is off-task
        recent = self.activity_pattern[-10:]
        off_task_count = sum(1 for p in recent if "off_task" in p)
        
        return off_task_count >= 6
    
    def reset_patterns(self):
        """Reset activity patterns (call when session starts)."""
        self.activity_pattern = []
        self.consecutive_off_task_count = 0
    
    def _get_phrase(self, phrase_type: str) -> str:
        """Get a phrase using personality manager or fallback."""
        if self.personality_manager:
            return self.personality_manager.get_phrase(phrase_type)
        
        # Fallback to default phrases
        phrases = {
            "off_task_warning": get_off_task_warnings(),
            "off_task_yell": get_off_task_yells(),
            "on_task": get_on_task_phrases(),
            "thinking": get_thinking_phrases(),
        }
        phrase_list = phrases.get(phrase_type, ["Stay focused!"])
        return random.choice(phrase_list)
    
    def _judge_with_llm(
        self,
        goal: str,
        activity: ActivityEvent,
        history: list[ActivityEvent]
    ) -> Judgment:
        """
        Judge using LLM with strict JSON contract.
        
        Args:
            goal: User's goal
            activity: Current activity
            history: Activity history
            
        Returns:
            Judgment from LLM or fallback
        """
        # Build prompt
        prompt = self._build_prompt(goal, activity, history)
        
        # Build activity context string for distraction override check
        activity_context = f"{activity.app} {activity.title}"
        
        # Use AIClient if available (preferred - uses OpenAI if configured)
        if self.ai_client:
            try:
                raw_output = self.ai_client.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    json_mode=True
                )
                logger.debug(f"LLM raw output: {raw_output}")
                
                # Parse JSON
                judgment_dict = self._parse_json_response(raw_output)
                
                # Validate and create Judgment
                judgment = self._validate_judgment(judgment_dict, activity_context)
                
                logger.debug(f"LLM judgment: {judgment.classification} ({judgment.confidence:.0%})")
                return judgment
                
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON from LLM: {e}, retrying once")
                try:
                    raw_output = self.ai_client.chat(
                        messages=[{"role": "user", "content": prompt + "\n\nRemember: output ONLY valid JSON."}],
                        temperature=0.3,
                        json_mode=True
                    )
                    judgment_dict = self._parse_json_response(raw_output)
                    judgment = self._validate_judgment(judgment_dict, activity_context)
                    return judgment
                except Exception as e2:
                    logger.error(f"Retry also failed: {e2}")
                    raise
            except Exception as e:
                logger.error(f"AI client call failed: {e}")
                raise
        
        # Fallback to direct Ollama (legacy)
        if not self.client:
            raise RuntimeError("No AI backend available")
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                format="json",
                options={
                    "temperature": 0.3,
                }
            )
            
            raw_output = response.get("response", "").strip()
            logger.debug(f"LLM raw output: {raw_output}")
            
            judgment_dict = self._parse_json_response(raw_output)
            judgment = self._validate_judgment(judgment_dict, activity_context)
            
            logger.debug(f"LLM judgment: {judgment.classification} ({judgment.confidence:.0%})")
            return judgment
            
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON from LLM: {e}, retrying once")
            try:
                response = self.client.generate(
                    model=self.model,
                    prompt=prompt + "\n\nRemember: output ONLY valid JSON.",
                    format="json"
                )
                raw_output = response.get("response", "").strip()
                judgment_dict = self._parse_json_response(raw_output)
                judgment = self._validate_judgment(judgment_dict, activity_context)
                return judgment
            except Exception as e2:
                logger.error(f"Retry also failed: {e2}")
                raise
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            raise
    
    def _build_prompt(self, goal: str, activity: ActivityEvent, history: list[ActivityEvent]) -> str:
        """Build prompt for LLM with enhanced activity context."""
        history_str = ""
        if history:
            recent = history[-3:]  # Last 3 activities
            history_str = "\nRecent activities:\n"
            for h in recent:
                history_str += f"- {h.app}: {h.title}\n"
        
        # Include enhanced activity context
        activity_context = f"""Current activity:
- App: {activity.app}
- Window title: {activity.title}
- Idle duration: {activity.idle_duration_seconds:.0f} seconds
- Keyboard active: {activity.keyboard_active}"""
        
        # Check for goal drift warning
        drift_warning = ""
        if self.detect_goal_drift():
            drift_warning = "\n\nWARNING: User appears to be gradually drifting from their goal. Consider a firmer response."
        
        # Get personality context if available
        personality_context = ""
        if self.personality_manager:
            profile = self.personality_manager.profile
            personality_context = f"\n\nYour personality: {profile.description}"
        
        prompt = f"""You are a focus assistant helping users stay on task.{personality_context}

User's goal: {goal}

{activity_context}
{history_str}
{drift_warning}

CLASSIFICATION RULES:
- "on_task": Activity is DIRECTLY related to the goal (coding, documentation, relevant research)
- "off_task": ANY entertainment, social media, videos, games, news, or unrelated browsing
- "thinking": User is in a productive app but idle (30-180 seconds) - they may be thinking
- "idle": User is truly AFK (away from keyboard) for extended period
- "unknown": Activity is ambiguous but NOT entertainment

CRITICAL - These are ALWAYS "off_task":
- YouTube (unless goal specifically involves YouTube)
- Netflix, Twitch, any streaming
- Twitter/X, Facebook, Instagram, TikTok, Reddit, Discord (social)
- News sites, sports sites
- Games of any kind
- Shopping sites
- Any video/audio entertainment

DO NOT classify entertainment as "idle" or "thinking" - that's WRONG. Entertainment = "off_task".

Output ONLY valid JSON:
{{
  "classification": "on_task" | "off_task" | "thinking" | "idle" | "unknown",
  "confidence": 0.0-1.0,
  "reason": "brief explanation",
  "say": "short phrase (max 15 words)",
  "action": "none" | "warn" | "yell"
}}

ACTION RULES:
- "none": For on_task or thinking
- "warn": First time off_task OR unknown activity
- "yell": Repeated off_task or obvious distraction (YouTube, social media, games)

JSON only:"""
        
        return prompt
    
    def _parse_json_response(self, raw_output: str) -> dict:
        """Parse JSON from LLM response, handling common issues."""
        # Try to extract JSON from response (in case LLM adds extra text)
        raw_output = raw_output.strip()
        
        # Find JSON object boundaries
        start_idx = raw_output.find('{')
        end_idx = raw_output.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = raw_output[start_idx:end_idx + 1]
        else:
            json_str = raw_output
        
        return json.loads(json_str)
    
    # Social media and distraction app keywords - always off_task
    DISTRACTION_KEYWORDS = [
        # Social media
        "instagram", "facebook", "twitter", "x.com", "tiktok", "reddit",
        "snapchat", "linkedin", "threads", "mastodon", "bluesky",
        # Video streaming  
        "youtube", "netflix", "hulu", "disney+", "hbo", "twitch",
        "vimeo", "dailymotion", "prime video",
        # Messaging (non-work)
        "discord", "whatsapp", "telegram", "messenger",
        # Entertainment
        "spotify", "apple music", "soundcloud",
        # Games
        "steam", "epic games", "game",
        # News/Sports
        "espn", "sports",
    ]
    
    def _validate_judgment(self, judgment_dict: dict, activity_context: str = "") -> Judgment:
        """Validate and create Judgment from dict, with override for known distractions."""
        # Validate classification (now includes "thinking")
        valid_classifications = ["on_task", "off_task", "idle", "unknown", "thinking"]
        classification = judgment_dict.get("classification", "unknown")
        if classification not in valid_classifications:
            logger.warning(f"Invalid classification: {classification}, defaulting to unknown")
            classification = "unknown"
        
        # Validate confidence
        confidence = float(judgment_dict.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
        
        # Validate action
        valid_actions = ["none", "warn", "yell"]
        action = judgment_dict.get("action", "none")
        if action not in valid_actions:
            action = "none"
        
        # Get reason and say
        reason = str(judgment_dict.get("reason", ""))[:100]
        say = str(judgment_dict.get("say", ""))[:200]
        
        # OVERRIDE: Force off_task for known distraction apps
        # This catches cases where LLM incorrectly classifies social media
        if activity_context:
            activity_lower = activity_context.lower()
            for keyword in self.DISTRACTION_KEYWORDS:
                if keyword in activity_lower:
                    if classification != "off_task":
                        logger.info(f"Override: Forcing off_task for '{keyword}' in activity")
                        classification = "off_task"
                        confidence = 0.95
                        action = "yell"
                        reason = f"Detected distraction: {keyword}"
                        say = self._get_phrase("off_task_yell")
                    break
        
        # If say is empty but action is warn/yell, generate one
        if not say and action != "none":
            if action == "yell":
                say = self._get_phrase("off_task_yell")
            else:
                say = self._get_phrase("off_task_warning")
        
        return Judgment(
            classification=classification,
            confidence=confidence,
            reason=reason,
            say=say,
            action=action
        )
    
    def _judge_fallback(self, goal: str, activity: ActivityEvent) -> Judgment:
        """
        Fallback rule-based classifier (STRICT).
        
        Args:
            goal: User's goal
            activity: Current activity
            
        Returns:
            Judgment from rules
        """
        app_lower = activity.app.lower()
        title_lower = activity.title.lower()
        combined = f"{app_lower} {title_lower}"
        
        # Entertainment/social keywords - BE STRICT!
        entertainment_keywords = [
            # Video streaming
            "youtube", "netflix", "hulu", "disney+", "hbo", "prime video",
            "twitch", "vimeo", "dailymotion",
            # Social media
            "twitter", "x.com", "facebook", "instagram", "reddit", "tiktok",
            "snapchat", "linkedin", "threads", "mastodon", "bluesky",
            # Messaging (non-work)
            "discord", "whatsapp", "telegram", "messenger", "imessage",
            # Music/Audio
            "spotify", "apple music", "soundcloud", "pandora",
            # News/Entertainment
            "news", "espn", "sports", "gaming", "game",
            # Shopping
            "amazon", "ebay", "shopping", "store",
        ]
        
        # Check if activity contains entertainment keywords
        is_entertainment = any(kw in combined for kw in entertainment_keywords)
        
        if is_entertainment:
            return Judgment(
                classification="off_task",
                confidence=0.9,
                reason="Detected entertainment/social/distraction",
                say=self._get_phrase("off_task_yell"),
                action="yell"
            )
        
        # Check if it's a code editor or documentation (productive)
        productive_keywords = [
            "code", "cursor", "vscode", "xcode", "sublime", "vim", "emacs", "neovim",
            "terminal", "iterm", "console", "shell",
            "docs", "documentation", "stackoverflow", "github", "gitlab", "bitbucket",
            "jira", "confluence", "notion", "obsidian",
            "figma", "sketch", "photoshop", "illustrator",  # Design tools
        ]
        is_productive = any(kw in combined for kw in productive_keywords)
        
        if is_productive:
            # Check for thinking state
            if activity.is_thinking or (activity.idle_duration_seconds >= 30 and activity.idle_duration_seconds <= 180):
                return Judgment(
                    classification="thinking",
                    confidence=0.7,
                    reason="User appears to be thinking in productive app",
                    say="",
                    action="none"
                )
            
            return Judgment(
                classification="on_task",
                confidence=0.8,
                reason="Detected productive app",
                say="",
                action="none"
            )
        
        # Default to unknown with mild warning
        return Judgment(
            classification="unknown",
            confidence=0.5,
            reason="Ambiguous activity - staying vigilant",
            say=self._get_phrase("off_task_warning"),
            action="warn"
        )
