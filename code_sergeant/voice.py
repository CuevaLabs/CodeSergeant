"""Voice recording, transcription, wake word detection, and LLM interaction."""
import logging
import threading
import time
import json
import re
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
import ollama
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime

logger = logging.getLogger("code_sergeant.voice")


# Voice command patterns
COMMAND_PATTERNS = {
    "start_session": [
        r"start\s+(?:a\s+)?session\s+(?:for\s+|to\s+|on\s+)?(.+)",
        r"begin\s+(?:a\s+)?session\s+(?:for\s+|to\s+|on\s+)?(.+)",
        r"let'?s\s+(?:start|begin)\s+(?:working\s+on\s+)?(.+)",
    ],
    "end_session": [
        r"(?:end|stop|finish|close)\s+(?:the\s+)?session",
        r"i'?m\s+done",
        r"session\s+(?:over|complete|finished)",
    ],
    "pause_session": [
        r"pause\s+(?:the\s+)?session",
        r"take\s+a\s+break",
        r"pause",
    ],
    "resume_session": [
        r"resume\s+(?:the\s+)?session",
        r"continue\s+(?:the\s+)?session",
        r"i'?m\s+back",
    ],
    "change_goal": [
        r"change\s+(?:my\s+)?goal\s+to\s+(.+)",
        r"(?:new|update)\s+goal[:\s]+(.+)",
        r"i'?m\s+(?:now\s+)?working\s+on\s+(.+)",
    ],
    "save_note": [
        r"(?:save|remember|note)[:\s]+(.+)",
        r"save\s+(?:this\s+)?(?:for\s+)?later[:\s]+(.+)",
        r"remind\s+me[:\s]+(.+)",
        r"i\s+just\s+thought\s+of[:\s]+(.+)",
        # Natural "take a note" patterns
        r"i\s+(?:want\s+to\s+)?take\s+a\s+note[:\s,]*(.+)",
        r"take\s+a\s+note[:\s,]*(.+)",
        r"(?:make|write)\s+a\s+note[:\s,]*(.+)",
        r"i\s+want\s+to\s+note[:\s,]*(.+)",
        r"note\s+(?:that\s+)?(.+)",
        r"jot\s+(?:down\s+)?(.+)",
        r"write\s+(?:down\s+)?(.+)",
    ],
    "report_distraction": [
        r"i'?m\s+(?:getting\s+)?distracted\s+(?:by|because)[:\s]+(.+)",
        r"distracted[:\s]+(.+)",
    ],
    "report_phone": [
        r"i'?m\s+on\s+(?:my\s+)?phone",
        r"phone\s+distraction",
        r"was\s+on\s+(?:my\s+)?phone",
    ],
    "start_pomodoro": [
        r"start\s+(?:a\s+)?pomodoro",
        r"start\s+(?:the\s+)?timer",
        r"pomodoro\s+start",
    ],
    "pause_pomodoro": [
        r"pause\s+(?:the\s+)?(?:pomodoro|timer)",
    ],
    "stop_pomodoro": [
        r"stop\s+(?:the\s+)?(?:pomodoro|timer)",
        r"cancel\s+(?:the\s+)?(?:pomodoro|timer)",
    ],
    "skip_pomodoro": [
        r"skip\s+(?:the\s+)?(?:pomodoro|timer|break)",
        r"next\s+(?:pomodoro|phase)",
    ],
    "status": [
        r"(?:what'?s?\s+)?(?:my\s+)?status",
        r"how\s+(?:am\s+)?i\s+doing",
        r"progress\s+(?:report|update)",
    ],
}


class VoiceCommand:
    """Represents a parsed voice command."""
    
    def __init__(self, command_type: str, args: Optional[str] = None, raw_text: str = ""):
        self.command_type = command_type
        self.args = args
        self.raw_text = raw_text
        self.timestamp = datetime.now()
    
    def __repr__(self):
        return f"VoiceCommand({self.command_type}, args={self.args})"


