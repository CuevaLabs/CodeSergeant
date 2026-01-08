"""Personality system for Code Sergeant."""
import logging
import random
from typing import Optional, Dict, Any, List
import ollama

from .models import PersonalityProfile, Judgment

logger = logging.getLogger("code_sergeant.personality")


# Predefined phrase templates for each personality
PERSONALITY_PHRASES = {
    "sergeant": {
        "off_task_warning": [
            "Hey! Stay focused on your goal, soldier!",
            "That's not what you're supposed to be doing. Get back to work!",
            "Get back to work, soldier!",
            "Focus up! You have a mission.",
            "Distraction detected. Return to task immediately!",
        ],
        "off_task_yell": [
            "Sergeant here! You're off track again!",
            "Enough distractions! Get back to work NOW!",
            "This is your final warning. FOCUS!",
            "You're wasting time. Get back on task!",
            "Drop and give me twenty! Just kidding, but GET FOCUSED!",
        ],
        "off_task_drill": [
            "Get off that distraction! Now!",
            "What are you doing?! Get back to work!",
            "This is unacceptable! Focus!",
            "Move it! Back to your task!",
            "Distraction alert! Eyes on the mission!",
            "Stop wasting time! Work!",
            "Hey! I said focus!",
            "Drop that and get back to it!",
            "You're still distracted! Come on!",
            "Time is ticking! Get moving!",
            "No excuses! Back to work!",
            "I'm not going to stop until you focus!",
            "Still slacking?! Unbelievable!",
            "Your goal isn't going to complete itself!",
            "Snap out of it! Work time!",
        ],
        "on_task": [
            "Good work, soldier. Keep it up.",
            "That's what I like to see. Stay focused.",
            "Outstanding! Maintain this momentum.",
        ],
        "thinking": [
            "Taking time to think? Approved. Stay sharp.",
            "Strategic pause acknowledged. Carry on.",
        ],
        "reminder": [
            "Time for a quick stretch break, soldier.",
            "Hydration check! Drink some water.",
            "Take a breather, then back to the mission.",
        ],
        "session_start": [
            "Session started! Time to focus, soldier!",
            "Mission briefing received. Let's do this!",
        ],
        "session_end": [
            "Session complete. Well done, soldier.",
            "Mission accomplished. At ease.",
        ],
    },
    "buddy": {
        "off_task_warning": [
            "Hey friend, let's get back on track!",
            "Oops! Looks like we got a bit distracted. No worries, let's refocus.",
            "Hey, I noticed you wandered off. Let's get back to it together!",
            "Just a friendly nudge - your goal is waiting for you!",
            "We got this! Let's get back to what we were doing.",
        ],
        "off_task_yell": [
            "Hey buddy, I really think we should get back to work now.",
            "I know it's tempting, but let's save that for later, okay?",
            "Come on, we can do this! Let's push through together.",
            "I believe in you! Let's get back on track.",
        ],
        "off_task_drill": [
            "Hey! Come on, let's get back to work!",
            "I know you can do this! Focus!",
            "We're still distracted. Let's try again!",
            "Hey friend, your goal needs you!",
            "Come on! We've got this!",
            "Let's snap back to it together!",
            "Still here! Let's refocus!",
            "Your goal is calling! Let's go!",
        ],
        "on_task": [
            "Awesome! You're doing great!",
            "Nice work! Keep it going!",
            "You're crushing it! So proud of you!",
        ],
        "thinking": [
            "Taking a moment to think? That's smart!",
            "Good thinking! Take your time.",
        ],
        "reminder": [
            "Hey, how about a quick stretch?",
            "Don't forget to stay hydrated!",
            "You're doing great! Maybe take a quick breather?",
        ],
        "session_start": [
            "Let's do this together! Session started!",
            "Excited to work with you! Let's focus!",
        ],
        "session_end": [
            "Great session! You did amazing!",
            "Session complete! You should be proud of yourself!",
        ],
    },
    "advisor": {
        "off_task_warning": [
            "I've noticed a deviation from your stated goal. Shall we refocus?",
            "This activity appears unrelated to your current objective.",
            "Consider whether this aligns with your priorities.",
            "A gentle reminder: your goal awaits your attention.",
            "Perhaps we should redirect our focus to the task at hand.",
        ],
        "off_task_yell": [
            "I strongly recommend returning to your primary objective.",
            "This extended deviation may impact your productivity significantly.",
            "It would be wise to return to your goal now.",
            "Consider the opportunity cost of this distraction.",
        ],
        "off_task_drill": [
            "Your attention is still diverted. Please refocus.",
            "This continued distraction is impacting productivity.",
            "I must insist we return to the objective.",
            "The deviation persists. Time to correct course.",
            "Your goal requires immediate attention.",
            "Productivity is declining. Please refocus.",
            "This distraction is costing valuable time.",
            "I recommend immediate return to task.",
        ],
        "on_task": [
            "Excellent focus. You're making good progress.",
            "Well done. Your dedication is commendable.",
            "Your current trajectory aligns well with your goals.",
        ],
        "thinking": [
            "Thoughtful consideration is valuable. Take your time.",
            "Reflection is an important part of the process.",
        ],
        "reminder": [
            "Consider taking a brief break to maintain optimal performance.",
            "A reminder to stay hydrated for cognitive function.",
            "Periodic rest enhances long-term productivity.",
        ],
        "session_start": [
            "Session initiated. Let's work toward your objectives.",
            "Ready to assist you in achieving your goals.",
        ],
        "session_end": [
            "Session concluded. Well executed.",
            "You've made meaningful progress today.",
        ],
    },
    "coach": {
        "off_task_warning": [
            "Hey champion! Let's get back in the game!",
            "You've got this! Time to refocus and win!",
            "Champions stay focused! Let's go!",
            "This is just a small setback. Get back up!",
            "Remember your goal! You're capable of greatness!",
        ],
        "off_task_yell": [
            "Come on! I know you can do better than this!",
            "Dig deep! Find that focus within you!",
            "This is your moment! Don't let distractions win!",
            "Push through! Victory awaits!",
        ],
        "off_task_drill": [
            "Champion! You're still off track! Get back in!",
            "Winners don't quit! Get focused!",
            "Come on! Dig deeper! Focus!",
            "This is your moment! Seize it!",
            "You're better than this! Get back to work!",
            "The clock is ticking! Move!",
            "Champions don't get distracted! Focus!",
            "Push! Push! Push! Back to work!",
            "Your goal is waiting! Go get it!",
            "No time for distractions! Let's go!",
        ],
        "on_task": [
            "That's the spirit! Keep pushing forward!",
            "You're on fire! Nothing can stop you!",
            "This is what champions do! Amazing work!",
        ],
        "thinking": [
            "Good! Strategize and then execute!",
            "Smart move taking time to plan!",
        ],
        "reminder": [
            "Time to recharge! Champions need rest too!",
            "Stay hydrated, stay strong!",
            "Quick break, then back to winning!",
        ],
        "session_start": [
            "Game time! Let's achieve something great!",
            "Ready to crush it? Let's go!",
        ],
        "session_end": [
            "Amazing session! You're a champion!",
            "What a performance! Be proud of yourself!",
        ],
    },
}


