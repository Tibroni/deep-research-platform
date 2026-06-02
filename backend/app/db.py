import datetime
import uuid
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

class Base(DeclarativeBase):
    pass

class ResearchJob(Base):
    __tablename__ = "research_jobs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255))
    prompt: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50))  # pending, planning, awaiting_plan_approval, researching, checking, writing, awaiting_final_approval, completed, failed
    thread_id: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    reports: Mapped[List["Report"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    sources: Mapped[List["Source"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    feedback: Mapped[List["HumanFeedback"]] = relationship(back_populates="job", cascade="all, delete-orphan")

class Report(Base):
    __tablename__ = "reports"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("research_jobs.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    
    job: Mapped["ResearchJob"] = relationship(back_populates="reports")

class Source(Base):
    __tablename__ = "sources"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("research_jobs.id", ondelete="CASCADE"))
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(Text)
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    
    job: Mapped["ResearchJob"] = relationship(back_populates="sources")

class HumanFeedback(Base):
    __tablename__ = "human_feedback"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("research_jobs.id", ondelete="CASCADE"))
    step_name: Mapped[str] = mapped_column(String(100))  # plan_approval, final_approval
    approved: Mapped[bool] = mapped_column(Boolean)
    feedback_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    
    job: Mapped["ResearchJob"] = relationship(back_populates="feedback")

# Engine initialization
engine = create_async_engine(settings.db_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    """Initializes the database schema."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Dependency injection helper for FastAPI endpoints."""
    async with async_session() as session:
        yield session
