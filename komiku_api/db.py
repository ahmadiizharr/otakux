"""SQLAlchemy 2.0 models + engine/session untuk Otakudesu API.

Domainnya anime: satu `Anime` punya banyak `Episode` (1-m) dan banyak `Genre`
(m2m). Berbeda dari manga, "episode" bukan gambar — halaman episode hanya
menyimpan URL sumber; link download di-scrape live saat diminta (lihat main.py).
"""
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

# Path absolut ke komiku_api/anime.db supaya API selalu memakai DB yang sama
# tak peduli dari direktori mana uvicorn/skrip dijalankan (dulu relatif ke CWD).
DB_PATH = Path(__file__).resolve().parent / "anime.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


anime_genre = Table(
    "anime_genre", Base.metadata,
    Column("anime_id", ForeignKey("anime.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genre.id", ondelete="CASCADE"), primary_key=True),
)


def _now() -> str:
    return dt.datetime.utcnow().isoformat(timespec="seconds")


class Anime(Base):
    __tablename__ = "anime"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str] = mapped_column(String)
    title_japanese: Mapped[str | None] = mapped_column(String, nullable=True)
    type: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    producers: Mapped[str | None] = mapped_column(String, nullable=True)
    studio: Mapped[str | None] = mapped_column(String, nullable=True)
    total_episode: Mapped[str | None] = mapped_column(String, nullable=True)
    duration: Mapped[str | None] = mapped_column(String, nullable=True)
    release_date: Mapped[str | None] = mapped_column(String, nullable=True)
    synopsis: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail: Mapped[str | None] = mapped_column(String, nullable=True)
    source_url: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=_now)
    updated_at: Mapped[str] = mapped_column(String, default=_now, onupdate=_now)

    genres: Mapped[list["Genre"]] = relationship(
        secondary=anime_genre, back_populates="animes", lazy="selectin")
    episodes: Mapped[list["Episode"]] = relationship(
        back_populates="anime", cascade="all, delete-orphan",
        order_by="Episode.number", lazy="selectin")


class Genre(Base):
    __tablename__ = "genre"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    animes: Mapped[list["Anime"]] = relationship(
        secondary=anime_genre, back_populates="genres")


class Episode(Base):
    __tablename__ = "episode"
    __table_args__ = (UniqueConstraint("url", name="uq_episode_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    anime_id: Mapped[int] = mapped_column(
        ForeignKey("anime.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String)
    number: Mapped[float | None] = mapped_column(Float, nullable=True)
    url: Mapped[str] = mapped_column(String)
    released_at: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=_now)

    anime: Mapped["Anime"] = relationship(back_populates="episodes")


# Catatan: link download episode TIDAK disimpan di DB. Endpoint di main.py
# live-fetch ke Otakudesu tiap request (lihat scraper.scrape_episode).


def init_db() -> None:
    Base.metadata.create_all(engine)
