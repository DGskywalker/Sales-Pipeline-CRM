def test_health_and_dashboard(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert "Sales Pipeline CRM" in client.get("/").text


def test_create_contact_normalizes_email_and_rejects_duplicates(client, contact):
    assert contact["email"] == "aisha@acme.com"
    r = client.post("/api/contacts", json={"name": "Dup", "email": "aisha@acme.com"})
    assert r.status_code == 409


def test_contact_validation(client):
    assert client.post("/api/contacts", json={"name": "X", "email": "not-an-email"}).status_code == 422
    assert client.post("/api/contacts", json={"name": "", "email": "a@b.co"}).status_code == 422


def test_contact_search_update_delete(client, contact):
    assert len(client.get("/api/contacts", params={"q": "acme"}).json()) == 1
    assert client.get("/api/contacts", params={"q": "zzz"}).json() == []
    r = client.patch(f"/api/contacts/{contact['id']}", json={"phone": "+97150"})
    assert r.json()["phone"] == "+97150"
    assert client.delete(f"/api/contacts/{contact['id']}").status_code == 204
    assert client.get(f"/api/contacts/{contact['id']}").status_code == 404


def test_csv_import_handles_duplicates_and_bad_rows(client, contact):
    csv_body = ("name,email,company\nBob,bob@x.com,X\nAisha,aisha@acme.com,Acme\n"
                "Bad,not-email,Z\nCara,cara@y.com,Y\n")
    r = client.post("/api/contacts/import", content=csv_body, headers={"Content-Type": "text/csv"})
    body = r.json()
    assert body["created"] == 2 and body["skipped_duplicates"] == 1 and len(body["errors"]) == 1
    assert client.post("/api/contacts/import", content="foo,bar\n1,2").status_code == 400


def test_deal_lifecycle_and_stage_audit_trail(client, contact):
    d = client.post("/api/deals", json={"contact_id": contact["id"], "title": "Pilot", "value": 10000}).json()
    assert d["stage"] == "Lead"
    client.patch(f"/api/deals/{d['id']}", json={"stage": "Qualified"})
    acts = client.get(f"/api/deals/{d['id']}/activities").json()
    assert acts[0]["type"] == "stage_change" and acts[0]["note"] == "Lead -> Qualified"
    r = client.post(f"/api/deals/{d['id']}/activities", json={"type": "call", "note": "Intro call"})
    assert r.status_code == 201


def test_deal_validation(client, contact):
    assert client.post("/api/deals", json={"contact_id": 999, "title": "x"}).status_code == 404
    assert client.post("/api/deals", json={"contact_id": contact["id"], "title": "x", "stage": "Nope"}).status_code == 422
    assert client.post("/api/deals", json={"contact_id": contact["id"], "title": "x", "value": -5}).status_code == 422
    assert client.get("/api/deals", params={"stage": "Nope"}).status_code == 422
    assert client.patch("/api/deals/999", json={"title": "y"}).status_code == 404


def test_filter_deals_by_stage_and_owner(client, contact):
    cid = contact["id"]
    client.post("/api/deals", json={"contact_id": cid, "title": "A", "value": 1, "owner": "sam"})
    client.post("/api/deals", json={"contact_id": cid, "title": "B", "value": 2, "stage": "Won", "owner": "lee"})
    assert len(client.get("/api/deals", params={"stage": "Won"}).json()) == 1
    assert len(client.get("/api/deals", params={"owner": "sam"}).json()) == 1


def test_summary_report_math(client, contact):
    cid = contact["id"]
    for title, value, stage in [("A", 1000, "Lead"), ("B", 2000, "Proposal"), ("C", 5000, "Won"), ("D", 700, "Lost")]:
        client.post("/api/deals", json={"contact_id": cid, "title": title, "value": value, "stage": stage})
    s = client.get("/api/reports/summary").json()
    assert s["open_pipeline_value"] == 3000
    assert s["weighted_forecast"] == 1000 * 0.1 + 2000 * 0.6
    assert s["won_value"] == 5000 and s["win_rate"] == 0.5 and s["total_contacts"] == 1


def test_summary_empty_has_null_win_rate(client):
    assert client.get("/api/reports/summary").json()["win_rate"] is None


def test_csv_export(client, contact):
    client.post("/api/deals", json={"contact_id": contact["id"], "title": "Pilot", "value": 1})
    r = client.get("/api/reports/deals.csv")
    assert r.headers["content-type"].startswith("text/csv") and "Pilot" in r.text


def test_cascade_delete_removes_deals(client, contact):
    client.post("/api/deals", json={"contact_id": contact["id"], "title": "Pilot"})
    client.delete(f"/api/contacts/{contact['id']}")
    assert client.get("/api/deals").json() == []
