# Chameleon - AI Language Model Game

A Python implementation of the popular party game "Chameleon" where AI Language Models compete against each other. One AI is randomly chosen as the "Chameleon" who doesn't know the secret word and must avoid detection while other AIs try to identify them.

## Game Setup

1. A category is set and secret word is randomly chosen (e.g., Category: Movies, Word: Jaws)
2. One AI is randomly selected as the Chameleon (doesn't know the secret word)
3. Each AI (including the Chameleon) gives a one-word hint related to the secret word
4. AIs vote on who they think is the Chameleon
5. The Chameleon gets one chance to guess the word


## Features

- Multiple AI players using different language models:
  - Alice (GPT-4)
  - Bob (OpenAI O1)
  - Charlie (Claude Sonnet)
  - David (Claude Haiku)
  - Eve (Gemini)
- Multiple categories (Movies, Animals, Cities, etc.)
- Fair play mechanisms (random turn order with systematic shifting)
- Detailed statistics tracking
- Game logging with timestamps

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/chameleon.git
cd chameleon
```

2. Install required packages:
```bash
pip install anthropic openai google-generativeai pydantic
```
Note: Standard library packages (`json`, `random`, `typing`, `dataclasses`, `enum`, `os`, `datetime`) are included with Python 3.8+.

3. Set up your configuration:
```bash
cp config.template.py config.py
```
Then edit `config.py` with your API keys:
```python
import os

os.environ['ANTHROPIC_API_KEY'] = 'your-anthropic-key'
os.environ['OPENAI_API_KEY'] = 'your-openai-key'
os.environ['GEMINI_API_KEY'] = 'your-gemini-key'
```
Note: `config.py` is gitignored to prevent accidentally committing your API keys.

## Usage

Run the game:
```bash
python main.py
```

The game will:
1. Play through all categories
2. Generate a statistics file with timestamp
3. Display results in the console

## Project Structure

- `main.py`: Entry point and game initialization
- `game_controller.py`: Core game logic and flow control
- `game_models.py`: Data models and enums
- `llm_handler.py`: AI language model integration
- `game_data.py`: Categories and word lists
- `config.py`: API key configuration

## Statistics

The game tracks various statistics for each AI player:
- Times played as Chameleon
- Times identified when Chameleon
- Correct word guesses
- Correct votes for Chameleon

## Contributing

Contributions are welcome! Some areas for improvement:
1. Additional categories and words
2. New AI models
3. Better logging of results
3. Enhanced game mechanics
4. UI improvements

## License

MIT License - feel free to use and modify as needed.

## Acknowledgments

- Inspired by the original Chameleon party game
- Uses APIs from OpenAI, Anthropic, and Google

## Note

This is an experimental project showcasing AI language models' capabilities in a game setting. API usage may incur costs. 