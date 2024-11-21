from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class LLMType(Enum):
    GPT4_MINI = "gpt-4o-mini"
    O1_MINI = "o1-mini"
    CLAUDE_SONNET = "claude-3-5-sonnet-latest"
    CLAUDE_HAIKU = "claude-3-5-haiku-latest"
    GEMINI_FLASH = "gemini-1.5-flash"

    @property
    def player_name(self) -> str:
        name_mapping = {
            "gpt-4o-mini": "Alice",
            "o1-mini": "Bob",
            "claude-3-5-sonnet-latest": "Charlie",
            "claude-3-5-haiku-latest": "David",
            "gemini-1.5-flash": "Eve"
        }
        return name_mapping[self.value]

@dataclass
class GameTurn:
    player: LLMType
    turn_number: int
    hint: str
    is_chameleon: bool

@dataclass
class GameRound:
    category: str
    word: str
    chameleon: LLMType
    turns: List[GameTurn]
    votes: Dict[LLMType, LLMType]  # voter -> suspected_chameleon
    winner: Optional[LLMType] = None
    chameleon_guess: Optional[str] = None

@dataclass
class PlayerStats:
    times_as_chameleon: int = 0
    times_identified: int = 0
    correct_guesses: int = 0
    correct_votes: int = 0 