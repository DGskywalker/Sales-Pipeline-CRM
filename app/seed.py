"""Populate the database with realistic demo data.

Usage: python -m app.seed [--reset] [--contacts N]
"""
import argparse
import random
from datetime import timedelta

from sqlalchemy import func, select

from app import models  # noqa: F401  (registers tables)
from app.db import Base, SessionLocal, engine
from app.models import STAGES, Activity, Contact, Deal, now

FIRST = ["Aisha", "Omar", "Priya", "Liam", "Sofia", "Kenji", "Elena", "Marcus", "Fatima", "Noah", "Chloe", "Ravi",
         "Hannah", "Diego", "Mei", "Lucas", "Zara", "Ethan", "Ines", "Yusuf", "Grace", "Mateo", "Leila", "Owen"]
LAST = ["Khan", "Patel", "Nguyen", "Schmidt", "Rossi", "Tanaka", "Garcia", "Okafor", "Silva", "Brown", "Haddad",
        "Kowalski", "Murphy", "Ivanova", "Chen", "Dubois", "Larsen", "Mendes", "Ali", "Fischer"]
COMPANIES = ["Acme Corp", "Globex", "Initech", "Umbrella Health", "Stark Logistics", "Wayne Fintech", "Hooli",
             "Vandelay Imports", "Soylent Foods", "Cyberdyne", "Tyrell Systems", "Wonka Retail", "Pied Piper",
             "Massive Dynamic", "Oscorp Energy", "Nakatomi Trading", "Gringotts Capital", "Aperture Labs"]
SOURCES = ["website", "referral", "linkedin", "conference", "cold_outreach", "csv_import", "webinar"]
PRODUCTS = ["Platform license", "Pilot", "Enterprise renewal", "Analytics add-on", "Onboarding package",
            "Annual subscription", "Data migration", "Support upgrade", "Multi-region expansion", "API tier"]
OWNERS = ["sam", "lee", "maria", "dev", "jordan"]
NOTES = {
    "call": ["Discovery call, strong interest", "Follow-up call re: pricing", "Left voicemail", "Call with CTO"],
    "email": ["Sent proposal deck", "Shared case study", "Sent pricing sheet", "Intro email sent"],
    "meeting": ["On-site demo", "Procurement review", "Exec sponsor meeting", "Technical deep-dive"],
    "note": ["Budget confirmed for Q1", "Competitor evaluation in progress", "Champion is VP Sales", "Needs SSO"],
}
STAGE_MIX = {"Lead": 18, "Contacted": 16, "Qualified": 14, "Proposal": 10, "Won": 12, "Lost": 7}


def seed(n_contacts: int = 48, reset: bool = False, rng: random.Random | None = None) -> dict:
    rng = rng or random.Random(42)
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not reset and db.scalar(select(func.count(Contact.id))):
            return {"skipped": True}
        t0 = now()
        contacts, used = [], set()
        while len(contacts) < n_contacts:
            first, last, company = rng.choice(FIRST), rng.choice(LAST), rng.choice(COMPANIES)
            email = f"{first}.{last}@{company.split()[0]}.com".lower()
            if email in used:
                continue
            used.add(email)
            contacts.append(Contact(name=f"{first} {last}", email=email, company=company,
                                    phone=f"+1 555 {rng.randint(100, 999)} {rng.randint(1000, 9999)}",
                                    source=rng.choice(SOURCES), created_at=t0 - timedelta(days=rng.randint(5, 180))))
        db.add_all(contacts)
        db.flush()

        deals = 0
        stages = [s for s, w in STAGE_MIX.items() for _ in range(w)]
        for stage in stages:
            c = rng.choice(contacts)
            # Walk the deal through the pipeline up to its current stage, logging touches along the way.
            path = STAGES[: STAGES.index(stage) + 1] if stage != "Lost" else STAGES[: rng.randint(2, 4)] + ["Lost"]
            events, t = [], timedelta()
            for prev, nxt in zip(path, path[1:]):
                for _ in range(rng.randint(1, 2)):
                    t += timedelta(hours=rng.randint(6, 96))
                    kind = rng.choice(list(NOTES))
                    events.append((t, kind, rng.choice(NOTES[kind])))
                t += timedelta(hours=rng.randint(2, 48))
                events.append((t, "stage_change", f"{prev} -> {nxt}"))
            # Start after the contact was added, but shift back so the last touch lands in the past.
            created = c.created_at + timedelta(days=rng.randint(0, 4))
            latest = t0 - timedelta(minutes=rng.randint(20, 60 * 24 * 10))
            created = min(created, latest - t)
            d = Deal(contact_id=c.id, title=f"{c.company} — {rng.choice(PRODUCTS)}", stage=stage,
                     value=float(rng.choice([2, 3, 5, 8, 12, 18, 25, 40, 60]) * 1000 + rng.randint(0, 9) * 100),
                     owner=rng.choice(OWNERS), created_at=created, updated_at=created + t)
            db.add(d)
            db.flush()
            db.add_all(Activity(deal_id=d.id, type=k, note=n, created_at=created + off) for off, k, n in events)
            deals += 1
        db.commit()
        return {"contacts": len(contacts), "deals": deals}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reset", action="store_true", help="drop and recreate all tables first")
    ap.add_argument("--contacts", type=int, default=48)
    args = ap.parse_args()
    print(seed(args.contacts, args.reset))


if __name__ == "__main__":
    main()
