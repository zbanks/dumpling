#!/usr/bin/env python3.7

import csv
import os
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import (IO, Any, Callable, DefaultDict, Dict, Iterator, List,
                    Optional, Tuple, TypeVar, Union)

from flask import Flask, Response, g, request, send_file
from flask.json import jsonify

DUMPLING_DB_PATH = Path(os.environ.get("DUMPLING_DB_PATH", "dumpling.db"))
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


def get_db(in_context: bool = True) -> sqlite3.Connection:
    if not in_context:
        return sqlite3.connect(DUMPLING_DB_PATH)

    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DUMPLING_DB_PATH)
    return db


@dataclass(order=True)
class Answer:
    score: float
    answer: str
    clues: List[str]


class SearchSyntaxError(Exception):
    def __str__(self) -> str:
        return f'Search syntax error: "{self.args[0]}"'


def search(query: str, limit: int, in_context: bool = True) -> List[Answer]:
    cur = get_db(in_context=in_context).cursor()
    try:
        entries = cur.execute(
            "SELECT clue, answer, -rank FROM clues WHERE clue MATCH ? ORDER BY rank LIMIT 50000",
            (query,),
        )
    except sqlite3.OperationalError as ex:
        if "syntax error" in ex.args[0]:
            raise SearchSyntaxError(query)
        raise

    matches: DefaultDict[str, List[Tuple[str, float]]] = defaultdict(list)
    for clue, answer, score in entries:
        matches[answer].append((clue, score))

    result: List[Answer] = []
    for answer, clues_and_scores in matches.items():
        scores = [s for c, s in clues_and_scores]
        score = max(scores) * (len(scores) ** 0.5) * 0.95 + sum(scores) * 0.05
        result.append(
            Answer(score=score, answer=answer, clues=[c for c, s in clues_and_scores])
        )

    result.sort(reverse=True)
    return result[:limit]


T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])
FuncResponse = TypeVar("FuncResponse", bound=Callable[..., Response])


def wrap_return(fn: Callable[[T], Response]) -> Callable[[F], FuncResponse]:
    def _decorator(f: F) -> FuncResponse:
        @wraps(f)
        def _wrap(*args: Any, **kwargs: Any) -> Response:
            result: T = f(*args, **kwargs)
            return fn(result)

        return _wrap  # type: ignore

    return _decorator


def textify(text: str) -> Response:
    return Response(text, content_type="text/plain")


@app.teardown_appcontext
def close_connection(exception: Optional[Exception]) -> None:
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


@app.route("/")
def index() -> Response:
    return send_file("static/index.html")


@app.route("/favicon.ico")
def favicon() -> Response:
    return send_file("static/favicon.ico")


@app.route("/json/<query>")
@wrap_return(jsonify)
def json_search(query: str) -> Dict[str, Union[List[Answer], str]]:
    limit = int(request.args.get("limit", 1000))

    try:
        results = search(query, limit)
    except SearchSyntaxError as ex:
        return {"error": str(ex)}
    if not results:
        return {"error": "no results :("}

    return {"results": results}


@app.route("/text/<query>")
@wrap_return(textify)
def text_search(query: str) -> str:
    limit = int(request.args.get("limit", 1000))

    try:
        results = search(query, limit)
    except SearchSyntaxError as ex:
        return str(ex)
    if not results:
        return "no results :("
    return "".join(f"{a.answer}\n" for a in results)


@app.route("/html/<query>")
def html_search(query: str) -> str:
    limit = int(request.args.get("limit", 1000))

    try:
        results = search(query, limit)
    except SearchSyntaxError as ex:
        return str(ex)
    if not results:
        return "no results :("

    rows = []
    for a in results:
        rows.append(
            f"""<tr>
            <td>{len(a.clues)}: {a.score:0.2f}</td>
            <td>{a.answer}</td>
            <td>({len(a.answer)})</td>
            <td>{a.clues[0]}</td>
        </tr>"""
        )
    return f"<table>{''.join(rows)}</table>"


if __name__ == "__main__":
    build_database()
