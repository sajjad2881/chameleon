from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime

@dataclass
class ModelConfig:
    provider: str  # 'openai', 'anthropic', or 'google'
    model_name: str  # The actual model identifier used in API calls
    player_name: str  # The human-readable name in the game (Alice, Bob, etc.)

class LLMType(Enum):
    # OpenAI Models
    GPT4_MINI = ModelConfig("openai", "gpt-4o-mini", "Alice")
    O1_MINI = ModelConfig("openai", "o1-mini", "Bob")
    
    # Anthropic Models
    CLAUDE_SONNET = ModelConfig("anthropic", "claude-3-5-sonnet-latest", "Charlie")
    CLAUDE_HAIKU = ModelConfig("anthropic", "claude-3-5-haiku-latest", "David")
    
    # Google Models
    GEMINI_FLASH = ModelConfig("google", "gemini-1.5-flash", "Eve")

    @property
    def provider(self) -> str:
        return self.value.provider

    @property
    def model_name(self) -> str:
        return self.value.model_name

    @property
    def player_name(self) -> str:
        return self.value.player_name

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
    times_falsely_accused: int = 0  # Times incorrectly voted as Chameleon

@dataclass
class DetailedGameLog:
    timestamp: datetime
    category: str
    word: str
    chameleon: str  # player_name
    player_hints: List[Dict[str, str]]  # [{player_name: hint}, ...]
    initial_votes: Dict[str, str]  # voter_name -> voted_name
    final_suspect: str  # player_name
    was_chameleon_caught: bool
    did_chameleon_guess_correctly: bool
    tie_break_votes: Optional[Dict[str, str]] = None  # voter_name -> voted_name
    chameleon_guess: Optional[str] = None
    winner: Optional[str] = None  # player_name