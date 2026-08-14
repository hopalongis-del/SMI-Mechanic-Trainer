import json

from fastapi.testclient import TestClient

import server


def main() -> None:
    bank = json.loads((server.ROOT / "cases.json").read_text(encoding="utf-8"))
    assert len(bank["cases"]) == 10
    for item in bank["cases"]:
        assert item["cart"]["fuel"] == "Gasoline"
        assert any(check.get("fix") for check in item["checks"])
        assert all("finding" in check for check in item["checks"])

    with TestClient(server.app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200, health.text
        assert health.json()["cases"] == 10

        ticket = client.get("/api/cases/no-start-after-unload")
        assert ticket.status_code == 200, ticket.text
        assert "cause" not in ticket.json()

        look = client.post(
            "/api/act",
            json={"case_id": "no-start-after-unload", "step": "check the gas", "already": []},
        )
        assert look.status_code == 200, look.text
        assert look.json()["kind"] == "hit"
        assert "empty" in look.json()["reply"].lower()
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

        foul = client.post(
            "/api/act",
            json={"case_id": "no-start-after-unload", "step": "replace the engine", "already": []},
        )
        assert foul.status_code == 200, foul.text
        assert foul.json()["kind"] == "foul"
        assert foul.json()["solved"] is False

        page = client.get("/")
        assert page.status_code == 200
        assert b"Check one thing" in page.content

    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
