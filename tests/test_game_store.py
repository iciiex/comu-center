from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.config import Settings
from tests.conftest import VISITOR, login


def csrf_header(client: TestClient) -> dict[str, str]:
    bootstrap = client.get("/api/v1/game/bootstrap")
    assert bootstrap.status_code == 200
    return {"X-CSRF-Token": bootstrap.json()["csrf_token"]}


def set_game_coins(settings: Settings, user_mobile: str, coins: int) -> None:
    import sqlite3

    conn = sqlite3.connect(settings.db_path)
    try:
        user_id, state = conn.execute(
            """SELECT u.id, gp.state_json FROM users u
               JOIN game_progress gp ON gp.user_id = u.id WHERE u.mobile = ?""",
            (user_mobile,),
        ).fetchone()
        progress = json.loads(state)
        progress["coins"] = coins
        conn.execute(
            "UPDATE game_progress SET state_json = ? WHERE user_id = ?",
            (json.dumps(progress), user_id),
        )
        conn.commit()
    finally:
        conn.close()


def test_demo_store_purchase_is_atomic_idempotent_and_unlocks_special_mission(
    client: TestClient, settings: Settings
) -> None:
    login(client, settings, VISITOR)
    csrf = csrf_header(client)
    set_game_coins(settings, VISITOR, 100)

    store = client.get("/api/v1/game/store")
    assert store.status_code == 200
    assert store.json()["is_demo"] is True
    assert store.json()["currency"] == "game_coins"
    assert store.json()["coin_balance"] == 100
    assert len(store.json()["offers"]) == 2
    offer_id = store.json()["offers"][0]["id"]

    purchase = client.post(
        "/api/v1/game/store/purchases",
        json={"offer_id": offer_id},
        headers={**csrf, "Idempotency-Key": "store-purchase-1"},
    )
    assert purchase.status_code == 200, purchase.text
    assert purchase.json()["coin_balance"] == 60
    assert purchase.json()["mission_id"] == "market-insight-special"
    assert purchase.json()["replayed"] is False

    replay = client.post(
        "/api/v1/game/store/purchases",
        json={"offer_id": offer_id},
        headers={**csrf, "Idempotency-Key": "store-purchase-1"},
    )
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert replay.json()["coin_balance"] == 60

    changed = client.post(
        "/api/v1/game/store/purchases",
        json={"offer_id": "special-sales-strategy"},
        headers={**csrf, "Idempotency-Key": "store-purchase-1"},
    )
    assert changed.status_code == 409
    assert changed.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"

    progress = client.get("/api/v1/game/progress").json()
    special = next(m for m in progress["special_missions"] if m["id"] == "market-insight-special")
    assert special["status"] == "available"
    assert special["storePriceCoins"] == 40

    store_after = client.get("/api/v1/game/store").json()
    assert store_after["coin_balance"] == 60
    assert store_after["offers"][0]["purchased"] is True

    special_completion = client.post(
        "/api/v1/game/missions/market-insight-special/completions",
        json={"answers": {"topic": "customer_needs", "finding": "opportunity", "rating": 4}},
        headers={**csrf, "Idempotency-Key": "special-mission-completion"},
    )
    assert special_completion.status_code == 200, special_completion.text
    assert special_completion.json()["entry"]["missionId"] == "market-insight-special"
    assert special_completion.json()["entry"]["coinsAfter"] == 80

    import sqlite3

    with sqlite3.connect(settings.db_path) as conn:
        assert conn.execute(
            """SELECT COUNT(*) FROM game_coin_transactions
               WHERE user_id = (SELECT id FROM users WHERE mobile = ?)""",
            (VISITOR,),
        ).fetchone()[0] == 1


def test_demo_store_rejects_insufficient_balance_and_missing_csrf(
    client: TestClient, settings: Settings
) -> None:
    login(client, settings, VISITOR)
    csrf = csrf_header(client)
    set_game_coins(settings, VISITOR, 10)
    no_csrf = client.post(
        "/api/v1/game/store/purchases",
        json={"offer_id": "special-market-insight"},
        headers={"Idempotency-Key": "no-csrf"},
    )
    assert no_csrf.status_code == 403

    response = client.post(
        "/api/v1/game/store/purchases",
        json={"offer_id": "special-market-insight"},
        headers={**csrf, "Idempotency-Key": "insufficient"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSUFFICIENT_GAME_COINS"
