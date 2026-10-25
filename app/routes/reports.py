import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import STAGE_WEIGHTS, STAGES, Activity, Contact, Deal
from app.schemas import FeedItem, OwnerStats

router = APIRouter(tags=["reports"])


@router.get("/reports/summary")
def summary(db: Session = Depends(get_db)):
    rows = db.execute(select(Deal.stage, func.count(Deal.id), func.coalesce(func.sum(Deal.value), 0.0))
                      .group_by(Deal.stage)).all()
    by = {s: {"stage": s, "count": 0, "total_value": 0.0} for s in STAGES}
    for stage, count, total in rows:
        by[stage] = {"stage": stage, "count": count, "total_value": float(total)}
    stages = [by[s] for s in STAGES]
    open_stages = [s for s in STAGES if s not in ("Won", "Lost")]
    won, lost = by["Won"]["count"], by["Lost"]["count"]
    return {
        "total_contacts": db.scalar(select(func.count(Contact.id))) or 0,
        "deals_by_stage": stages,
        "open_pipeline_value": sum(by[s]["total_value"] for s in open_stages),
        "weighted_forecast": round(sum(by[s]["total_value"] * STAGE_WEIGHTS[s] for s in open_stages), 2),
        "won_value": by["Won"]["total_value"],
        "win_rate": round(won / (won + lost), 4) if (won + lost) else None,
    }


@router.get("/reports/owners", response_model=list[OwnerStats])
def owner_leaderboard(db: Session = Depends(get_db)):
    """Per-owner performance, ranked by won value."""
    is_open = Deal.stage.notin_(("Won", "Lost"))
    rows = db.execute(
        select(Deal.owner,
               func.sum(case((is_open, 1), else_=0)),
               func.coalesce(func.sum(case((is_open, Deal.value), else_=0.0)), 0.0),
               func.sum(case((Deal.stage == "Won", 1), else_=0)),
               func.coalesce(func.sum(case((Deal.stage == "Won", Deal.value), else_=0.0)), 0.0),
               func.sum(case((Deal.stage == "Lost", 1), else_=0)))
        .where(Deal.owner.is_not(None)).group_by(Deal.owner)).all()
    out = [OwnerStats(owner=o, open_deals=od, open_value=float(ov), won_deals=wd, won_value=float(wv),
                      win_rate=round(wd / (wd + ld), 4) if (wd + ld) else None)
           for o, od, ov, wd, wv, ld in rows]
    return sorted(out, key=lambda r: (-r.won_value, -r.open_value))


@router.get("/reports/activity", response_model=list[FeedItem])
def activity_feed(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """Most recent activities across all deals."""
    rows = db.execute(select(Activity, Deal.title, Contact.company)
                      .join(Deal, Deal.id == Activity.deal_id).join(Contact, Contact.id == Deal.contact_id)
                      .order_by(Activity.created_at.desc(), Activity.id.desc()).limit(limit)).all()
    return [FeedItem(id=a.id, deal_id=a.deal_id, type=a.type, note=a.note, created_at=a.created_at,
                     deal_title=t, company=c) for a, t, c in rows]


@router.get("/reports/deals.csv")
def export_deals(db: Session = Depends(get_db)):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["deal_id", "title", "company", "contact", "stage", "value", "owner"])
    for d, c in db.execute(select(Deal, Contact).join(Contact, Contact.id == Deal.contact_id)).all():
        w.writerow([d.id, d.title, c.company or "", c.name, d.stage, d.value, d.owner or ""])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=deals.csv"})
