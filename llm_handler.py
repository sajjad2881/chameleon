import os
from typing import List, Tuple, Dict
import anthropic
from openai import OpenAI
import google.generativeai as genai
from game_models import LLMType
import random
from pydantic import BaseModel

SYSTEM_PROMPT = """You're an AI player in a game of Chameleon. A secret word will be chosen from a given category - only legitimate players know this word, while one player (the Chameleon) doesn't. When it's your turn, you must provide a single-word clue related to the secret word. Keep the entire set of possible words in mind when giving the clue. Your clue should be clever enough to prove you know the word, but vague enough that the Chameleon can't guess. If you are the Chameleon, give a clue such as to avoid detection. IN ALL CIRCUMSTANCES answer with one word only. Once the round is done, we will vote on the Chameleon. If you are the Chameleon, you win if you are not voted Chameleon. If you are not the Chameleon, you win if you correctly vote for the Chameleon and the majority agrees."""

class Hint(BaseModel):
    hint: str

class Vote(BaseModel):
    player_name: str

class LLMHandler:
    def __init__(self, cards: Dict[str, List[str]]):
        self.openai_client = OpenAI()
        self.anthropic_client = anthropic.Anthropic()
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        self.gemini_model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        self.cards = cards

    def _sanitize_hint(self, hint_text: str, secret_word: str = None) -> str:
        """Use OpenAI to ensure we get a single-word hint that isn't the secret word."""
        try:
            completion = self.openai_client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract a one-word hint from the text. The hint cannot be the secret word itself."},
                    {"role": "user", "content": f"Secret word: {secret_word}\nHint text: {hint_text}"},
                ],
                response_format=Hint,
            )
            hint = completion.choices[0].message.parsed.hint
            # Double check it's not the secret word
            if secret_word and hint.lower() == secret_word.lower():
                return "invalid"  # Force them to try again
            return hint
        except Exception as e:
            print(f"Error in hint sanitization: {e}")
            return hint_text.strip().split()[0]  # Fallback to simple extraction

    def _sanitize_vote(self, vote_text: str) -> str:
        """Use OpenAI to ensure we get a single player name."""
        try:
            completion = self.openai_client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract the player name (Alice, Bob, Charlie, David, or Eve) from the text. Return only that name."},
                    {"role": "user", "content": vote_text},
                ],
                response_format=Vote,
            )
            return completion.choices[0].message.parsed.player_name
        except Exception as e:
            print(f"Error in vote sanitization: {e}")
            return vote_text.strip().split()[0]  # Fallback to simple extraction

    def get_hint(self, model: LLMType, category: str, word: str, 
                 previous_hints: List[tuple[str, str]], is_chameleon: bool) -> str:
        print(f"\n{model.player_name} is thinking of a hint...")
        if is_chameleon:
            word = None
            print(f"({model.player_name} is the Chameleon and doesn't know the word)")
            
        prompt = self._create_hint_prompt(category, word, previous_hints)
        
        try:
            if model in [LLMType.GPT4_MINI, LLMType.O1_PREVIEW]:
                hint = self._get_openai_hint(model.value, prompt)
            elif model in [LLMType.CLAUDE_SONNET, LLMType.CLAUDE_HAIKU]:
                hint = self._get_claude_hint(model.value, prompt)
            else:
                hint = self._get_gemini_hint(prompt)
            
            # Remove the sanitization - let the models give their own hints
            print(f"{model.player_name} gives hint: {hint}")
            return hint
        except Exception as e:
            print(f"Error getting hint from {model.player_name}: {e}")
            return "error"

    def get_vote(self, model: LLMType, category: str, 
                 all_hints: List[Tuple[LLMType, str]], word: str = None) -> LLMType:
        print(f"\n{model.player_name} is considering who might be the Chameleon...")
        
        # Different prompt for chameleon vs regular players
        if word:
            prompt = (f"You are playing as {model.player_name}. The category is '{category}' and "
                     f"these are all possible words: {self.cards[category]}. "
                     f"The secret word is '{word}'. Given these hints:\n")
        else:
            prompt = (f"You are playing as {model.player_name} and you are the Chameleon. "
                     f"The category is '{category}' and these are all possible words: {self.cards[category]}. "
                     f"You need to vote for someone else to avoid suspicion. Given these hints:\n")
        
        for player, hint in all_hints:
            prompt += f"{player.player_name}: {hint}\n"
        
        prompt += (f"\nAs {model.player_name}, who do you think is the Chameleon? "
                  f"You cannot vote for yourself. "
                  f"Choose from these players (excluding yourself): ")
        
        # List all players except the current one
        other_players = [p.player_name for p in LLMType if p.player_name != model.player_name]
        prompt += ", ".join(other_players)
        
        prompt += "\nAnswer with just one name."

        try:
            if model in [LLMType.GPT4_MINI, LLMType.O1_PREVIEW]:
                response = self.openai_client.chat.completions.create(
                    model=model.value,
                    messages=[
                        {"role": "assistant", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    max_completion_tokens=500 if model == LLMType.O1_PREVIEW else None,
                    max_tokens=500 if model != LLMType.O1_PREVIEW else None
                )
                response = response.choices[0].message.content.strip()
            elif model in [LLMType.CLAUDE_SONNET, LLMType.CLAUDE_HAIKU]:
                response = self.anthropic_client.messages.create(
                    model=model.value,
                    max_tokens=500,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}]
                )
                response = response.content[0].text.strip()
            else:
                gemini = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=SYSTEM_PROMPT
                )
                response = gemini.generate_content(prompt)
                response = response.text.strip()

            # Sanitize the vote to ensure it's a valid player name
            sanitized_vote = self._sanitize_vote(response)
            print(f"{model.player_name}'s vote: {sanitized_vote}")

            # Convert name response back to LLMType
            name_to_model = {t.player_name.lower(): t for t in LLMType}
            if sanitized_vote.lower() in name_to_model:
                voted_player = name_to_model[sanitized_vote.lower()]
                print(f"{model.player_name} votes for {voted_player.player_name}")
                return voted_player
            
            random_vote = random.choice(list(LLMType))
            print(f"{model.player_name} gave unclear response, randomly voting for {random_vote.player_name}")
            return random_vote
        except Exception as e:
            random_vote = random.choice(list(LLMType))
            print(f"Error getting vote from {model.player_name}: {e}")
            print(f"Falling back to random vote: {random_vote.player_name}")
            return random_vote

    def get_chameleon_guess(self, model: LLMType, category: str, 
                           all_hints: List[Tuple[LLMType, str]]) -> str:
        print(f"\n{model.player_name} (Chameleon) is trying to guess the word...")
        prompt = f"You are the Chameleon in the game. The category is '{category}'. "
        prompt += "Given these previous guesses:\n"
        for player, hint in all_hints:
            prompt += f"{player.player_name}: {hint}\n"
        prompt += "\nWhat is your guess? Answer with just one word."

        try:
            if model in [LLMType.GPT4_MINI, LLMType.O1_PREVIEW]:
                guess = self._get_openai_hint(model.value, prompt)
            elif model in [LLMType.CLAUDE_SONNET, LLMType.CLAUDE_HAIKU]:
                guess = self._get_claude_hint(model.value, prompt)
            else:
                guess = self._get_gemini_hint(prompt)
            print(f"{model.player_name} guesses: {guess}")
            return guess
        except Exception as e:
            print(f"Error getting guess from {model.player_name}: {e}")
            return "unknown"

    def _create_hint_prompt(self, category: str, word: str, 
                           previous_hints: List[Tuple[str, str]]) -> str:
        base_prompt = (f"The category is '{category}' and these are all possible words: "
                      f"{self.cards[category]}. ")
        
        if word:
            base_prompt += f"The secret word is '{word}'. "
        else:
            base_prompt += "You don't know the secret word. "
        
        if previous_hints:
            base_prompt += "\nPrevious hints:\n"
            for player_name, hint in previous_hints:
                player_name_mapping = {
                    "gpt-4o-mini": "Alice",
                    "o1-preview": "Bob",
                    "claude-3-5-sonnet-latest": "Charlie",
                    "claude-3-5-haiku-latest": "David",
                    "gemini-1.5-flash": "Eve"
                }
                human_name = player_name_mapping.get(player_name, player_name)
                base_prompt += f"{human_name}: {hint}\n"
        
        base_prompt += "\nGive your ONE-WORD hint:"
        return base_prompt

    def _create_vote_prompt(self, category: str, word: str, 
                          all_hints: List[Tuple[LLMType, str]], is_chameleon: bool) -> str:
        base_prompt = (f"The category is '{category}' and these are all possible words: "
                      f"{self.cards[category]}. ")
        
        if not is_chameleon:
            base_prompt += f"The secret word is '{word}'. "
        else:
            base_prompt += "You are the Chameleon and need to vote to avoid suspicion. "
        
        base_prompt += "\nAll hints given:\n"
        for player, hint in all_hints:
            base_prompt += f"{player.player_name}: {hint}\n"
        
        base_prompt += "\nWho do you think is the Chameleon? Answer with just their name (Alice, Bob, Charlie, David, or Eve)."
        return base_prompt

    def _get_openai_hint(self, model: str, prompt: str) -> str:
        try:
            if model == "o1-mini":
                response = self.openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "assistant", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    max_completion_tokens=500
                )
            else:
                response = self.openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "assistant", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500
                )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error in OpenAI call: {e}")
            return str(e)

    def _get_claude_hint(self, model: str, prompt: str) -> str:
        try:
            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=500,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"Error getting hint from {model}: {e}")
            return str(e)

    def _get_gemini_hint(self, prompt: str) -> str:
        try:
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=SYSTEM_PROMPT
            )
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error getting hint from gemini: {e}")
            return str(e)

    def get_tie_break_vote(self, model: LLMType, category: str, 
                          all_hints: List[Tuple[LLMType, str]], 
                          word: str, tied_players: List[LLMType]) -> LLMType:
        print(f"\n{model.player_name} is voting in the tie-break...")
        
        prompt = (f"You are playing as {model.player_name}. The category is '{category}' and "
                 f"these are all possible words: {self.cards[category]}. "
                 f"The secret word is '{word}'. Given these hints:\n")
        
        for player, hint in all_hints:
            prompt += f"{player.player_name}: {hint}\n"
        
        prompt += "\nThere was a tie between these players: "
        prompt += ", ".join(p.player_name for p in tied_players)
        prompt += "\nWho do you think is the Chameleon? Choose only from the tied players listed above."
        
        try:
            if model in [LLMType.GPT4_MINI, LLMType.O1_PREVIEW]:
                response = self.openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "assistant", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500 if model != "o1-preview" else None,
                    max_completion_tokens=500 if model == "o1-preview" else None
                )
                response = response.choices[0].message.content.strip()
            elif model in [LLMType.CLAUDE_SONNET, LLMType.CLAUDE_HAIKU]:
                response = self.anthropic_client.messages.create(
                    model=model,
                    max_tokens=500,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}]
                )
                response = response.content[0].text.strip()
            else:
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=SYSTEM_PROMPT
                )
                response = model.generate_content(prompt)
                response = response.text.strip()

            sanitized_vote = self._sanitize_vote(response)
            print(f"{model.player_name}'s tie-break vote: {sanitized_vote}")

            # Convert name response back to LLMType
            name_to_model = {t.player_name.lower(): t for t in tied_players}
            if sanitized_vote.lower() in name_to_model:
                voted_player = name_to_model[sanitized_vote.lower()]
                return voted_player
            
            return random.choice(tied_players)  # Fallback to random choice among tied players
        except Exception as e:
            print(f"Error in tie-break vote from {model.player_name}: {e}")
            return random.choice(tied_players)
