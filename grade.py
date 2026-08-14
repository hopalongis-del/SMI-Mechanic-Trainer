from __future__ import annotations

import re
from typing import Any

REPLACE_WORDS = (
    "replace",
    "replaced",
    "change",
    "changed",
    "swap",
    "swapped",
    "install",
    "installed",
    "rebuild",
    "rebuilt",
    "new",
)
CHECK_WORDS = (
    "check",
    "checked",
    "test",
    "tested",
    "inspect",
    "inspected",
    "look",
    "looked",
    "pull",
    "pulled",
    "meter",
    "read",
    "verify",
)
KNOWN_PARTS = (
    "fuel pump",
    "pump",
    "fuel pickup",
    "pick up",
    "pickup",
    "carb",
    "carburetor",
    "injector",
    "spark plug",
    "plug",
    "coil",
    "ignition",
    "battery",
    "cables",
    "starter",
    "isg",
    "solenoid",
    "controller",
    "belt",
    "clutch",
    "clutches",
    "oil",
    "oil filter",
    "fuel filter",
    "filter",
    "air filter",
    "kill switch",
    "fuel cap",
    "vent",
    "tie rod",
    "steering",
    "engine",
    "motor",
    "muffler",
    "exhaust",
    "cvt",
    "screen",
    "fins",
    "gas",
    "fuel",
    "tank",
)

CHECKS_GOOD = "Checks good."
STILL_BROKEN = "You replaced it. Same problem. Cart is still doing the same thing."

PART_SYSTEMS = {
    "fuel pump": "fuel",
    "pump": "fuel",
    "fuel pickup": "fuel",
    "pick up": "fuel",
    "pickup": "fuel",
    "carb": "fuel",
    "carburetor": "fuel",
    "injector": "fuel",
    "fuel filter": "fuel",
    "fuel cap": "fuel",
    "vent": "fuel",
    "gas": "fuel",
    "fuel": "fuel",
    "tank": "fuel",
    "spark plug": "spark",
    "plug": "spark",
    "coil": "spark",
    "ignition": "spark",
    "kill switch": "electrical",
    "battery": "electrical",
    "cables": "electrical",
    "starter": "electrical",
    "isg": "electrical",
    "solenoid": "electrical",
    "controller": "electrical",
    "oil": "oil",
    "oil filter": "oil",
    "belt": "belt",
    "clutch": "belt",
    "clutches": "belt",
    "cvt": "cooling",
    "screen": "cooling",
    "fins": "cooling",
    "air filter": "cooling",
    "tie rod": "steering",
    "steering": "steering",
    "engine": "engine",
    "motor": "engine",
    "muffler": "exhaust",
    "exhaust": "exhaust",
}


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


def is_replace(blob: str) -> bool:
    tokens = set(blob.split())
    return bool(tokens & set(REPLACE_WORDS))


def is_doing_work(blob: str) -> bool:
    tokens = set(blob.split())
    return is_replace(blob) or bool(
        tokens & {"fill", "filled", "add", "added", "clean", "cleaned", "tighten", "tightened"}
    )


def is_check(blob: str) -> bool:
    tokens = set(blob.split())
    if any(word in tokens for word in CHECK_WORDS):
        return True
    return any(contains_alias(blob, part) for part in KNOWN_PARTS)


def core_checks(case: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in (case.get("checks") or []) if item.get("core")]


def problem_systems(case: dict[str, Any]) -> set[str]:
    return {
        item.get("system")
        for item in (case.get("checks") or [])
        if item.get("system") and (item.get("core") or item.get("fix"))
    }


def step_systems(blob: str) -> set[str]:
    found: set[str] = set()
    for part, system in PART_SYSTEMS.items():
        if contains_alias(blob, part):
            found.add(system)
    return found


def still_text(case: dict[str, Any]) -> str:
    return case.get("still") or "Cart is still doing the same thing."


def hit_reply(case: dict[str, Any], check: dict[str, Any], already: list[str], solved: bool) -> str:
    reply = check.get("finding") or check["label"]
    if solved:
        return reply
    extra = check.get("after")
    if extra:
        return f"{reply} {extra}"
    leftover = [item for item in core_checks(case) if item["id"] not in already]
    if leftover and check.get("core"):
        return f"{reply} That's only part of the issue."
    return reply


def close_reply(case: dict[str, Any], replacing: bool) -> str:
    leftover = still_text(case)
    if replacing:
        return f"You replaced that. Problem persists. {leftover} You're in the right area though."
    return f"Checks good. You're in the right area though. {leftover}"


def apply_step(
    case: dict[str, Any],
    step: str,
    already: list[str] | None = None,
) -> dict[str, Any]:
    already = list(already or [])
    blob = normalize(step)
    replacing = is_replace(blob)
    doing_work = is_doing_work(blob)

    matches = [
        check
        for check in (case.get("checks") or [])
        if check["id"] not in already and any_alias(blob, check.get("aliases") or [])
    ]
    if matches:
        if doing_work:
            check = next((item for item in matches if item.get("fix")), None)
            if check is None and replacing:
                return {
                    "kind": "persist",
                    "id": None,
                    "reply": STILL_BROKEN,
                    "already": already,
                    "solved": False,
                }
            if check is None:
                check = matches[0]
        else:
            check = next((item for item in matches if not item.get("fix")), matches[0])
        already.append(check["id"])
        solved = _solved(case, already)
        kind = "hit" if solved or check.get("fix") else "partial"
        if not check.get("fix") and not solved:
            kind = "partial"
        return {
            "kind": kind,
            "id": check["id"],
            "label": check["label"],
            "reply": hit_reply(case, check, already, solved),
            "core": bool(check.get("core")),
            "fix": bool(check.get("fix")),
            "already": already,
            "solved": solved,
            "score": _progress(case, already),
        }

    close = bool(step_systems(blob) & problem_systems(case))
    if replacing:
        return {
            "kind": "persist",
            "id": None,
            "reply": close_reply(case, True) if close else STILL_BROKEN,
            "already": already,
            "solved": False,
            "score": _progress(case, already),
        }

    if is_check(blob):
        return {
            "kind": "ok",
            "id": None,
            "reply": close_reply(case, False) if close else CHECKS_GOOD,
            "already": already,
            "solved": False,
            "score": _progress(case, already),
        }

    return {
        "kind": "miss",
        "id": None,
        "reply": "Say what you're checking or what you're replacing.",
        "already": already,
        "solved": False,
        "score": _progress(case, already),
    }


def _progress(case: dict[str, Any], already: list[str]) -> int:
    cores = core_checks(case)
    if not cores:
        return 0
    found = len([item for item in cores if item["id"] in already])
    return min(100, round(100 * found / len(cores)))


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
        if result["kind"] in ("foul", "persist"):
            fouls += 1

    solved = _solved(case, already)
    cores = core_checks(case)
    hit_cores = [item for item in cores if item["id"] in already]
    result = "pass" if solved and fouls == 0 else ("almost" if solved else "fail")
    score = 100 if result == "pass" else (80 if result == "almost" else min(60, 20 * len(hit_cores)))

    if result == "pass":
        feedback = "That's it. You found it and you fixed it."
    elif result == "almost":
        feedback = "You got there, but you also threw a good part."
    else:
        feedback = "Not yet. Check until you find the bad one, then replace that."

    return {
        "score": score,
        "result": result,
        "solved": solved,
        "needed": len(cores),
        "found": len(hit_cores),
        "hits": [item for item in log if item["kind"] == "hit"],
        "fouls": [item for item in log if item["kind"] in ("foul", "persist")],
        "cause": case.get("cause") or "",
        "feedback": feedback,
    }
