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


def core_checks(case: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in (case.get("checks") or []) if item.get("core")]


def apply_step(
    case: dict[str, Any],
    step: str,
    already: list[str] | None = None,
) -> dict[str, Any]:
    already = list(already or [])
    blob = normalize(step)

    for rule in case.get("forbidden") or []:
        if any_alias(blob, rule.get("aliases") or []):
            return {
                "kind": "foul",
                "id": rule["id"],
                "reply": rule.get("label") or "That's the expensive wrong call.",
                "already": already,
                "solved": False,
            }

    matches = [
        check
        for check in (case.get("checks") or [])
        if check["id"] not in already and any_alias(blob, check.get("aliases") or [])
    ]
    if matches:
        check = next((item for item in matches if item.get("fix")), matches[0])
        already.append(check["id"])
        solved = _solved(case, already)
        return {
            "kind": "hit",
            "id": check["id"],
            "label": check["label"],
            "reply": check.get("finding") or check["label"],
            "core": bool(check.get("core")),
            "fix": bool(check.get("fix")),
            "already": already,
            "solved": solved,
        }

    return {
        "kind": "miss",
        "id": None,
        "reply": "Nothing useful from that. Try a real check — gas, spark, oil, belt, steering.",
        "already": already,
        "solved": False,
    }


def _solved(case: dict[str, Any], already: list[str]) -> bool:
    fixes = [item for item in (case.get("checks") or []) if item.get("fix")]
    if not fixes:
        needed = {item["id"] for item in core_checks(case)}
        return bool(needed) and needed.issubset(set(already))
    return any(item["id"] in already for item in fixes)


def grade_attempt(case: dict[str, Any], steps: list[str]) -> dict[str, Any]:
    already: list[str] = []
    log: list[dict[str, Any]] = []
    fouls = 0
    for step in steps:
        result = apply_step(case, step, already)
        already = result["already"]
        log.append(result)
        if result["kind"] == "foul":
            fouls += 1

    solved = _solved(case, already)
    cores = core_checks(case)
    hit_cores = [item for item in cores if item["id"] in already]
    result = "pass" if solved and fouls == 0 else ("almost" if solved else "fail")
    score = 100 if result == "pass" else (80 if result == "almost" else min(60, 20 * len(hit_cores)))

    if result == "pass":
        feedback = "That's it. You found it and you fixed it."
    elif result == "almost":
        feedback = "You got there, but you also called a bad part. Don't do that on the lot."
    else:
        feedback = "Not yet. You don't have to name every check — just find what's actually wrong and fix it."

    return {
        "score": score,
        "result": result,
        "solved": solved,
        "needed": len(cores),
        "found": len(hit_cores),
        "hits": [item for item in log if item["kind"] == "hit"],
        "fouls": [item for item in log if item["kind"] == "foul"],
        "cause": case.get("cause") or "",
        "feedback": feedback,
    }
