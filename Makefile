POETRY = python3.7 -m poetry 
DB = dumpling.db

.PHONY: setup db lint serve

setup:
	$(POETRY) update

db:
	rm -f $(DB)
	env DUMPLING_DB_PATH=$(DB) $(POETRY) run ./dumpling.py

lint:
	$(POETRY) run black .
	$(POETRY) run isort .
	$(POETRY) run mypy

serve:
	env DUMPLING_DB_PATH=$(DB) FLASK_APP=dumpling.py $(POETRY) run flask run --host 0 --reload

