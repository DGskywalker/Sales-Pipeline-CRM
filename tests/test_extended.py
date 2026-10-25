import random

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app import seed as seed_mod
from app.models import STAGES, Activity, Contact, Deal


def _deal(client, cid, **kw):
    return client.post("/api/deals", json={"contact_id": cid, "title": "Deal", **kw}).json()


def test_deal_detail_includes_contact_fields(client, contact):
    d = _deal(client, contact["id"], value=500)
    r = client.get(f"/api/deals/{d['id']}").json()
    assert r["contact_name"] == "Aisha Khan" and r["company"] == "Acme"
    assert client.get("/api/deals/999").status_code == 404


def test_deal_search_matches_title_and_company(client, contact):
    _deal(client, contact["id"], title="Analytics add-on")
    assert len(client.get("/api/deals", params={"q": "analytics"}).json()) == 1
    assert len(client.get("/api/deals", params={"q": "acme"}).json()) == 1
    assert client.get("/api/deals", params={"q": "nomatch"}).json() == []


def test_contact_list_total_count_header_and_pagination(client):
    for i in range(5):
        client.post("/api/contacts", json={"name": f"P{i}", "email": f"p{i}@x.com"})
    r = client.get("/api/contacts", params={"limit": 2, "offset": 2})
    assert r.headers["x-total-count"] == "5" and len(r.json()) == 2
    assert client.get("/api/contacts", params={"q": "p1"}).headers["x-total-count"] == "1"


def test_contact_deals(client, contact):
    _deal(client, contact["id"])
    _deal(client, contact["id"])
    assert len(client.get(f"/api/contacts/{contact['id']}/deals").json()) == 2
    assert client.get("/api/contacts/999/deals").status_code == 404


def test_owner_leaderboard(client, contact):
    cid = contact["id"]
    _deal(client, cid, value=100, owner="sam", stage="Won")
    _deal(client, cid, value=50, owner="sam", stage="Lost")
    _deal(client, cid, value=70, owner="sam")
    _deal(client, cid, value=900, owner="lee", stage="Proposal")
    _deal(client, cid, value=1)  # no owner -> excluded
    rows = client.get("/api/reports/owners").json()
    assert [r["owner"] for r in rows] == ["sam", "lee"]
    sam = rows[0]
    assert sam["won_value"] == 100 and sam["open_value"] == 70 and sam["open_deals"] == 1 and sam["win_rate"] == 0.5
    assert rows[1]["win_rate"] is None


def test_activity_feed(client, contact):
    d = _deal(client, contact["id"], title="Pilot")
    client.post(f"/api/deals/{d['id']}/activities", json={"type": "call", "note": "hello"})
    client.patch(f"/api/deals/{d['id']}", json={"stage": "Contacted"})
    feed = client.get("/api/reports/activity", params={"limit": 5}).json()
    assert len(feed) == 2 and feed[0]["type"] == "stage_change"
    assert feed[0]["deal_title"] == "Pilot" and feed[0]["company"] == "Acme"


def test_seed_populates_consistent_data(monkeypatch):
    engine = create_engine("sqlite://")
    monkeypatch.setattr(seed_mod, "engine", engine)
    monkeypatch.setattr(seed_mod, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))
    out = seed_mod.seed(12, rng=random.Random(1))
    assert out == {"contacts": 12, "deals": sum(seed_mod.STAGE_MIX.values())}
    assert seed_mod.seed(12) == {"skipped": True}
    with seed_mod.SessionLocal() as db:
        assert db.scalar(select(func.count(Contact.id))) == 12
        for d in db.scalars(select(Deal)):
            last = db.scalars(select(Activity).where(Activity.deal_id == d.id, Activity.type == "stage_change")
                              .order_by(Activity.created_at.desc(), Activity.id.desc())).first()
            assert d.stage in STAGES
            assert (last is None and d.stage == "Lead") or last.note.endswith(d.stage)
    assert seed_mod.seed(5, reset=True)["contacts"] == 5
