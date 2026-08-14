import json

from fastapi.testclient import TestClient

import server


def main() -> None:
    bank = json.loads((server.ROOT / "cases.json").read_text(encoding="utf-8"))
    assert len(bank["cases"]) == 20
    for item in bank["cases"]:
        assert item["cart"]["fuel"] == "Gasoline"
        assert any(check.get("fix") for check in item["checks"])
        assert all("finding" in check for check in item["checks"])

    with TestClient(server.app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200, health.text
        assert health.json()["cases"] == 20

        ticket = client.get("/api/cases/no-start-after-unload")
        assert ticket.status_code == 200, ticket.text
        assert "cause" not in ticket.json()

        look = client.post(
            "/api/act",
            json={"case_id": "no-start-after-unload", "step": "check the gas", "already": []},
        )
        assert look.status_code == 200, look.text
        assert look.json()["kind"] in ("hit", "partial")
        assert "empty" in look.json()["reply"].lower()
        assert "part" in look.json()["reply"].lower()
        assert look.json()["solved"] is False

        already = look.json()["already"]
        fix = client.post(
            "/api/act",
            json={
                "case_id": "no-start-after-unload",
                "step": "fill it and turn the kill switch on",
                "already": already,
            },
        )
        assert fix.status_code == 200, fix.text
        assert fix.json()["solved"] is True

        pump = client.post(
            "/api/act",
            json={"case_id": "starts-then-dies", "step": "fuel pump", "already": []},
        )
        assert pump.status_code == 200, pump.text
        assert pump.json()["kind"] == "ok"
        assert "right area" in pump.json()["reply"].lower()
        assert "ten seconds" in pump.json()["reply"].lower()

        swap = client.post(
            "/api/act",
            json={"case_id": "starts-then-dies", "step": "change fuel pump", "already": []},
        )
        assert swap.status_code == 200, swap.text
        assert swap.json()["kind"] == "persist"
        assert "persists" in swap.json()["reply"].lower() or "still" in swap.json()["reply"].lower()

        part = client.post(
            "/api/act",
            json={"case_id": "starts-then-dies", "step": "fuel filter", "already": []},
        )
        assert part.status_code == 200, part.text
        assert part.json()["solved"] is False
        assert "filter" in part.json()["reply"].lower()

        foul = client.post(
            "/api/act",
            json={"case_id": "no-start-after-unload", "step": "replace the engine", "already": []},
        )
        assert foul.status_code == 200, foul.text
        assert foul.json()["kind"] == "persist"
        assert foul.json()["solved"] is False

        page = client.get("/")
        assert page.status_code == 200
        assert b"Check one thing" in page.content

    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
