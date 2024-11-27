import random
from typing import Dict, List, Tuple
from datetime import datetime
import json
from game_models import LLMType, GameRound, GameTurn, PlayerStats, DetailedGameLog
from llm_handler import LLMHandler

class ChameleonGame:
    def __init__(self, cards: Dict[str, List[str]]):
        self.cards = cards
        self.llm_handler = LLMHandler(cards)
        self.players = list(LLMType)
        self.stats = {model: PlayerStats() for model in LLMType}
        self.game_log = []
        self.detailed_logs = []  # List[DetailedGameLog]

    def play_tournament(self, rounds_per_category: int = 2):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        detailed_log_file = f"chameleon_detailed_log_{timestamp}.json"
        
        for category, words in self.cards.items():
            print(f"\nPlaying category: {category}")
            for round_num in range(rounds_per_category):
                print(f"\nRound {round_num + 1}")
                word = random.choice(words)
                chameleon = random.choice(self.players)
                player_order = self.players.copy()
                shift = len(self.detailed_logs) % len(player_order)
                player_order = player_order[shift:] + player_order[:shift]
                random.shuffle(player_order)
                
                round = self.play_round(category, word, chameleon, player_order)
                self.game_log.append(round)
                self._update_stats(round)
                
                # Create detailed log
                detailed_log = self._create_detailed_log(round)
                self.detailed_logs.append(detailed_log)
                
                # Save logs after each round
                self._save_detailed_logs(detailed_log_file)

    def _create_detailed_log(self, round: GameRound) -> DetailedGameLog:
        # Convert initial votes to player names
        initial_votes = {
            voter.player_name: vote.player_name 
            for voter, vote in round.votes.items()
        }
        
        # Create player hints list
        player_hints = [
            {turn.player.player_name: turn.hint}
            for turn in round.turns
        ]
        
        # Determine if chameleon was caught (majority voted for them)
        votes_for_chameleon = sum(1 for v in round.votes.values() if v == round.chameleon)
        was_caught = votes_for_chameleon > len(self.players) / 2
        
        # Check if chameleon guessed correctly
        guessed_correctly = (
            round.chameleon_guess and 
            round.chameleon_guess.lower() == round.word.lower()
        )
        
        return DetailedGameLog(
            timestamp=datetime.now(),
            category=round.category,
            word=round.word,
            chameleon=round.chameleon.player_name,
            player_hints=player_hints,
            initial_votes=initial_votes,
            tie_break_votes=None,  # TODO: Add tie break votes if they occurred
            final_suspect=max(
                initial_votes.values(),
                key=lambda x: list(initial_votes.values()).count(x)
            ),
            chameleon_guess=round.chameleon_guess,
            winner=round.winner.player_name if round.winner else None,
            was_chameleon_caught=was_caught,
            did_chameleon_guess_correctly=guessed_correctly
        )

    def _save_detailed_logs(self, filename: str):
        # Convert DetailedGameLog objects to dictionaries
        log_dicts = []
        for log in self.detailed_logs:
            log_dict = {
                'timestamp': log.timestamp.isoformat(),
                'category': log.category,
                'word': log.word,
                'chameleon': log.chameleon,
                'player_hints': log.player_hints,
                'initial_votes': log.initial_votes,
                'tie_break_votes': log.tie_break_votes,
                'final_suspect': log.final_suspect,
                'chameleon_guess': log.chameleon_guess,
                'winner': log.winner,
                'was_chameleon_caught': log.was_chameleon_caught,
                'did_chameleon_guess_correctly': log.did_chameleon_guess_correctly
            }
            log_dicts.append(log_dict)
        
        # Save to file with pretty printing
        with open(filename, 'w') as f:
            json.dump(log_dicts, f, indent=2)

    def play_round(self, category: str, word: str, 
                   chameleon: LLMType, player_order: List[LLMType]) -> GameRound:
        print(f"Secret word: {word}")
        print(f"Chameleon: {chameleon.player_name}")

        
        turns = []
        previous_hints = []
        
        # Get hints from all players
        for turn_num, player in enumerate(player_order):
            is_chameleon = (player == chameleon)
            hint = self.llm_handler.get_hint(
                player, category, word, previous_hints, is_chameleon
            )
            
            turn = GameTurn(player=player, turn_number=turn_num, 
                          hint=hint, is_chameleon=is_chameleon)
            turns.append(turn)
            previous_hints.append((player, hint))
            print(f"{player.player_name} hint: {hint}")

        # Initial voting phase
        votes = {}
        for player in player_order:
            vote = self.llm_handler.get_vote(
                player, 
                category, 
                [(t.player, t.hint) for t in turns], 
                word if player != chameleon else None
            )
            votes[player] = vote
            print(f"{player.player_name} votes for: {vote.player_name}")

        # Count votes and handle ties
        vote_counts = {}
        for voted_player in votes.values():
            vote_counts[voted_player] = vote_counts.get(voted_player, 0) + 1
        
        print("\nFirst Round Vote Tally:")
        for player in self.players:
            count = vote_counts.get(player, 0)
            print(f"{player.player_name}: {count} vote{'s' if count != 1 else ''}")
        
        # Find players with the most votes
        max_votes = max(vote_counts.values())
        most_voted = [player for player, count in vote_counts.items() if count == max_votes]
        
        # If there's a tie, do a second round of voting between tied players
        if len(most_voted) > 1:
            print("\nTie detected! Second round of voting between:", 
                  ", ".join(p.player_name for p in most_voted))
            
            tie_break_votes = {}
            for player in player_order:
                vote = self.llm_handler.get_tie_break_vote(
                    player, 
                    category, 
                    [(t.player, t.hint) for t in turns],
                    word, 
                    most_voted,
                    is_chameleon=(player == chameleon)
                )
                tie_break_votes[player] = vote
                print(f"{player.player_name} votes for: {vote.player_name}")
            
            # Count tie-break votes
            tie_vote_counts = {}
            for voted_player in tie_break_votes.values():
                tie_vote_counts[voted_player] = tie_vote_counts.get(voted_player, 0) + 1
            
            print("\nTie-Break Vote Tally:")
            for player in most_voted:
                count = tie_vote_counts.get(player, 0)
                print(f"{player.player_name}: {count} vote{'s' if count != 1 else ''}")
            
            most_voted = [max(tie_vote_counts.items(), key=lambda x: x[1])[0]]
        
        final_suspect = most_voted[0]
        
        # Always let the Chameleon guess
        chameleon_guess = self.llm_handler.get_chameleon_guess(
            chameleon, category, [(t.player, t.hint) for t in turns]
        )
        print(f"Chameleon guesses: {chameleon_guess}")
        
        # Determine winner
        if final_suspect == chameleon:
            print("Chameleon was caught!")
            if chameleon_guess.lower() == word.lower():
                winner = chameleon
                print("Chameleon guessed correctly and wins!")
            else:
                winner = None
                print("Chameleon guessed wrong - no winner!")
        else:
            winner = chameleon
            print("Chameleon wasn't caught and wins!")

        return GameRound(
            category=category,
            word=word,
            chameleon=chameleon,
            turns=turns,
            votes=votes,
            winner=winner,
            chameleon_guess=chameleon_guess  # Always include the guess
        )

    def get_final_stats(self) -> Dict[LLMType, PlayerStats]:
        return self.stats

    def print_game_log(self):
        for round in self.game_log:
            print(f"\nCard: {round.category}")
            print(f"Secret word: {round.word}")
            print(f"Chameleon: {round.chameleon.player_name}")
            for turn in round.turns:
                print(f"{turn.player.player_name}: Turn: {turn.turn_number} "
                      f"Hint: {turn.hint} Chameleon: {turn.is_chameleon}")
            print(f"Voting Results: {[(k.player_name, v.player_name) for k,v in round.votes.items()]}")
            if round.chameleon_guess:
                print(f"Chameleon guess: {round.chameleon_guess}")
            print(f"Winner: {round.winner.player_name if round.winner else 'No winner'}")

    def _update_stats(self, round: GameRound):
        # Update chameleon stats
        self.stats[round.chameleon].times_as_chameleon += 1
        
        # Count votes for each player
        vote_counts = {}
        for voted_player in round.votes.values():
            vote_counts[voted_player] = vote_counts.get(voted_player, 0) + 1
        
        # Check if chameleon was identified
        votes_for_chameleon = vote_counts.get(round.chameleon, 0)
        if votes_for_chameleon > len(self.players) / 2:  # Majority voted correctly
            self.stats[round.chameleon].times_identified += 1
        
        # Track correct guesses regardless of whether chameleon was identified
        if round.chameleon_guess and round.chameleon_guess.lower() == round.word.lower():
            self.stats[round.chameleon].correct_guesses += 1
        
        # Update voting stats and track false accusations
        for voter, vote in round.votes.items():
            if vote == round.chameleon:
                self.stats[voter].correct_votes += 1
            elif vote != round.chameleon and vote_counts.get(vote, 0) > len(self.players) / 2:
                # If a non-chameleon got majority votes, increment their false accusation counter
                self.stats[vote].times_falsely_accused += 1

    def _tally_votes(self, votes: Dict[LLMType, LLMType]):
        vote_counts = {}
        for voted_player in votes.values():
            vote_counts[voted_player] = vote_counts.get(voted_player, 0) + 1
        
        print("\nVote Tally:")
        for player in self.players:
            count = vote_counts.get(player, 0)
            print(f"{player.player_name}: {count} vote{'s' if count != 1 else ''}")
        print()
        
        return max(vote_counts.items(), key=lambda x: x[1])[0]