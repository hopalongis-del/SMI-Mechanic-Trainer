from __future__ import annotations

import re
from typing import Any


def normalize(text: str) -> str:
    text = (text or "").lower().replace("/", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def contains_alias(blob: str, alias: str) -> bool:
    needle = normalize(alias)
    if not needle:
        return False
    if needle in blob:
        return True
    words = needle.split()
    if len(words) >= 2:
        return all(word in blob.split() for word in words)
    return False


def any_alias(blob: str, aliases: list[str]) -> bool:
    return any(contains_alias(blob, alias) for alias in aliases)


def grade_attempt(case: dict[str, Any], steps: list[str]) -> dict[str, Any]:
    blob = normalize("\n".join(steps))
    checks = case.get("checks") or []
    forbidden = case.get("forbidden") or []

    earned = 0
    possible = 0
    hits: list[dict[str, Any]] = []
    misses: list[dict[str, Any]] = []

    for check in checks:
        pts = int(check.get("points") or 0)
        possible += pts
        if any_alias(blob, check.get("aliases") or []):
            earned += pts
            hits.append(
                {
                    "id": check["id"],
                    "label": check["label"],
                    "category": check.get("category") or "diagnosis",
                    "points": pts,
                }
            )
        else:
            misses.append(
                {
                    "id": check["id"],
                    "label": check["label"],
                    "category": check.get("category") or "diagnosis",
                    "points": pts,
                }
            )

    penalties = 0
    fouls: list[dict[str, Any]] = []
    for rule in forbidden:
        if any_alias(blob, rule.get("aliases") or []):
            pen = int(rule.get("penalty") or 0)
            penalties += pen
            fouls.append(
                {
                    "id": rule["id"],
                    "label": rule["label"],
                    "penalty": pen,
                }
            )

    score = max(0, min(100, round((earned - penalties) / possible * 100))) if possible else 0
    pass_score = int(case.get("pass_score") or 70)
    safety_missed = [item for item in misses if item["category"] == "safety"]
    result = "pass" if score >= pass_score and not safety_missed else "fail"
    if score >= pass_score and safety_missed:
        result = "almost"

    return {
        "score": score,
        "result": result,
        "pass_score": pass_score,
        "earned": earned,
        "possible": possible,
        "penalties": penalties,
        "hits": hits,
        "misses": misses,
        "fouls": fouls,
        "cause": case.get("cause") or "",
        "feedback": _feedback(result, hits, misses, fouls, safety_missed),
    }


def _feedback(
    result: str,
    hits: list[dict[str, Any]],
    misses: list[dict[str, Any]],
    fouls: list[dict[str, Any]],
    safety_missed: list[dict[str, Any]],
) -> str:
    if result == "pass":
        lead = "That's a pass. You chased the cart, not the parts cannon."
    elif result == "almost":
        lead = "Score was there, but you skipped a safety step. That's a fail on the lot."
    else:
        lead = "Not a pass. You either skipped the cheap checks or jumped to a part."

    bits = [lead]
    if fouls:
        bits.append("Don't " + fouls[0]["label"].lower() + ".")
    if safety_missed:
        bits.append("Safety miss: " + safety_missed[0]["label"] + ".")
    elif misses:
        bits.append("Biggest miss: " + misses[0]["label"] + ".")
    if hits:
        bits.append("You did get: " + hits[0]["label"].lower() + ".")
    return " ".join(bits)
