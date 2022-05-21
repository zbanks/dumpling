# dumpling
Crossword clue lookup tool

## Setup
```
python3.7 -m virtualenv venv
source venv/bin/activate.sh

pip install -r requirements.txt -r requirements.dev
# OR: pip install -r requirements.lock

# Generate clue database
rm -f dumpling.db; ./dumpling.py

# Run debug server (bound to INET_ANY & with reloading)
env FLASK_APP=dumpling.py flask run --host 0 --reload
```
