import csv
import io
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Contact, Deal
from app.schemas import EMAIL_RE, ContactIn, ContactOut, ContactUpdate, DealOut

router = APIRouter(tags=["contacts"])


@router.post("/contacts", response_model=ContactOut, status_code=201)
def create_contact(body: ContactIn, db: Session = Depends(get_db)):
    if db.scalar(select(Contact).where(Contact.email == body.email)):
        raise HTTPException(409, "A contact with this email already exists")
    c = Contact(**body.model_dump())
    db.add(c)
    db.commit()
    return c


@router.get("/contacts", response_model=list[ContactOut])
def list_contacts(
    response: Response,
    q: str | None = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Contact)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(Contact.name.ilike(like), Contact.email.ilike(like), Contact.company.ilike(like)))
    response.headers["X-Total-Count"] = str(db.scalar(select(func.count()).select_from(stmt.subquery())))
    return db.scalars(stmt.order_by(Contact.created_at.desc(), Contact.id.desc()).limit(limit).offset(offset)).all()


@router.get("/contacts/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    c = db.get(Contact, contact_id)
    if not c:
        raise HTTPException(404, "Contact not found")
    return c


@router.get("/contacts/{contact_id}/deals", response_model=list[DealOut])
def contact_deals(contact_id: int, db: Session = Depends(get_db)):
    if not db.get(Contact, contact_id):
        raise HTTPException(404, "Contact not found")
    return db.scalars(select(Deal).where(Deal.contact_id == contact_id).order_by(Deal.updated_at.desc())).all()


@router.patch("/contacts/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: int, body: ContactUpdate, db: Session = Depends(get_db)):
    c = db.get(Contact, contact_id)
    if not c:
        raise HTTPException(404, "Contact not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    return c


@router.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    c = db.get(Contact, contact_id)
    if not c:
        raise HTTPException(404, "Contact not found")
    db.delete(c)
    db.commit()


@router.post("/contacts/import")
async def import_contacts(request: Request, db: Session = Depends(get_db)):
    """Bulk lead import: POST raw CSV (Content-Type: text/csv) with header name,email[,company,phone,source].
    Existing emails are skipped; invalid rows are reported, not fatal."""
    raw = (await request.body()).decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames or not {"name", "email"} <= {f.strip().lower() for f in reader.fieldnames}:
        raise HTTPException(400, "CSV must have 'name' and 'email' columns")
    created = skipped = 0
    errors: list[dict] = []
    seen = set(db.scalars(select(Contact.email)).all())
    for i, row in enumerate(reader, start=2):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        email = row.get("email", "").lower()
        if not row.get("name") or not re.match(EMAIL_RE, email):
            errors.append({"row": i, "reason": "missing name or invalid email"})
            continue
        if email in seen:
            skipped += 1
            continue
        seen.add(email)
        db.add(Contact(name=row["name"], email=email, company=row.get("company") or None,
                       phone=row.get("phone") or None, source=row.get("source") or "csv_import"))
        created += 1
    db.commit()
    return {"created": created, "skipped_duplicates": skipped, "errors": errors}
