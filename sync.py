import os
import re
import asyncio
from datetime import datetime, timedelta

import httpx
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

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}


async def check_stream(url):
    if not url:
        return None
    try:
        async with httpx.AsyncClient(
            timeout=10, follow_redirects=True, headers=HEADERS
        ) as client:
            response = await client.get(url)
            return response.status_code
    except Exception:
        return None


def extract_m3u8(html):
    pattern = r'https?://[^"\'>\s]+\.m3u8(?:\?[^"\'>\s]*)?'
    return list(dict.fromkeys(re.findall(pattern, html, re.IGNORECASE)))


async def find_new_stream(source_url):
    if not source_url:
        return None

    try:
        async with httpx.AsyncClient(
            timeout=20, follow_redirects=True, headers=HEADERS
        ) as client:
            response = await client.get(source_url)
            response.raise_for_status()
            urls = extract_m3u8(response.text)

            # Chỉ tự chọn khi nguồn trả đúng một stream.
            # Không chọn bừa nếu có nhiều stream.
            return urls[0] if len(urls) == 1 else None
    except Exception:
        return None


async def main():
    db = SessionLocal()
    try:
        matches = db.query(Match).filter(Match.enabled == True).all()

        for match in matches:
            if not match.stream_url:
                continue

            status = await check_stream(match.stream_url)
            match.last_status = status
            match.updated_at = datetime.utcnow()

            print(f"{match.home_team} - {match.away_team}: {status}")

            if status != 200:
                new_url = await find_new_stream(match.source_url)

                if new_url and await check_stream(new_url) == 200:
                    match.stream_url = new_url
                    match.last_status = 200
                    print(f"Updated: {match.home_team} - {match.away_team}")

            await asyncio.sleep(0.2)

        cutoff = datetime.utcnow() - timedelta(hours=6)
        for match in db.query(Match).filter(Match.start_time < cutoff).all():
            match.enabled = False

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