class PersonalityManager:
    """Manages personality profiles and phrase generation."""
    
    def __init__(self, config: Dict[str, Any], ollama_model: str = "llama3.2",
                 ollama_base_url: str = "http://localhost:11434"):
        """
        Initialize personality manager.
        
        Args:
            config: Configuration dictionary
            ollama_model: Ollama model for custom phrase generation
            ollama_base_url: Ollama API base URL
        """
        self.config = config
        self.ollama_model = ollama_model
        self.ollama_client = ollama.Client(host=ollama_base_url)
        self._current_profile: Optional[PersonalityProfile] = None
        self._load_profile()
        logger.info(f"PersonalityManager initialized with profile: {self._current_profile.name}")
    
    def _load_profile(self):
        """Load personality profile from config."""
        personality_config = self.config.get("personality", {})
        name = personality_config.get("name", "sergeant")
        
        if name == "custom":
            self._current_profile = PersonalityProfile(
                name="custom",
                wake_word_name=personality_config.get("wake_word_name", "assistant"),
                description=personality_config.get("description", ""),
                tone=personality_config.get("tone", [])
            )
        else:
            self._current_profile = PersonalityProfile.get_predefined(name)
    
    @property
    def profile(self) -> PersonalityProfile:
        """Get current personality profile."""
        return self._current_profile
    
    @property
    def wake_word(self) -> str:
        """Get current wake word."""
        return f"hey {self._current_profile.wake_word_name}"
    
    def set_personality(self, name: str, custom_description: str = None,
                       custom_wake_word: str = None):
        """
        Set the current personality.
        
        Args:
            name: Personality name
            custom_description: Description for custom personality
            custom_wake_word: Wake word for custom personality
        """
        if name == "custom":
            self._current_profile = PersonalityProfile(
                name="custom",
                wake_word_name=custom_wake_word or "assistant",
                description=custom_description or "",
                tone=[]
            )
        else:
            self._current_profile = PersonalityProfile.get_predefined(name)
        
        logger.info(f"Personality set to: {self._current_profile.name}")
    
    def get_phrase(self, phrase_type: str, context: Dict[str, Any] = None) -> str:
        """
        Get a phrase for the current personality.
        
        Args:
            phrase_type: Type of phrase (off_task_warning, off_task_yell, on_task, thinking, reminder, etc.)
            context: Additional context for phrase generation
            
        Returns:
            Generated or selected phrase
        """
        profile_name = self._current_profile.name
        
        # For predefined personalities, use templates
        if profile_name in PERSONALITY_PHRASES:
            phrases = PERSONALITY_PHRASES[profile_name].get(phrase_type, [])
            if phrases:
                return random.choice(phrases)
        
        # For custom personality or missing phrases, generate with LLM
        return self._generate_phrase(phrase_type, context)
    
    def _generate_phrase(self, phrase_type: str, context: Dict[str, Any] = None) -> str:
        """
        Generate a phrase using LLM for custom personalities.
        
        Args:
            phrase_type: Type of phrase to generate
            context: Additional context
            
        Returns:
            Generated phrase
        """
        try:
            tone_str = ", ".join(self._current_profile.tone) if self._current_profile.tone else "neutral"
            description = self._current_profile.description or "a helpful assistant"
            
            phrase_instructions = {
                "off_task_warning": "Generate a gentle warning for someone who got distracted.",
                "off_task_yell": "Generate a firm reminder for someone who has been distracted for too long.",
                "on_task": "Generate encouragement for someone who is focused and doing well.",
                "thinking": "Generate acknowledgment for someone who is thinking/planning.",
                "reminder": "Generate a reminder to take a break or stay hydrated.",
                "session_start": "Generate an encouraging message to start a focus session.",
                "session_end": "Generate a summary message for completing a focus session.",
            }
            
            instruction = phrase_instructions.get(phrase_type, "Generate an appropriate response.")
            
            prompt = f"""You are {description}. Your tone is: {tone_str}.

{instruction}

Keep your response SHORT (1-2 sentences max, under 20 words).
Respond in character only - no explanations, just the phrase.

Response:"""
            
            response = self.ollama_client.generate(
                model=self.ollama_model,
                prompt=prompt,
                options={"temperature": 0.8, "num_predict": 50}
            )
            
            phrase = response.get("response", "").strip()
            # Clean up any quotes
            phrase = phrase.strip('"\'')
            
            if phrase:
                return phrase
            
        except Exception as e:
            logger.warning(f"Failed to generate phrase: {e}")
        
        # Fallback to sergeant phrases
        fallback_phrases = PERSONALITY_PHRASES.get("sergeant", {}).get(phrase_type, ["Keep going!"])
        return random.choice(fallback_phrases) if fallback_phrases else "Keep going!"
    
    def get_judgment_phrase(self, judgment: Judgment, context: Dict[str, Any] = None) -> str:
        """
        Get an appropriate phrase based on judgment.
        
        Args:
            judgment: Judgment object
            context: Additional context
            
        Returns:
            Appropriate phrase for the judgment
        """
        if judgment.action == "yell":
            return self.get_phrase("off_task_yell", context)
        elif judgment.action == "warn":
            return self.get_phrase("off_task_warning", context)
        elif judgment.classification == "on_task":
            return self.get_phrase("on_task", context)
        elif judgment.classification == "thinking":
            return self.get_phrase("thinking", context)
        else:
            return ""


def get_personality_choices() -> List[Dict[str, str]]:
    """
    Get list of available personality choices for UI.
    
    Returns:
        List of personality options with name and description
    """
    return [
        {
            "name": "sergeant",
            "display_name": "Drill Sergeant",
            "wake_word": "hey sergeant",
            "description": "Strict, no-nonsense military-style motivation"
        },
        {
            "name": "buddy",
            "display_name": "Friendly Buddy",
            "wake_word": "hey buddy",
            "description": "Warm, supportive friend who encourages gently"
        },
        {
            "name": "advisor",
            "display_name": "Professional Advisor",
            "wake_word": "hey advisor",
            "description": "Thoughtful, professional guidance"
        },
        {
            "name": "coach",
            "display_name": "Motivational Coach",
            "wake_word": "hey coach",
            "description": "Energetic, inspiring motivation"
        },
        {
            "name": "custom",
            "display_name": "Custom",
            "wake_word": "hey [your name]",
            "description": "Define your own personality and wake word"
        },
    ]

