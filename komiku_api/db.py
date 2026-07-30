"""SQLAlchemy 2.0 models + engine/session untuk Komiku API."""
from __future__ import annotations
import datetime as dt
from pathlib import Path
from sqlalchemy import (
    create_engine, ForeignKey, String, Integer, Float, Text, Table, Column,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker,
)

# Path absolut ke komiku_api/komiku.db supaya API selalu memakai DB yang sama
# tak peduli dari direktori mana uvicorn/skrip dijalankan (dulu relatif ke CWD).
DB_PATH = Path(__file__).resolve().parent / "komiku.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


manga_genre = Table(
    "manga_genre", Base.metadata,
    Column("manga_id", ForeignKey("manga.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genre.id", ondelete="CASCADE"), primary_key=True),
)


def _now() -> str:
    return dt.datetime.utcnow().isoformat(timespec="seconds")


class Manga(Base):
    __tablename__ = "manga"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str] = mapped_column(String)
    title_alt: Mapped[str | None] = mapped_column(String, nullable=True)
    type: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    theme: Mapped[str | None] = mapped_column(String, nullable=True)
    author: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    age_rating: Mapped[str | None] = mapped_column(String, nullable=True)
    reading_direction: Mapped[str | None] = mapped_column(String, nullable=True)
    total_views: Mapped[int] = mapped_column(Integer, default=0)
    synopsis: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail: Mapped[str | None] = mapped_column(String, nullable=True)
    source_url: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=_now)
    updated_at: Mapped[str] = mapped_column(String, default=_now, onupdate=_now)

    genres: Mapped[list["Genre"]] = relationship(
        secondary=manga_genre, back_populates="mangas", lazy="selectin")
    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="manga", cascade="all, delete-orphan",
        order_by="Chapter.number", lazy="selectin")


class Genre(Base):
    __tablename__ = "genre"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    mangas: Mapped[list["Manga"]] = relationship(
        secondary=manga_genre, back_populates="genres")


class Chapter(Base):
    __tablename__ = "chapter"
    __table_args__ = (UniqueConstraint("url", name="uq_chapter_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    manga_id: Mapped[int] = mapped_column(
        ForeignKey("manga.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String)
    number: Mapped[float | None] = mapped_column(Float, nullable=True)
    url: Mapped[str] = mapped_column(String)
    released_at: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=_now)

    manga: Mapped["Manga"] = relationship(back_populates="chapters")


# Catatan: gambar halaman TIDAK disimpan di DB. Endpoint reader di main.py
# live-fetch ke Komiku tiap request (lihat scraper.scrape_chapter).


def init_db() -> None:
    Base.metadata.create_all(engine)
