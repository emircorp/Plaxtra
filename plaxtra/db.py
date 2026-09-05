import os
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, String, Integer, Boolean, Text, DateTime, ForeignKey, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, relationship

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
DATABASE_URL = os.getenv("PLAXTRA_DATABASE_URL", f"sqlite:///{DATA / 'plaxtra.db'}")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(20), default="user")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Movie(Base):
    __tablename__ = "movies"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    synopsis: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    genre: Mapped[str] = mapped_column(String(300), default="")
    poster_url: Mapped[str] = mapped_column(String(500), default="")
    backdrop_url: Mapped[str] = mapped_column(String(500), default="")
    stream_url: Mapped[str] = mapped_column(String(1000), default="")
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

class Series(Base):
    __tablename__ = "series"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    synopsis: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    genre: Mapped[str] = mapped_column(String(300), default="")
    poster_url: Mapped[str] = mapped_column(String(500), default="")
    backdrop_url: Mapped[str] = mapped_column(String(500), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    seasons: Mapped[list["Season"]] = relationship(back_populates="series", cascade="all, delete-orphan")

class Season(Base):
    __tablename__ = "seasons"
    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"))
    season_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    series: Mapped[Series] = relationship(back_populates="seasons")
    episodes: Mapped[list["Episode"]] = relationship(back_populates="season", cascade="all, delete-orphan")

class Episode(Base):
    __tablename__ = "episodes"
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    episode_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    synopsis: Mapped[str] = mapped_column(Text, default="")
    stream_url: Mapped[str] = mapped_column(String(1000), default="")
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    season: Mapped[Season] = relationship(back_populates="episodes")

class Channel(Base):
    __tablename__ = "channels"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    group_name: Mapped[str] = mapped_column(String(120), default="General")
    logo_url: Mapped[str] = mapped_column(String(500), default="")
    stream_url: Mapped[str] = mapped_column(String(1000))
    epg_id: Mapped[str] = mapped_column(String(200), default="")
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

class Playlist(Base):
    __tablename__ = "playlists"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(String(1000))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class WatchProgress(Base):
    __tablename__ = "watch_progress"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    media_type: Mapped[str] = mapped_column(String(30))
    media_id: Mapped[int] = mapped_column(Integer)
    position: Mapped[float] = mapped_column(default=0)
    duration: Mapped[float] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Favorite(Base):
    __tablename__ = "favorites"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    media_type: Mapped[str] = mapped_column(String(30))
    media_id: Mapped[int] = mapped_column(Integer)

class Setting(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[str] = mapped_column(Text, default="")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(120))
    target: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def _add_missing_columns():
    # Small self-contained migration for installs created before metadata_json existed.
    inspector = inspect(engine)
    additions = {
        'movies': 'metadata_json', 'series': 'metadata_json', 'seasons': 'metadata_json',
        'episodes': 'metadata_json', 'channels': 'metadata_json'
    }
    with engine.begin() as conn:
        for table, column in additions.items():
            if table in inspector.get_table_names() and column not in {c['name'] for c in inspector.get_columns(table)}:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} TEXT NOT NULL DEFAULT \'{{}}\''))


def init_db():
    Base.metadata.create_all(engine)
    _add_missing_columns()
    db = SessionLocal()
    defaults = {"app_name":"Plaxtra", "tagline":"Your media. Your server.", "accent":"#8ea8ff", "attribution":"Powered by Plaxtra"}
    for key, value in defaults.items():
        if not db.query(Setting).filter_by(key=key).first(): db.add(Setting(key=key, value=value))
    db.commit(); db.close()
