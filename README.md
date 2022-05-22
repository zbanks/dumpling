# dumpling
[Dumpling](https://dumpling.fly.dev/) is a crossword clue search tool.
It's similar to <a href="https://www.wordplays.com/">Wordplays.com</a> or <a href="https://crossword-solver.io/">Crossword Solver</a>.

It uses a the <a href="https://huggingface.co/datasets/albertxu/CrosswordQA">CrosswordQA</a> dataset of 6.8 million clues prepared by Albert Xu.

Pull requests welcome!

## Running locally
```
python3.7 -m pip install -U poetry
make setup

# Generate clue database
make db

# Run debug server (bound to INET_ANY & with reloading)
make serve
```
