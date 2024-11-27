import config  # This needs to be the first import
from game_controller import ChameleonGame
from game_data import cards
import json
from datetime import datetime

def main():
    # Create unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stats_file = f"chameleon_stats_{timestamp}.json"
    
    game = ChameleonGame(cards)
    game.play_tournament(rounds_per_category=1)
    
    # Save statistics to file
    stats = game.get_final_stats()
    stats_output = {}
    for model, stat in stats.items():
        stats_output[model.player_name] = {
            "times_as_chameleon": stat.times_as_chameleon,
            "times_identified": stat.times_identified,
            "correct_guesses": stat.correct_guesses,
            "correct_votes": stat.correct_votes,
        }
    
    with open(stats_file, 'w') as f:
        json.dump(stats_output, f, indent=4)
    
    print(f"\n\nGame complete! Statistics have been saved to {stats_file}")
    
if __name__ == "__main__":
    main() 