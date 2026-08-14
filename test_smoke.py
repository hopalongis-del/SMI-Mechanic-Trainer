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
        assert "tow-run-carryall" in ids

        ticket = client.get("/api/cases/tow-run-carryall")
        assert ticket.status_code == 200, ticket.text
        assert "cause" not in ticket.json()
        assert "Tow" not in ticket.json()["ticket"] or "tow/run" not in ticket.json()["ticket"].lower()

        good = client.post(
            "/api/grade",
            json={
                "trainee": "Smoke",
                "case_id": "tow-run-carryall",
                "steps": [
                    "chocked the wheels",
                    "key on, checked F/R in forward",
                    "checked tow/run, it was in tow",
                    "metered the pack, 36V",
                    "flipped it back to run and it drove",
                ],
            },
        )
        assert good.status_code == 200, good.text
        good_body = good.json()
        assert good_body["result"] == "pass", good_body
        assert good_body["score"] >= 70
        assert "Tow/run" in good_body["cause"]

        bad = client.post(
            "/api/grade",
            json={
                "trainee": "Smoke",
                "case_id": "tow-run-carryall",
                "steps": [
                    "replace the controller",
                    "order a new solenoid",
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
