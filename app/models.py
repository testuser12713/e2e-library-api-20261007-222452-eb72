"""SQLAlchemy 2.0 ORM models for the library API."""

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Book(Base):
    """A book held by the library."""

    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    titel: Mapped[str] = mapped_column(String, nullable=False)
    autor: Mapped[str] = mapped_column(String, nullable=False)
    isbn: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    erscheinungsjahr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exemplare: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    verfuegbar: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    loans: Mapped[list["Loan"]] = relationship(back_populates="book")


class Member(Base):
    """A registered member of the library."""

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    mitglied_seit: Mapped[date] = mapped_column(Date, nullable=False)
    offene_ausleihen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    loans: Mapped[list["Loan"]] = relationship(back_populates="member")


class Loan(Base):
    """A loan of one book copy by one member."""

    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)
    ausgeliehen_am: Mapped[date] = mapped_column(Date, nullable=False)
    faellig_am: Mapped[date] = mapped_column(Date, nullable=False)
    zurueckgegeben_am: Mapped[date | None] = mapped_column(Date, nullable=True)

    book: Mapped[Book] = relationship(back_populates="loans")
    member: Mapped[Member] = relationship(back_populates="loans")
