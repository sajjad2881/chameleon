import os
from typing import List, Tuple, Dict
import anthropic
from openai import OpenAI
import google.generativeai as genai
from game_models import LLMType
import random
from pydantic import BaseModel

SYSTEM_PROMPT = """You're an AI player in a game of Chameleon. A secret word will be chosen from a given category - only legitimate players know this word, while one player (the Chameleon) doesn't. When it's your turn, you must provide a single-word clue related to the secret word in the context of the category and the rest of the possible words. Keep the entire set of possible words in mind when giving the clue. Your clue should be clever enough to prove to the other players that you know the word, but vague enough that the Chameleon can't guess the word from your hint. If you are the Chameleon, give a clue such as to avoid detection, so the other players don't vote you out. IN ALL CIRCUMSTANCES answer with one word only. Once the round is done, we will vote on the Chameleon. If you are the Chameleon, you win if you are not voted Chameleon. If you are not the Chameleon, you win if you correctly vote for the Chameleon and the majority agrees."""

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
        self.current_model = None  # Track current model

    def _sanitize_hint(self, hint_text: str, secret_word: str = None) -> str:
        """Ensure we get a single-word hint that isn't the secret word."""
        try:
            completion = self.openai_client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract the player's one-word hint from the text. The hint cannot be the secret word itself."},
                    {"role": "user", "content": f"Secret word: {secret_word}\n Hint text: {hint_text}"},
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
        """Ensure we get a single player name in the vote."""
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

    def _call_llm(self, model: LLMType, prompt: str) -> str:
        """Central method for all LLM API calls."""
        try:
            if model.provider == "openai":
                response = self.openai_client.chat.completions.create(
                    model=model.model_name,
                    messages=[
                        {"role": "assistant", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.choices[0].message.content.strip()
                
            elif model.provider == "anthropic":
                response = self.anthropic_client.messages.create(
                    model=model.model_name,
                    max_tokens=500,  # Only needed for Anthropic
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text.strip()
                
            elif model.provider == "google":
                gemini = genai.GenerativeModel(
                    model_name=model.model_name,
                    system_instruction=SYSTEM_PROMPT
                )
                response = gemini.generate_content(prompt)
                return response.text.strip()
            
            else:
                raise ValueError(f"Unsupported model provider: {model.provider}")
                
        except Exception as e:
            print(f"Error calling {model.player_name}: {e}")
            return str(e)

    def get_hint(self, model: LLMType, category: str, word: str, 
                 previous_hints: List[Tuple[LLMType, str]], is_chameleon: bool) -> str:
        #print(f"\n{model.player_name} is thinking of a hint...")
        if is_chameleon:
            print(f"({model.player_name} is the Chameleon and doesn't know the word)")
            
        prompt = self._create_hint_prompt(category, word, previous_hints, is_chameleon)
        hint = self._call_llm(model, prompt)
        #print(f"{model.player_name} gives hint: {hint}")
        return hint
    def _create_hint_prompt(self, category: str, word: str, 
                           previous_hints: List[Tuple[LLMType, str]], 
                           is_chameleon: bool = False) -> str:
        base_prompt = (f"The category is '{category}' and these are all possible words: "
                      f"{self.cards[category]}. ")
        
        if not is_chameleon:
            base_prompt += f"The secret word is '{word}'. "
        else:
            base_prompt += "You don't know the secret word. "
        
        if previous_hints:
            base_prompt += "\nHere are the hints given so far:\n"
            for player, hint in previous_hints:
                base_prompt += f"{player.player_name}: {hint}\n"
        
        base_prompt += "\nRecall the instructions and give your ONE-WORD hint:"
        return base_prompt
            
    def get_vote(self, model: LLMType, category: str, 
                 all_hints: List[Tuple[LLMType, str]], word: str = None) -> LLMType:
        #print(f"\n{model.player_name} is considering who might be the Chameleon...")
        
        is_chameleon = (word is None)  # Determine if this player is the Chameleon
        prompt = self._create_vote_prompt(model, category, word, all_hints, is_chameleon)
        response = self._call_llm(model, prompt)
        
        # Sanitize the vote to ensure it's a valid player name
        sanitized_vote = self._sanitize_vote(response)
        print(f"{model.player_name}'s vote: {sanitized_vote}")

        # Convert name response back to LLMType
        name_to_model = {t.player_name.lower(): t for t in LLMType}
        if sanitized_vote.lower() in name_to_model:
            voted_player = name_to_model[sanitized_vote.lower()]
            #print(f"{model.player_name} votes for {voted_player.player_name}")
            return voted_player
        
        random_vote = random.choice([p for p in LLMType if p != model])  # Don't vote for self
        print(f"{model.player_name} gave unclear response, randomly voting for {random_vote.player_name}")
        return random_vote
    def _create_vote_prompt(self, model: LLMType, category: str, word: str, 
                          all_hints: List[Tuple[LLMType, str]], is_chameleon: bool = False) -> str:
        base_prompt = (f"You are playing as {model.player_name}. The category is '{category}' and these are all possible words: "
                      f"{self.cards[category]}. ")
        
        if not is_chameleon:  # Changed from if word
            base_prompt += f"The secret word is '{word}'. "
        else:
            base_prompt += "You are the Chameleon and need to vote to avoid suspicion. "
        
        base_prompt += "\nAll hints given:\n"
        for player, hint in all_hints:
            base_prompt += f"{player.player_name}: {hint}\n"
        
        base_prompt += "\nWho do you think is the Chameleon? Answer with just their name (Alice, Bob, Charlie, David, or Eve)."
        return base_prompt
    
    def get_tie_break_vote(self, model: LLMType, category: str, 
                          all_hints: List[Tuple[LLMType, str]], 
                          word: str, tied_players: List[LLMType],
                          is_chameleon: bool = False) -> LLMType:
        print(f"\n{model.player_name} is voting in the tie-break...")
        
        prompt = self._create_tiebreak_prompt(model, category, word, all_hints, tied_players, is_chameleon)
        response = self._call_llm(model, prompt)
        
        sanitized_vote = self._sanitize_vote(response)
        print(f"{model.player_name}'s tie-break vote: {sanitized_vote}")

        # Convert name response back to LLMType
        name_to_model = {t.player_name.lower(): t for t in tied_players}
        if sanitized_vote.lower() in name_to_model:
            voted_player = name_to_model[sanitized_vote.lower()]
            return voted_player
        
        return random.choice(tied_players)  # Fallback to random choice among tied players
    def _create_tiebreak_prompt(self, model: LLMType, category: str, word: str, 
                               all_hints: List[Tuple[LLMType, str]], 
                               tied_players: List[LLMType],
                               is_chameleon: bool = False) -> str:
        prompt = (f"You are playing as {model.player_name}. The category is '{category}' and "
                 f"these are all possible words: {self.cards[category]}. ")
        
        if not is_chameleon:  # Use is_chameleon parameter instead of current_model
            prompt += f"The secret word is '{word}'. "
        else:
            prompt += "You are the Chameleon and need to vote to avoid suspicion. "
        
        prompt += "Given these hints:\n"
        for player, hint in all_hints:
            prompt += f"{player.player_name}: {hint}\n"
        
        prompt += "\nThere was a tie between these players: "
        prompt += ", ".join(p.player_name for p in tied_players)
        prompt += "\nWho do you think is the Chameleon? Choose only from the tied players listed above."
        
        return prompt

    def get_chameleon_guess(self, model: LLMType, category: str, 
                           all_hints: List[Tuple[LLMType, str]]) -> str:
        #print(f"\n{model.player_name} (Chameleon) is trying to guess the word...")
        self.current_model = model  # Set current model before creating prompt
        prompt = self._create_chameleon_guess_prompt(model, category, all_hints)
        guess = self._call_llm(model, prompt)
        self.current_model = None  # Reset current model
        print(f"{model.player_name} guesses: {guess}")
        return guess
    def _create_chameleon_guess_prompt(self, model: LLMType, category: str, 
                                        all_hints: List[Tuple[LLMType, str]]) -> str:
            prompt = (f"You are playing as {model.player_name} and you are the Chameleon. "
                    f"The category is '{category}' and these are all possible words: "
                    f"{self.cards[category]}. Given these hints from all players:\n")
            
            for player, hint in all_hints:
                prompt += f"{player.player_name}: {hint}\n"
            
            prompt += ("\nBased on these hints, "
                    "which word from the list do you think is the secret word?"
                    "If you choose the secret word from the list correctly based on the hints, you win the game."
                    "Choose and answer with exactly one of the words/phrases from the list above.")
            return prompt