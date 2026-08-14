from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from grade import apply_step, grade_attempt

ROOT = Path(__file__).parent.resolve()
DATA_DIR = Path(os.environ.get("DATA_DIR", str(ROOT))).resolve()
CASES_PATH = ROOT / "cases.json"
DB_PATH = DATA_DIR / "trainer.db"
STATIC_NAMES = {
    "index.html",
    "app.js",
    "styles.css",
    "favicon.svg",
}

app = FastAPI(title="SMI Mechanic Trainer")
_CASES: dict[str, Any] | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


_CASES_MTIME = 0.0


def load_bank() -> dict[str, Any]:
    global _CASES, _CASES_MTIME
    mtime = CASES_PATH.stat().st_mtime
    if _CASES is None or mtime != _CASES_MTIME:
        _CASES = json.loads(CASES_PATH.read_text(encoding="utf-8"))
        _CASES_MTIME = mtime
    return _CASES


def public_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": case["id"],
        "title": case["title"],
        "cart": case["cart"],
        "setting": case["setting"],
        "ticket": case["ticket"],
    }


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS attempts (
                id TEXT PRIMARY KEY,
                trainee TEXT NOT NULL,
                case_id TEXT NOT NULL,
                steps_json TEXT NOT NULL,
                score INTEGER NOT NULL,
                result TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


@app.on_event("startup")
def startup() -> None:
    init_db()
    load_bank()


@app.get("/api/health")
def health() -> dict[str, Any]:
    bank = load_bank()
    return {
        "ok": True,
        "product": "SMI Mechanic Trainer",
        "cases": len(bank.get("cases") or []),
    }


@app.get("/api/cases")
def list_cases() -> dict[str, Any]:
    bank = load_bank()
    return {
        "product": bank.get("product") or "SMI Mechanic Trainer",
        "count": len(bank["cases"]),
        "cases": [public_case(item) for item in bank["cases"]],
    }


@app.get("/api/cases/{case_id}")
def get_case(case_id: str) -> dict[str, Any]:
    bank = load_bank()
    for item in bank["cases"]:
        if item["id"] == case_id:
            return public_case(item)
    raise HTTPException(status_code=404, detail="Case not found")


class ActIn(BaseModel):
    case_id: str
    step: str = Field(min_length=1, max_length=400)
    already: list[str] = Field(default_factory=list)


class GradeIn(BaseModel):
    trainee: str = Field(min_length=1, max_length=80)
    case_id: str
    steps: list[str] = Field(min_length=1)


@app.post("/api/act")
def act(body: ActIn) -> dict[str, Any]:
    bank = load_bank()
    case = next((item for item in bank["cases"] if item["id"] == body.case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    result = apply_step(case, body.step.strip(), body.already)
    cores = [item["id"] for item in case.get("checks") or [] if item.get("core")]
    result["needed"] = len(cores)
    result["found"] = len([item for item in cores if item in result["already"]])
    result["hint"] = case.get("hint") or ""
    if result.get("solved"):
        result["cause"] = case.get("cause") or ""
    return result


@app.post("/api/grade")
def grade(body: GradeIn) -> dict[str, Any]:
    bank = load_bank()
    case = next((item for item in bank["cases"] if item["id"] == body.case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    steps = [step.strip() for step in body.steps if step and step.strip()]
    if not steps:
        raise HTTPException(status_code=400, detail="Type at least one step")

    result = grade_attempt(case, steps)
    attempt_id = str(uuid.uuid4())
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """
            INSERT INTO attempts (id, trainee, case_id, steps_json, score, result, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                body.trainee.strip(),
                body.case_id,
                json.dumps(steps),
                result["score"],
                result["result"],
                utc_now(),
            ),
        )
    result["attempt_id"] = attempt_id
    result["trainee"] = body.trainee.strip()
    result["case_id"] = body.case_id
    result["title"] = case["title"]
    return result


@app.get("/api/attempts")
def attempts(trainee: str = "") -> dict[str, Any]:
    sql = "SELECT id, trainee, case_id, score, result, created_at FROM attempts"
    args: list[str] = []
    if trainee.strip():
        sql += " WHERE trainee = ?"
        args.append(trainee.strip())
    sql += " ORDER BY created_at DESC LIMIT 50"
    with sqlite3.connect(DB_PATH) as db:
        rows = db.execute(sql, args).fetchall()
    return {
        "attempts": [
            {
                "id": row[0],
                "trainee": row[1],
                "case_id": row[2],
                "score": row[3],
                "result": row[4],
                "created_at": row[5],
            }
            for row in rows
        ]
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "index.html")


@app.get("/{name}")
def static_file(name: str) -> FileResponse:
    if name not in STATIC_NAMES:
        raise HTTPException(status_code=404, detail="Not found")
    target = ROOT / name
    if not target.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(target)
