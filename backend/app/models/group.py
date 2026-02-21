import uuid
import secrets
import string
from datetime import datetime, timezone
import enum

from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GroupRole(str, enum.Enum):
    owner = "owner"
    member = "member"


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    invite_code: Mapped[str] = mapped_column(
        String(12), unique=True, nullable=False,
        default=lambda: ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), default="SGD")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    members: Mapped[list["GroupMember"]] = relationship(back_populates="group", lazy="selectin", cascade="all, delete-orphan")


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"), index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    role: Mapped[GroupRole] = mapped_column(SAEnum(GroupRole), nullable=False, default=GroupRole.member)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    group: Mapped["Group"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(lazy="selectin")

    @property
    def display_name(self) -> str:
        return self.user.display_name if self.user else "Unknown"
