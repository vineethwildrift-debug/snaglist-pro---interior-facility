import enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Enum,
    ForeignKey, JSON, Boolean, Index,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from snaglist_pro.database import Base


class SnagStatus(str, enum.Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"
    REOPENED = "Reopened"


class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    INSPECTOR = "Inspector"
    VENDOR = "Vendor"
    CLIENT = "Client"


class Project(Base):
    __tablename__ = "projects"

    id: int = Column(Integer, primary_key=True)
    name: str = Column(String(255), nullable=False, index=True)
    slug: str = Column(String(255), unique=True, nullable=False, index=True)
    facility: str = Column(String(100), default="")
    client: str = Column(String(255), default="")
    floor: str = Column(String(50), default="")

    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active: bool = Column(Boolean, default=True)

    snags: Mapped[List["Snag"]] = relationship("Snag", back_populates="project", cascade="all, delete-orphan")
    attachments: Mapped[List["AttachmentRecord"]] = relationship("AttachmentRecord", back_populates="project", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "facility": self.facility,
            "client": self.client,
            "floor": self.floor,
            "snag_count": len(self.snags) if self.snags else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
        }


class Snag(Base):
    __tablename__ = "snags"

    id: int = Column(Integer, primary_key=True)
    project_id: int = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    index: int = Column(Integer, default=0)

    image_filename: str = Column(String(255), default="")
    image_path: str = Column(String(500), default="")
    description: str = Column(Text, default="")
    description_enhanced: str = Column(Text, default="")

    sender: str = Column(String(255), default="")
    date_reported: str = Column(String(20), default="")

    category: str = Column(String(100), default="Unassigned")
    area: str = Column(String(255), default="")
    check_point: str = Column(Text, default="")
    priority: str = Column(String(20), default="Medium")
    status: str = Column(String(20), default=SnagStatus.OPEN.value, index=True)
    vendor: str = Column(String(255), default="")
    match_score: float = Column(Float, default=0.0)

    closed_date: str = Column(String(20), default="")
    closed_image_path: str = Column(String(500), default="")

    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="snags")
    status_history: Mapped[List["StatusHistory"]] = relationship(
        "StatusHistory", back_populates="snag", cascade="all, delete-orphan",
        order_by="StatusHistory.changed_at.desc()",
    )

    __table_args__ = (
        Index("ix_snags_project_status", "project_id", "status"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "index": self.index,
            "image_filename": self.image_filename,
            "description": self.description,
            "description_enhanced": self.description_enhanced,
            "sender": self.sender,
            "date_reported": self.date_reported,
            "category": self.category,
            "area": self.area,
            "check_point": self.check_point,
            "priority": self.priority,
            "status": self.status,
            "vendor": self.vendor,
            "match_score": self.match_score,
            "closed_date": self.closed_date,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: int = Column(Integer, primary_key=True)
    snag_id: int = Column(Integer, ForeignKey("snags.id"), nullable=False, index=True)
    from_status: str = Column(String(20), nullable=True)
    to_status: str = Column(String(20), nullable=False)
    changed_by: str = Column(String(255), default="")
    changed_by_user_id: int = Column(Integer, ForeignKey("users.id"), nullable=True)
    comment: str = Column(Text, default="")
    changed_at: datetime = Column(DateTime, default=datetime.utcnow)

    snag: Mapped["Snag"] = relationship("Snag", back_populates="status_history")
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[changed_by_user_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "snag_id": self.snag_id,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "changed_by": self.changed_by,
            "comment": self.comment,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
        }


class User(Base):
    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True)
    username: str = Column(String(100), unique=True, nullable=False, index=True)
    email: str = Column(String(255), unique=True, nullable=True)
    password_hash: str = Column(String(255), nullable=False)
    role: str = Column(String(20), default=UserRole.INSPECTOR.value)
    display_name: str = Column(String(255), default="")
    vendor_name: str = Column(String(255), default="")
    is_active: bool = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    last_login: Optional[datetime] = Column(DateTime, nullable=True)

    status_changes: Mapped[List["StatusHistory"]] = relationship(
        "StatusHistory", foreign_keys=[StatusHistory.changed_by_user_id],
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "display_name": self.display_name,
            "vendor_name": self.vendor_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


class AttachmentRecord(Base):
    __tablename__ = "attachments"

    id: int = Column(Integer, primary_key=True)
    project_id: int = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    attachment_name: str = Column(String(255), nullable=False)
    attachment_type: str = Column(String(50), default="")
    file_size: int = Column(Integer, default=0)
    file_path: str = Column(String(500), default="")
    page_count: Optional[int] = Column(Integer, nullable=True)
    layer_count: Optional[int] = Column(Integer, nullable=True)
    entity_count: Optional[int] = Column(Integer, nullable=True)
    layer_names: str = Column(Text, default="")
    text_snippet: str = Column(Text, default="")
    keyword_summary: str = Column(Text, default="")
    suggested_action: str = Column(Text, default="")
    analysis_notes: str = Column(Text, default="")
    referenced: bool = Column(Boolean, default=False)
    reference_count: int = Column(Integer, default=0)
    first_referenced_by: str = Column(String(255), default="")
    first_reference_date: str = Column(String(20), default="")
    chat_notes: str = Column(Text, default="")
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="attachments")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "attachment_name": self.attachment_name,
            "attachment_type": self.attachment_type,
            "file_size_kb": round(self.file_size / 1024, 1) if self.file_size else 0,
            "page_count": self.page_count,
            "layer_count": self.layer_count,
            "entity_count": self.entity_count,
            "layer_names": self.layer_names,
            "keyword_summary": self.keyword_summary,
            "suggested_action": self.suggested_action,
            "referenced": self.referenced,
        }