class WakeWordDetector:
    """Detects wake words using continuous audio streaming and Whisper."""
    
    # Special command phrases that can follow wake words
    NOTE_TAKING_PHRASES = [
        "take a note",
        "take note",
        "make a note",
        "note this",
        "remember this",
        "save this",
    ]
    
    def __init__(
        self,
        wake_words: List[str],
        sample_rate: int = 16000,
        chunk_duration: float = 2.0,
        sensitivity: float = 0.5,
        on_wake_word: Optional[Callable[[str], None]] = None,
        on_note_taking: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize wake word detector.
        
        Args:
            wake_words: List of wake words to detect (e.g., ["hey sergeant", "hey buddy"])
            sample_rate: Audio sample rate
            chunk_duration: Duration of each audio chunk in seconds
            sensitivity: Detection sensitivity (0.0-1.0)
            on_wake_word: Callback when wake word detected
            on_note_taking: Callback when "hey [personality] take a note" detected
        """
        self.wake_words = [w.lower() for w in wake_words]
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.sensitivity = sensitivity
        self.on_wake_word = on_wake_word
        self.on_note_taking = on_note_taking
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Initialize Whisper model (tiny for speed in wake word detection)
        try:
            self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
            logger.info("Wake word detector: Whisper tiny model loaded")
        except Exception as e:
            logger.error(f"Failed to load Whisper model for wake word detection: {e}")
            self.whisper_model = None
    
    def set_wake_words(self, wake_words: List[str]):
        """Update wake words."""
        self.wake_words = [w.lower() for w in wake_words]
        logger.info(f"Wake words updated: {self.wake_words}")
    
    def start(self):
        """Start wake word detection in background thread."""
        if self._running:
            logger.warning("Wake word detector already running")
            return
        
        if not self.whisper_model:
            logger.error("Cannot start wake word detection: Whisper model not available")
            return
        
        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._thread.start()
        logger.info(f"Wake word detection started. Listening for: {self.wake_words}")
    
    def stop(self):
        """Stop wake word detection."""
        if not self._running:
            return
        
        self._stop_event.set()
        self._running = False
        
        # Don't try to join if we're stopping from within the detection thread itself
        # (this happens when stop is called from a wake word callback)
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=3.0)
        
        logger.info("Wake word detection stopped")
    
    def _detection_loop(self):
        """Main detection loop."""
        chunk_samples = int(self.chunk_duration * self.sample_rate)
        
        while not self._stop_event.is_set():
            try:
                # Record audio chunk
                audio_data = sd.rec(
                    chunk_samples,
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype=np.float32
                )
                sd.wait()
                
                if self._stop_event.is_set():
                    break
                
                audio_data = audio_data.flatten()
                
                # Check audio level (skip if too quiet)
                # Lower threshold to catch quieter speech
                audio_level = np.abs(audio_data).max()
                if audio_level < 0.01:  # Lowered threshold for better detection
                    continue
                
                # Transcribe
                segments, _ = self.whisper_model.transcribe(
                    audio_data,
                    language="en",
                    beam_size=1,  # Fast decoding
                    vad_filter=True
                )
                
                transcript = " ".join(seg.text for seg in segments).lower().strip()
                
                if not transcript:
                    continue
                
                logger.debug(f"Wake word check: '{transcript}'")
                
                # Check for wake words
                for wake_word in self.wake_words:
                    # Use fuzzy matching with sensitivity
                    if self._matches_wake_word(transcript, wake_word):
                        logger.info(f"Wake word detected: '{wake_word}' in '{transcript}'")
                        
                        # Check if this is a note-taking command (e.g., "hey sergeant take a note")
                        is_note_taking = self._is_note_taking_command(transcript)
                        
                        if is_note_taking and self.on_note_taking:
                            logger.info(f"Note-taking command detected: '{transcript}'")
                            self.on_note_taking(wake_word)
                        elif self.on_wake_word:
                            self.on_wake_word(wake_word)
                        
                        # Brief pause after detection to avoid rapid triggers
                        time.sleep(1.0)
                        break
                
            except sd.PortAudioError as e:
                logger.error(f"Audio error in wake word detection: {e}")
                time.sleep(1.0)
            except Exception as e:
                logger.error(f"Error in wake word detection: {e}")
                time.sleep(0.5)
    
    def _matches_wake_word(self, transcript: str, wake_word: str) -> bool:
        """
        Check if transcript contains wake word with fuzzy matching.
        
        Uses sensitivity parameter for fuzzy matching threshold.
        Higher sensitivity = more strict matching, lower = more lenient.
        
        Args:
            transcript: Transcribed text
            wake_word: Wake word to match
            
        Returns:
            True if match found
        """
        # Exact match
        if wake_word in transcript:
            return True
        
        # Handle common transcription variations
        variations = self._get_wake_word_variations(wake_word)
        for variation in variations:
            if variation in transcript:
                return True
        
        # Fuzzy matching using word-level similarity
        # Split transcript into words and check for partial matches
        transcript_words = transcript.lower().split()
        wake_words_parts = wake_word.lower().split()
        
        # Try to find wake word parts in sequence in the transcript
        if len(wake_words_parts) >= 2:
            for i in range(len(transcript_words) - len(wake_words_parts) + 1):
                matches = 0
                for j, wake_part in enumerate(wake_words_parts):
                    transcript_part = transcript_words[i + j] if i + j < len(transcript_words) else ""
                    # Check similarity
                    if self._word_similarity(transcript_part, wake_part) >= (0.6 + self.sensitivity * 0.3):
                        matches += 1
                
                # If most parts match, consider it a match
                if matches >= len(wake_words_parts) - 1:
                    logger.debug(f"Fuzzy match: '{transcript}' matched '{wake_word}' with {matches}/{len(wake_words_parts)} parts")
                    return True
        
        return False
    
    def _word_similarity(self, word1: str, word2: str) -> float:
        """
        Calculate similarity between two words (0.0 to 1.0).
        
        Uses a simple character-based similarity metric.
        """
        if word1 == word2:
            return 1.0
        if not word1 or not word2:
            return 0.0
        
        # Normalize
        word1 = word1.lower().strip()
        word2 = word2.lower().strip()
        
        if word1 == word2:
            return 1.0
        
        # Check if one contains the other
        if word1 in word2 or word2 in word1:
            return 0.8
        
        # Simple Levenshtein-like ratio
        len1, len2 = len(word1), len(word2)
        max_len = max(len1, len2)
        
        # Count matching characters at same positions
        matches = sum(1 for c1, c2 in zip(word1, word2) if c1 == c2)
        
        # Also count matching characters overall
        common_chars = sum(1 for c in set(word1) if c in word2)
        
        # Weighted average
        position_score = matches / max_len if max_len > 0 else 0
        char_score = common_chars / max(len(set(word1)), len(set(word2))) if max_len > 0 else 0
        
        return (position_score * 0.6 + char_score * 0.4)
    
    def _get_wake_word_variations(self, wake_word: str) -> List[str]:
        """Get common variations of a wake word."""
        variations = [wake_word]
        
        # Common variations for "hey X"
        if wake_word.startswith("hey "):
            name = wake_word[4:]
            variations.extend([
                f"hey {name}",
                f"hey, {name}",
                f"hey. {name}",
                f"a {name}",    # Whisper sometimes mishears "hey" as "a"
                f"hay {name}",
                f"hi {name}",
                f"he {name}",   # Sometimes "hey" becomes "he"
                f"heh {name}",
                f"hey {name}.",  # With trailing punctuation
                f"hey, {name}.",
                # Handle common sergeant mishearings
                name,  # Just the name alone sometimes
            ])
            
            # Handle common mishearings of "sergeant"
            if "sergeant" in name:
                base = name.replace("sergeant", "")
                variations.extend([
                    f"hey{base}sargent",
                    f"hey {base}sargent",
                    f"hey {base}sargent.",
                    f"hey {base}sargeant",
                    f"a {base}sargent",
                    f"hey {base}sergent",
                    f"hey {base}serjeant",
                ])
        
        return variations
    
    def _is_note_taking_command(self, transcript: str) -> bool:
        """
        Check if transcript contains a note-taking command after the wake word.
        
        Args:
            transcript: Full transcript text
            
        Returns:
            True if note-taking phrase found
        """
        transcript_lower = transcript.lower()
        
        for phrase in self.NOTE_TAKING_PHRASES:
            if phrase in transcript_lower:
                return True
        
        return False


class VoiceCommandParser:
    """Parses voice input into commands."""
    
    def __init__(self, ollama_model: str = "llama3.2", ollama_base_url: str = "http://localhost:11434"):
        """
        Initialize command parser.
        
        Args:
            ollama_model: Ollama model for complex command parsing
            ollama_base_url: Ollama API base URL
        """
        self.ollama_client = ollama.Client(host=ollama_base_url)
        self.ollama_model = ollama_model
    
    def parse(self, transcript: str) -> Optional[VoiceCommand]:
        """
        Parse transcript into a command.
        
        Args:
            transcript: Voice transcript
            
        Returns:
            VoiceCommand if recognized, None otherwise
        """
        transcript_lower = transcript.lower().strip()
        
        # Try pattern matching first
        for command_type, patterns in COMMAND_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, transcript_lower, re.IGNORECASE)
                if match:
                    args = match.group(1) if match.lastindex else None
                    
                    # Special handling for save_note: if args is just punctuation or empty,
                    # treat as a request to start note-taking mode (return start_note_taking command)
                    if command_type == "save_note":
                        cleaned_args = re.sub(r'^[\s.,!?:;]+|[\s.,!?:;]+$', '', args or '').strip() if args else ''
                        if not cleaned_args:
                            # User said "take a note" without content - they want to dictate
                            logger.info(f"Parsed command: start_note_taking (user wants to dictate)")
                            return VoiceCommand("start_note_taking", None, transcript)
                        args = cleaned_args
                    
                    logger.info(f"Parsed command: {command_type} with args: {args}")
                    return VoiceCommand(command_type, args, transcript)
        
        # If no pattern match, try LLM parsing for complex commands
        return self._parse_with_llm(transcript)
    
    def _parse_with_llm(self, transcript: str) -> Optional[VoiceCommand]:
        """Parse command using LLM for complex/ambiguous input."""
        try:
            prompt = f"""Parse this voice command and output ONLY valid JSON.

Voice input: "{transcript}"

Possible commands:
- start_session: Start a focus session (args: goal)
- end_session: End the session
- pause_session: Pause the session
- resume_session: Resume the session
- change_goal: Change the goal (args: new goal)
- save_note: Save a note for later (args: note content)
- report_distraction: Report being distracted (args: reason)
- report_phone: Report phone usage
- start_pomodoro: Start pomodoro timer
- pause_pomodoro: Pause pomodoro
- stop_pomodoro: Stop pomodoro
- skip_pomodoro: Skip current phase
- status: Get status
- chat: General conversation (not a command)

Output JSON:
{{"command": "command_type", "args": "arguments or null"}}

If it's just general conversation, output:
{{"command": "chat", "args": null}}

JSON only:"""
            
            response = self.ollama_client.generate(
                model=self.ollama_model,
                prompt=prompt,
                format="json",
                options={"temperature": 0.1, "num_predict": 50}
            )
            
            raw = response.get("response", "").strip()
            result = json.loads(raw)
            
            command_type = result.get("command")
            args = result.get("args")
            
            if command_type and command_type != "chat":
                return VoiceCommand(command_type, args, transcript)
            
            return None
            
        except Exception as e:
            logger.warning(f"LLM command parsing failed: {e}")
            return None


class VoiceWorker:
    """Worker for handling voice input: record → transcribe → LLM → TTS."""
    
    def __init__(
        self,
        record_seconds: int = 3,
        sample_rate: int = 16000,
        ollama_model: str = "llama3.2",
        ollama_base_url: str = "http://localhost:11434",
        tts_service=None,
        personality_manager=None
    ):
        """
        Initialize voice worker.
        
        Args:
            record_seconds: Duration to record in seconds
            sample_rate: Audio sample rate
            ollama_model: Ollama model name
            ollama_base_url: Ollama API base URL
            tts_service: TTSService instance for speaking responses
            personality_manager: PersonalityManager for personality-aware responses
        """
        self.record_seconds = record_seconds
        self.sample_rate = sample_rate
        self.ollama_model = ollama_model
        self.ollama_client = ollama.Client(host=ollama_base_url)
        self.tts_service = tts_service
        self.personality_manager = personality_manager
        
        # Command parser
        self.command_parser = VoiceCommandParser(ollama_model, ollama_base_url)
        
        # Initialize Whisper model (base model for accuracy)
        try:
            self.whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            logger.info("Whisper model loaded")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self.whisper_model = None
    
    # Stop phrases for ending note-taking
    NOTE_STOP_PHRASES = [
        "end note",
        "and note",  # Common Whisper mishearing of "end note"
        "in note",   # Another mishearing
        "stop note",
        "stop taking note",
        "stop taking notes", 
        "done taking note",
        "done taking notes",
        "done with note",
        "that's all",
        "that's it",
        "finish note",
        "save note",
        "save it",
    ]
    
    # TTS prompt phrases to filter from the start of recordings
    TTS_PROMPT_PHRASES = [
        "when you're done",
        "when you are done",
        "go ahead",
        "say end note",
        "say 'end note'",
    ]
    
    def record_note(self, max_duration: float = 120.0) -> Optional[str]:
        """
        Record a note until user says a stop phrase (e.g., "end note").
        
        Records in chunks, transcribing periodically to check for stop phrases.
        Continues until stop phrase detected or max duration reached.
        
        Args:
            max_duration: Maximum recording duration in seconds (default 2 minutes)
            
        Returns:
            Transcript text (without stop phrase), or None if recording/transcription failed
        """
        try:
            default_input = sd.query_devices(kind='input')
            logger.info(f"Using input device: {default_input['name']}")
            
            all_audio_chunks = []
            chunk_duration = 5.0  # Record in 5-second chunks for transcription checks
            chunk_samples = int(chunk_duration * self.sample_rate)
            max_samples = int(max_duration * self.sample_rate)
            total_samples = 0
            
            logger.info(f"Recording note (max {max_duration}s). Say 'end note' or 'stop taking note' when done.")
            
            while total_samples < max_samples:
                # Record chunk
                chunk = sd.rec(
                    chunk_samples,
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype=np.float32
                )
                sd.wait()
                
                chunk = chunk.flatten()
                all_audio_chunks.append(chunk)
                total_samples += len(chunk)
                
                # Transcribe this chunk to check for stop phrase
                try:
                    chunk_transcript = self._transcribe(chunk)
                    if chunk_transcript:
                        chunk_lower = chunk_transcript.lower()
                        logger.debug(f"Note chunk: '{chunk_transcript}'")
                        
                        # Check for stop phrases
                        for stop_phrase in self.NOTE_STOP_PHRASES:
                            if stop_phrase in chunk_lower:
                                logger.info(f"Stop phrase detected: '{stop_phrase}'")
                                # Combine all audio and transcribe the full recording
                                full_audio = np.concatenate(all_audio_chunks)
                                full_transcript = self._transcribe(full_audio)
                                
                                if full_transcript:
                                    # Remove the stop phrase from the transcript
                                    cleaned = self._remove_stop_phrases(full_transcript)
                                    logger.info(f"Note transcribed: {cleaned[:100]}...")
                                    return cleaned
                                return None
                except Exception as e:
                    logger.warning(f"Chunk transcription failed: {e}")
                    # Continue recording even if chunk transcription fails
            
            # Max duration reached - transcribe everything
            logger.info("Max duration reached, finalizing note...")
            full_audio = np.concatenate(all_audio_chunks)
            full_transcript = self._transcribe(full_audio)
            
            if full_transcript:
                cleaned = self._remove_stop_phrases(full_transcript)
                logger.info(f"Note transcribed: {cleaned[:100]}...")
                return cleaned
            return None
            
        except sd.PortAudioError as e:
            logger.error(f"PortAudio error (mic permission?): {e}")
            self._handle_mic_error(e)
            return None
        except Exception as e:
            logger.error(f"Note recording error: {e}")
            return None
    
    def _remove_stop_phrases(self, transcript: str) -> str:
        """Remove stop phrases from the end and TTS prompts from the start of a transcript."""
        result = transcript.strip()
        
        # Remove TTS prompt phrases from the beginning (mic picked up the TTS)
        for prompt_phrase in self.TTS_PROMPT_PHRASES:
            pattern = rf'^[\s.,!?]*{re.escape(prompt_phrase)}[\s.,!?]*'
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        
        # Also remove common partial TTS bleed-through patterns
        result = re.sub(r'^[\s.,!?]*(what|when)\s+you\'?r?e?\s+done[\s.,!?]*', '', result, flags=re.IGNORECASE)
        
        # Remove stop phrases from the end
        for stop_phrase in self.NOTE_STOP_PHRASES:
            pattern = rf'\s*{re.escape(stop_phrase)}[\s.,!?]*$'
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        
        return result.strip()
    
    def record_and_process(
        self,
        goal: Optional[str] = None,
        current_activity: Optional[str] = None,
        parse_commands: bool = True
    ) -> tuple[Optional[str], Optional[VoiceCommand]]:
        """
        Record audio, transcribe, optionally parse commands, get LLM response.
        
        Args:
            goal: Current session goal (for context)
            current_activity: Current activity (for context)
            parse_commands: Whether to try parsing as command
            
        Returns:
            Tuple of (transcript, command) - command may be None
        """
        # Announce recording start
        if self.tts_service:
            self.tts_service.speak("Listening")
            time.sleep(0.5)  # Brief pause after announcement
        
        # Record audio
        try:
            logger.info("Recording audio...")
            audio_data = self._record_audio()
            if audio_data is None:
                return None, None
        except Exception as e:
            logger.error(f"Recording failed: {e}")
            self._handle_mic_error(e)
            return None, None
        
        # Transcribe
        try:
            logger.info("Transcribing audio...")
            transcript = self._transcribe(audio_data)
            if not transcript:
                logger.warning("Empty transcription")
                return None, None
            logger.info(f"Transcribed: {transcript}")
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None, None
        
        # Try to parse as command
        command = None
        if parse_commands:
            command = self.command_parser.parse(transcript)
            if command:
                logger.info(f"Voice command detected: {command}")
                return transcript, command
        
        # Get LLM response for non-command input
        try:
            logger.info("Getting LLM response...")
            response = self._get_llm_response(transcript, goal, current_activity)
            if response:
                logger.info(f"LLM response: {response}")
                if self.tts_service:
                    self.tts_service.speak(response)
        except Exception as e:
            logger.error(f"LLM response failed: {e}")
        
        return transcript, command
    
    def _record_audio(self) -> Optional[np.ndarray]:
        """
        Record audio from microphone.
        
        Returns:
            Audio data as numpy array, or None on error
        """
        try:
            # List available devices for debugging
            devices = sd.query_devices()
            default_input = sd.query_devices(kind='input')
            logger.debug(f"Available audio devices: {len(devices)}")
            logger.info(f"Using input device: {default_input['name']}")
            
            # Record audio
            audio_data = sd.rec(
                int(self.record_seconds * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.float32
            )
            sd.wait()  # Wait until recording is finished
            
            # Flatten from (samples, 1) to (samples,) for Whisper
            audio_data = audio_data.flatten()
            
            # Check audio level
            audio_level = np.abs(audio_data).max()
            audio_rms = np.sqrt(np.mean(audio_data**2))
            logger.info(f"Recorded {len(audio_data)} samples, peak level: {audio_level:.4f}, RMS: {audio_rms:.4f}")
            
            if audio_level < 0.01:
                logger.warning("Audio level very low - microphone may not be capturing sound")
            
            return audio_data
            
        except sd.PortAudioError as e:
            logger.error(f"PortAudio error (mic permission?): {e}")
            self._handle_mic_error(e)
            return None
        except Exception as e:
            logger.error(f"Recording error: {e}")
            return None
    
    def _record_audio_with_vad(
        self,
        max_duration: float = 15.0,
        silence_threshold: float = 0.02,
        silence_duration: float = 1.5,
        chunk_duration: float = 0.5
    ) -> Optional[np.ndarray]:
        """
        Record audio with voice activity detection.
        
        Records until silence is detected (after speech) or max duration reached.
        
        Args:
            max_duration: Maximum recording duration in seconds
            silence_threshold: RMS threshold for silence detection
            silence_duration: Duration of silence to trigger stop
            chunk_duration: Duration of each recording chunk
            
        Returns:
            Audio data as numpy array, or None on error
        """
        try:
            default_input = sd.query_devices(kind='input')
            logger.info(f"Using input device: {default_input['name']}")
            
            chunks = []
            chunk_samples = int(chunk_duration * self.sample_rate)
            max_samples = int(max_duration * self.sample_rate)
            silence_samples = int(silence_duration * self.sample_rate)
            
            total_samples = 0
            consecutive_silence_samples = 0
            speech_detected = False
            
            logger.info(f"Recording with VAD (max {max_duration}s, silence threshold: {silence_threshold})")
            
            while total_samples < max_samples:
                # Record chunk
                chunk = sd.rec(
                    chunk_samples,
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype=np.float32
                )
                sd.wait()
                
                chunk = chunk.flatten()
                chunks.append(chunk)
                total_samples += len(chunk)
                
                # Calculate RMS for this chunk
                chunk_rms = np.sqrt(np.mean(chunk**2))
                
                if chunk_rms > silence_threshold:
                    # Speech detected
                    speech_detected = True
                    consecutive_silence_samples = 0
                else:
                    # Silence
                    if speech_detected:
                        consecutive_silence_samples += len(chunk)
                        
                        # Check if we've had enough silence after speech
                        if consecutive_silence_samples >= silence_samples:
                            logger.info(f"VAD: Silence detected after speech, stopping recording")
                            break
            
            # Combine all chunks
            audio_data = np.concatenate(chunks)
            
            audio_level = np.abs(audio_data).max()
            audio_rms = np.sqrt(np.mean(audio_data**2))
            logger.info(f"VAD recorded {len(audio_data)} samples ({len(audio_data)/self.sample_rate:.1f}s), peak: {audio_level:.4f}, RMS: {audio_rms:.4f}")
            
            return audio_data
            
        except sd.PortAudioError as e:
            logger.error(f"PortAudio error (mic permission?): {e}")
            self._handle_mic_error(e)
            return None
        except Exception as e:
            logger.error(f"VAD recording error: {e}")
            return None
    
    def _transcribe(self, audio_data: np.ndarray) -> Optional[str]:
        """
        Transcribe audio using Whisper.
        
        Args:
            audio_data: Audio data as numpy array (must be 1D, float32)
            
        Returns:
            Transcribed text, or None on error
        """
        if not self.whisper_model:
            logger.error("Whisper model not available")
            return None
        
        try:
            # Ensure audio is the right format
            if audio_data.ndim > 1:
                audio_data = audio_data.flatten()
            
            # Ensure float32
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            logger.debug(f"Transcribing audio: shape={audio_data.shape}, dtype={audio_data.dtype}")
            
            segments, info = self.whisper_model.transcribe(
                audio_data,
                language="en",
                beam_size=5,
                vad_filter=True,  # Enable voice activity detection
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            # Collect all segments
            transcript_parts = []
            for segment in segments:
                logger.debug(f"Segment: [{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
                transcript_parts.append(segment.text)
            
            transcript = " ".join(transcript_parts).strip()
            
            if not transcript:
                logger.warning("No speech detected in audio")
            
            return transcript if transcript else None
            
        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            return None
    
    def _get_llm_response(
        self,
        transcript: str,
        goal: Optional[str] = None,
        current_activity: Optional[str] = None
    ) -> Optional[str]:
        """
        Get LLM response to user's voice input.
        
        Args:
            transcript: Transcribed user input
            goal: Current session goal
            current_activity: Current activity
            
        Returns:
            LLM response text, or None on error
        """
        # Build context
        context = ""
        if goal:
            context += f"User's current goal: {goal}\n"
        if current_activity:
            context += f"Current activity: {current_activity}\n"
        
        # Get personality context
        personality_desc = "You are Code Sergeant, a focus assistant helping the user stay on task."
        if self.personality_manager:
            profile = self.personality_manager.profile
            personality_desc = f"You are {profile.wake_word_name.title()}, a focus assistant. {profile.description}"
        
        prompt = f"""{personality_desc}

{context}

User said: "{transcript}"

Respond briefly and in character. Keep it short (1-2 sentences max). Be encouraging but firm if they're off track.

Response:"""
        
        try:
            response = self.ollama_client.generate(
                model=self.ollama_model,
                prompt=prompt,
                options={
                    "temperature": 0.7,
                    "num_predict": 100  # Limit response length
                }
            )
            
            return response.get("response", "").strip()
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None
    
    def _handle_mic_error(self, error: Exception):
        """Handle microphone permission errors gracefully."""
        error_str = str(error).lower()
        if "permission" in error_str or "denied" in error_str:
            logger.error("Microphone permission denied")
            # Alert will be shown by UI
            raise PermissionError(
                "Microphone access denied. Go to System Settings → Privacy & Security → Microphone and enable Code Sergeant."
            )
        else:
            logger.error(f"Microphone error: {error}")
            raise


def run_voice_worker(
    voice_worker: VoiceWorker,
    goal: Optional[str],
    current_activity: Optional[str],
    event_queue
):
    """
    Run voice worker in a thread.
    
    Args:
        voice_worker: VoiceWorker instance
        goal: Current goal
        current_activity: Current activity string
        event_queue: Event queue to emit events to
    """
    try:
        transcript, command = voice_worker.record_and_process(goal, current_activity)
        
        if command:
            # Emit command event
            event_queue.put({
                'type': 'voice_command',
                'command': command.command_type,
                'args': command.args,
                'transcript': transcript,
                'timestamp': time.time()
            })
        elif transcript:
            # Emit transcript event
            event_queue.put({
                'type': 'voice_transcript',
                'transcript': transcript,
                'timestamp': time.time()
            })
    except PermissionError as e:
        # Re-raise permission errors so UI can handle them
        raise
    except Exception as e:
        logger.error(f"Voice worker error: {e}")
        event_queue.put({
            'type': 'error_event',
            'message': f"Voice processing error: {e}"
        })
