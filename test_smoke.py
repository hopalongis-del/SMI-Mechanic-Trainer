import json

from fastapi.testclient import TestClient

import server


def main() -> None:
    with TestClient(server.app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200, health.text
        body = health.json()
        assert body["ok"] is True
        assert body["cases"] == 10
        assert body["product"] == "SMI Mechanic Trainer"

        listing = client.get("/api/cases")
        assert listing.status_code == 200, listing.text
        cases = listing.json()["cases"]
        assert len(cases) == 10
        assert "cause" not in cases[0]
        ids = {item["id"] for item in cases}
        assert "no-start-after-unload" in ids
        assert all("36V" not in json.dumps(item.get("cart") or {}) for item in cases)

        ticket = client.get("/api/cases/no-start-after-unload")
        assert ticket.status_code == 200, ticket.text
        assert "cause" not in ticket.json()
        assert ticket.json()["cart"]["fuel"] == "Gasoline"

        good = client.post(
            "/api/grade",
            json={
                "trainee": "Smoke",
                "case_id": "no-start-after-unload",
                "steps": [
                    "chocked the wheels",
                    "key on, pedal in forward",
                    "checked the kill switch",
                    "tank was empty so I put gas in it",
                    "switch on, filled it, it started, test drive",
                ],
            },
        )
        assert good.status_code == 200, good.text
        good_body = good.json()
        assert good_body["result"] == "pass", good_body
        assert good_body["score"] >= 70
        assert "gas" in good_body["cause"].lower()

        bad = client.post(
            "/api/grade",
            json={
                "trainee": "Smoke",
                "case_id": "no-start-after-unload",
                "steps": [
                    "replace the engine",
                    "new carburetor",
                    "meter the pack 36 volt",
                ],
            },
        )
        assert bad.status_code == 200, bad.text
        assert bad.json()["result"] == "fail"
        assert bad.json()["score"] < 70

        page = client.get("/")
        assert page.status_code == 200
        assert b"SMI Mechanic Trainer" in page.content

    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
