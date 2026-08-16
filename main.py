import os
from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./playlist.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)
    event_id = Column(String, unique=True, nullable=False)
    league = Column(String, default="Football")
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=True)
    stream_url = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)
    last_status = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(engine)

app = FastAPI(title="My Personal IPTV")


@app.get("/")
def home():
    return {"status": "ok", "playlist": "/playlist.m3u"}


@app.get("/playlist.m3u", response_class=PlainTextResponse)
def playlist():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        matches = (
            db.query(Match)
            .filter(Match.enabled == True)
            .filter((Match.start_time == None) | (Match.start_time >= now))
            .order_by(Match.start_time.asc())
            .all()
        )

        output = ["#EXTM3U"]

        for match in matches:
            if not match.stream_url:
                continue

            title = f"{match.home_team} vs {match.away_team}"
            group = match.league or "Football"

            output.append(
                f'#EXTINF:-1 group-title="{group}",{title}'
            )
            output.append(match.stream_url)

        return "\n".join(output) + "\n"
    finally:
        db.close()
