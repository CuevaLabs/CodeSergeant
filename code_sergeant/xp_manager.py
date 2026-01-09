"""XP and Rank management system for Code Sergeant."""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger("code_sergeant.xp_manager")

# Default rank configuration
DEFAULT_RANKS = [
    {"name": "Recruit", "xp_threshold": 0, "icon": "🎖️"},
    {"name": "Private", "xp_threshold": 100, "icon": "⭐"},
    {"name": "Corporal", "xp_threshold": 300, "icon": "⭐⭐"},
    {"name": "Sergeant", "xp_threshold": 600, "icon": "⭐⭐⭐"},
    {"name": "Staff Sergeant", "xp_threshold": 1000, "icon": "🎖️⭐"},
    {"name": "Captain", "xp_threshold": 1500, "icon": "🎖️⭐⭐"},
]


@dataclass
class RankLevel:
    """Represents a rank level with requirements."""

    name: str
    xp_threshold: int
    icon: str  # emoji or symbol


@dataclass
class XPState:
    """Current XP state."""

    total_xp: int = 0
    current_rank: str = "Recruit"
    rank_index: int = 0
    session_xp: int = 0  # XP earned in current session
    last_updated: str = ""


class XPManager:
    """Manages XP awards, rank progression, and persistence."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize XP manager.

        Args:
            config: Application configuration dictionary
        """
        self.config = config
        xp_config = config.get("xp", {})

        # XP settings
        self.xp_per_minute = xp_config.get("xp_per_minute", 1)
        self.early_end_penalty_percent = xp_config.get("early_end_penalty_percent", 50)
        self.enabled = xp_config.get("enabled", True)

        # Load ranks from config (or use defaults)
        self.ranks = self._load_ranks()

        # Load persisted state
        self.state = self._load_state()

        logger.info(
            f"XPManager initialized: {len(self.ranks)} ranks, "
            f"{self.xp_per_minute} XP/min, {self.early_end_penalty_percent}% penalty"
        )
        logger.info(
            f"Current state: {self.state.total_xp} XP, Rank: {self.state.current_rank}"
        )

    def _load_ranks(self) -> list[RankLevel]:
        """Load rank definitions from config or defaults."""
        xp_config = self.config.get("xp", {})
        rank_data = xp_config.get("ranks", DEFAULT_RANKS)

        ranks = []
        for r in rank_data:
            try:
                ranks.append(
                    RankLevel(
                        name=r["name"],
                        xp_threshold=r["xp_threshold"],
                        icon=r.get("icon", "⭐"),
                    )
                )
            except (KeyError, TypeError) as e:
                logger.error(f"Invalid rank config: {r}, error: {e}")
                continue

        # Ensure ranks are sorted by threshold
        ranks.sort(key=lambda r: r.xp_threshold)

        if not ranks:
            logger.warning("No valid ranks found, using defaults")
            ranks = [RankLevel(**r) for r in DEFAULT_RANKS]

        return ranks

    def _load_state(self) -> XPState:
        """Load XP state from persistent storage."""
        state_file = self._get_state_file()

        if state_file.exists():
            try:
                with open(state_file, "r") as f:
                    data = json.load(f)
                state = XPState(**data)
                logger.info(f"Loaded XP state from {state_file}")
                return state
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to load XP state: {e}, starting fresh")

        # Return fresh state if file doesn't exist or is invalid
        return XPState()

    def _save_state(self):
        """Persist XP state to disk."""
        if not self.enabled:
            return

        state_file = self._get_state_file()
        state_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.state.last_updated = datetime.now().isoformat()
            with open(state_file, "w") as f:
                json.dump(asdict(self.state), f, indent=2)
            logger.debug(f"Saved XP state: {self.state.total_xp} XP")
        except Exception as e:
            logger.error(f"Failed to save XP state: {e}")

    def _get_state_file(self) -> Path:
        """Get path to state file."""
        return Path.home() / ".code_sergeant" / "xp_state.json"

    def _update_rank(self):
        """Update rank based on total XP."""
        old_rank = self.state.current_rank

        # Find highest rank achieved
        for i, rank in enumerate(self.ranks):
            if self.state.total_xp >= rank.xp_threshold:
                self.state.current_rank = rank.name
                self.state.rank_index = i
            else:
                break

        if old_rank != self.state.current_rank:
            logger.info(
                f"Rank up! {old_rank} -> {self.state.current_rank} "
                f"({self.state.total_xp} XP)"
            )

    def award_xp(self, minutes: int) -> int:
        """
        Award XP for focus time.

        Args:
            minutes: Number of minutes of focus time

        Returns:
            XP awarded
        """
        if not self.enabled:
            return 0

        xp = minutes * self.xp_per_minute
        self.state.total_xp += xp
        self.state.session_xp += xp

        self._update_rank()
        self._save_state()

        logger.info(f"Awarded {xp} XP for {minutes} min focus (total: {self.state.total_xp})")
        return xp

    def deduct_xp_for_early_end(self) -> int:
        """
        Deduct XP penalty for ending session early.

        Returns:
            XP deducted (penalty amount)
        """
        if not self.enabled or self.state.session_xp == 0:
            return 0

        penalty = int(self.state.session_xp * (self.early_end_penalty_percent / 100))
        self.state.total_xp = max(0, self.state.total_xp - penalty)

        self._update_rank()
        self._save_state()

        logger.warning(
            f"Early end penalty: -{penalty} XP ({self.early_end_penalty_percent}% "
            f"of {self.state.session_xp} session XP), total now: {self.state.total_xp}"
        )
        return penalty

    def get_next_rank_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about next rank.

        Returns:
            Dict with next rank info, or None if at max rank
        """
        next_index = self.state.rank_index + 1

        if next_index < len(self.ranks):
            next_rank = self.ranks[next_index]
            current_rank = self.ranks[self.state.rank_index]
            xp_needed = next_rank.xp_threshold - self.state.total_xp

            # Progress from current rank to next rank
            xp_range = next_rank.xp_threshold - current_rank.xp_threshold
            xp_progress = self.state.total_xp - current_rank.xp_threshold
            progress = (xp_progress / xp_range) if xp_range > 0 else 1.0

            return {
                "name": next_rank.name,
                "xp_needed": max(0, xp_needed),
                "xp_threshold": next_rank.xp_threshold,
                "progress": min(1.0, max(0.0, progress)),  # Clamp to 0-1
                "icon": next_rank.icon,
            }

        return None

    def reset_session(self):
        """Reset session XP counter."""
        self.state.session_xp = 0
        self._save_state()
        logger.info("Session XP reset to 0")

    def get_state_dict(self) -> Dict[str, Any]:
        """
        Get current state as dictionary for API.

        Returns:
            Dict with XP state info
        """
        current_rank_obj = self.ranks[self.state.rank_index]
        next_rank_info = self.get_next_rank_info()

        return {
            "total_xp": self.state.total_xp,
            "session_xp": self.state.session_xp,
            "current_rank": self.state.current_rank,
            "rank_index": self.state.rank_index,
            "rank_icon": current_rank_obj.icon,
            "next_rank_name": next_rank_info["name"] if next_rank_info else None,
            "xp_to_next_rank": next_rank_info["xp_needed"] if next_rank_info else 0,
            "rank_progress": next_rank_info["progress"] if next_rank_info else 1.0,
            "xp_per_minute": self.xp_per_minute,
            "early_end_penalty_percent": self.early_end_penalty_percent,
            "enabled": self.enabled,
        }

    def reset_all_xp(self):
        """Reset all XP and rank to starting state (for testing/admin)."""
        self.state = XPState()
        self._save_state()
        logger.warning("All XP and rank reset to starting state")

    def get_rank_list(self) -> list[Dict[str, Any]]:
        """
        Get list of all ranks with info.

        Returns:
            List of rank dictionaries
        """
        return [
            {
                "name": rank.name,
                "xp_threshold": rank.xp_threshold,
                "icon": rank.icon,
                "achieved": self.state.total_xp >= rank.xp_threshold,
            }
            for rank in self.ranks
        ]
