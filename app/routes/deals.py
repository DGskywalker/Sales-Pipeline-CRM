from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import STAGES, Activity, Contact, Deal
from app.schemas import ActivityIn, ActivityOut, DealIn, DealOut, DealUpdate

router = APIRouter(tags=["deals"])


@router.post("/deals", response_model=DealOut, status_code=201)
def create_deal(body: DealIn, db: Session = Depends(get_db)):
    if not db.get(Contact, body.contact_id):
        raise HTTPException(404, "Contact not found")
    d = Deal(**body.model_dump())
    db.add(d)
    db.commit()
    return d


@router.get("/deals", response_model=list[DealOut])
def list_deals(stage: str | None = Query(None), owner: str | None = None,
               q: str | None = Query(None, max_length=100),
               limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
               db: Session = Depends(get_db)):
    if stage and stage not in STAGES:
        raise HTTPException(422, f"stage must be one of {STAGES}")
    stmt = (select(Deal).join(Contact).options(joinedload(Deal.contact))
            .order_by(Deal.updated_at.desc()).limit(limit).offset(offset))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(Deal.title.ilike(like), Contact.name.ilike(like), Contact.company.ilike(like)))
    if stage:
        stmt = stmt.where(Deal.stage == stage)
    if owner:
        stmt = stmt.where(Deal.owner == owner)
    return db.scalars(stmt).all()


@router.get("/deals/{deal_id}", response_model=DealOut)
def get_deal(deal_id: int, db: Session = Depends(get_db)):
    d = db.get(Deal, deal_id)
    if not d:
        raise HTTPException(404, "Deal not found")
    return d


@router.patch("/deals/{deal_id}", response_model=DealOut)
def update_deal(deal_id: int, body: DealUpdate, db: Session = Depends(get_db)):
    d = db.get(Deal, deal_id)
    if not d:
        raise HTTPException(404, "Deal not found")
    changes = body.model_dump(exclude_unset=True)
    old_stage = d.stage
    for k, v in changes.items():
        setattr(d, k, v)
    if "stage" in changes and changes["stage"] != old_stage:  # audit trail for pipeline moves
        db.add(Activity(deal_id=d.id, type="stage_change", note=f"{old_stage} -> {changes['stage']}"))
    db.commit()
    return d


@router.delete("/deals/{deal_id}", status_code=204)
def delete_deal(deal_id: int, db: Session = Depends(get_db)):
    d = db.get(Deal, deal_id)
    if not d:
        raise HTTPException(404, "Deal not found")
    db.delete(d)
    db.commit()


@router.post("/deals/{deal_id}/activities", response_model=ActivityOut, status_code=201)
def add_activity(deal_id: int, body: ActivityIn, db: Session = Depends(get_db)):
    if not db.get(Deal, deal_id):
        raise HTTPException(404, "Deal not found")
    a = Activity(deal_id=deal_id, **body.model_dump())
    db.add(a)
    db.commit()
    return a


@router.get("/deals/{deal_id}/activities", response_model=list[ActivityOut])
def list_activities(deal_id: int, db: Session = Depends(get_db)):
    if not db.get(Deal, deal_id):
        raise HTTPException(404, "Deal not found")
    return db.scalars(select(Activity).where(Activity.deal_id == deal_id).order_by(Activity.created_at)).all()
