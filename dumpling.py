#!/usr/bin/env python3.7

import csv
import sqlite3
from pathlib import Path
from collections import defaultdict
from typing import DefaultDict, IO, Iterator, List, Tuple

from flask import Flask, g, request

DATABASE_PATH = Path("dumpling.db")
CROSSWORDQA_PATH = Path("../CrosswordQA/")

DB_SCHEMA = """
    PRAGMA journal_mode = OFF;
    CREATE VIRTUAL TABLE clues USING fts5(
        clue,
        answer UNINDEXED,
        cryptic UNINDEXED
    );
"""


app = Flask(__name__)


def build_database() -> None:
    def norm(ans: str) -> str:
        return ans.replace(" ", "").upper()

    def cqa_iter(f: IO[str]) -> Iterator[Tuple[str, str]]:
        reader = csv.reader(csv_file)
        for _, clue, answer in reader:
            # Some clues in the CSV file were incorrectly parsed (and actually contain multiple rows)
            # Try to reparse them into individual clues
            if "\n" in clue:
                clue, _, final_line = clue.rpartition("\n")
                for line in clue.split("\n"):
                    line = line.strip()
                    subclue, _, subanswer = line.rpartition(" ")
                    assert norm(subanswer) == subanswer and subanswer, (
                        subclue,
                        subanswer,
                    )
                    assert len(subclue) < 1024 and len(answer) < 128, (
                        subclue,
                        subanswer,
                    )
                    yield subclue, subanswer
                clue = final_line.strip()
            assert len(clue) < 1024 and len(answer) < 128, (clue, answer)
            yield clue, norm(answer)

    with get_db(in_context=False) as db:
        db.executescript(DB_SCHEMA)

        for csv_path in CROSSWORDQA_PATH.glob("*.csv"):
            with csv_path.open() as csv_file:
                db.executemany(
                    "INSERT INTO clues (clue, answer, cryptic) VALUES (?, ?, 0)",
                    cqa_iter(csv_file),
                )


def get_db(in_context: bool = True):
    connect = lambda: sqlite3.connect(DATABASE_PATH)
    if not in_context:
        return connect()

    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = connect()
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


@app.route("/")
def index():
    return """
<!doctype html>
<head>
<title>Dumpling!</title>
<style>
html, body, iframe { width: 100%; height: 100%; }
iframe { border: none; margin: 0; padding: 0; }
</style>
</head>
<body>
    <h1>Dumpling!</h1>
    <p>
        <input type="text" id="q">
        <button id="go">go</button>
    </p>
    <iframe id="results"></iframe>
    <script type="text/javascript">
    const q = document.querySelector("#q");
    const button = document.querySelector("#go");
    const results = document.querySelector("#results");

    var run = function() {
        console.log(q.value);
        results.setAttribute("src", "/q/" + encodeURIComponent(q.value));    
    }
    button.addEventListener("click", run);
    q.addEventListener("change", run);
    </script>
</body>
</html>
"""


@app.route("/q/<query>")
def search(query: str):
    cur = get_db().cursor()
    matches: DefaultDict[str, List[str]] = defaultdict(list)
    for clue, answer in cur.execute(
        "SELECT clue, answer FROM clues WHERE clue MATCH ? LIMIT 10000", (query,)
    ):
        matches[answer].append(clue)

    limit = int(request.args.get("limit", 1000))
    output = ""
    for answer, clues in sorted(matches.items(), key=lambda x: -len(x[1]))[:limit]:
        output += f"<tr><td>{len(clues)}</td><td>{answer}</td><td>({len(answer)})</td><td>{clues[0]}</td></tr>\n"
    if output:
        output = f"<table>\n{output}\n</table>\n"
    else:
        output = "no results :(\n"
    return output


if __name__ == "__main__":
    build_database()
