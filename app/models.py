from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

STAGES = ["Lead", "Contacted", "Qualified", "Proposal", "Won", "Lost"]
STAGE_WEIGHTS = {"Lead": 0.1, "Contacted": 0.2, "Qualified": 0.4, "Proposal": 0.6, "Won": 1.0, "Lost": 0.0}


def now():
    return datetime.now(timezone.utc)


class Contact(Base):
    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    company: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    deals: Mapped[list["Deal"]] = relationship(back_populates="contact", cascade="all, delete-orphan")


class Deal(Base):
    __tablename__ = "deals"
    id: Mapped[int] = mapped_column(primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(160))
    value: Mapped[float] = mapped_column(Float, default=0.0)
    stage: Mapped[str] = mapped_column(String(20), default="Lead")
    owner: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    contact: Mapped[Contact] = relationship(back_populates="deals")
    activities: Mapped[list["Activity"]] = relationship(back_populates="deal", cascade="all, delete-orphan")
    __table_args__ = (Index("ix_deals_stage", "stage"),)

    @property
    def contact_name(self) -> str:
        return self.contact.name

    @property
    def company(self) -> str | None:
        return self.contact.company


class Activity(Base):
    __tablename__ = "activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(30))  # note | call | email | meeting | stage_change
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    deal: Mapped[Deal] = relationship(back_populates="activities")
