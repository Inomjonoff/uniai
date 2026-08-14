"""
SQLAlchemy models for UNICON-SOFT AI Technical Assistant.
Includes support for pgvector embeddings and full audit/source tracking.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    Boolean,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
import enum
from app.db.session import Base

try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    Vector = None


class SourceType(str, enum.Enum):
    USER = "USER"
    TELEGRAM_GROUP = "TELEGRAM_GROUP"
    TELEGRAM_PRIVATE = "TELEGRAM_PRIVATE"
    FILE = "FILE"
    IMAGE = "IMAGE"
    WEB = "WEB"
    SYSTEM = "SYSTEM"


class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED_BY_USER = "VERIFIED_BY_USER"
    VERIFIED_BY_COMMUNITY = "VERIFIED_BY_COMMUNITY"
    DEPRECATED = "DEPRECATED"


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class TelegramGroup(Base):
    __tablename__ = "telegram_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    username = Column(String(255), nullable=True)
    learning_enabled = Column(Boolean, default=True, nullable=False)
    reply_enabled = Column(Boolean, default=False, nullable=False)
    status = Column(String(50), default="active", nullable=False)
    last_processed_message_id = Column(BigInteger, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    messages = relationship("TelegramMessage", back_populates="group", cascade="all, delete-orphan")


class TelegramMessage(Base):
    __tablename__ = "telegram_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, ForeignKey("telegram_groups.chat_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=True)
    sender_name = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    text = Column(Text, nullable=True)
    media_type = Column(String(50), nullable=True)  # text, photo, document, voice
    file_id = Column(String(255), nullable=True)
    reply_to_message_id = Column(BigInteger, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_processed = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    group = relationship("TelegramGroup", back_populates="messages")

    __table_args__ = (
        Index("ix_chat_message", "chat_id", "message_id", unique=True),
    )


class Knowledge(Base):
    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=True)
    problem = Column(Text, nullable=True)
    possible_cause = Column(Text, nullable=True)
    solution = Column(Text, nullable=True)
    raw_content = Column(Text, nullable=False)
    category = Column(String(100), default="general", nullable=False, index=True)
    tags = Column(JSON, default=list, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)  # 0.0 to 1.0
    trust_score = Column(Float, default=1.0, nullable=False)  # USER = 1.0, Group = 0.8, Web = 0.5
    verification_status = Column(SQLEnum(VerificationStatus), default=VerificationStatus.UNVERIFIED, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    sources = relationship("KnowledgeSource", back_populates="knowledge", cascade="all, delete-orphan")
    embeddings = relationship("KnowledgeEmbedding", back_populates="knowledge", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="knowledge", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="knowledge", cascade="all, delete-orphan")


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(SQLEnum(SourceType), default=SourceType.USER, nullable=False, index=True)
    source_id = Column(String(255), nullable=True)  # Chat ID, User ID, or File Path
    source_message_id = Column(BigInteger, nullable=True)
    source_group_name = Column(String(255), nullable=True)
    author = Column(String(255), nullable=True)
    url = Column(String(1000), nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    knowledge = relationship("Knowledge", back_populates="sources")


class KnowledgeEmbedding(Base):
    __tablename__ = "knowledge_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Use Vector(3072) if pgvector is installed, otherwise JSON
    if PGVECTOR_AVAILABLE:
        embedding = Column(Vector(3072), nullable=True)
    else:
        embedding = Column(JSON, nullable=True)
        
    embedding_json = Column(JSON, nullable=True)  # JSON fallback for raw vectors
    model_name = Column(String(100), default="gemini-embedding-001", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    knowledge = relationship("Knowledge", back_populates="embeddings")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge.id", ondelete="SET NULL"), nullable=True, index=True)
    telegram_file_id = Column(String(255), nullable=False)
    telegram_message_id = Column(BigInteger, nullable=True)
    chat_id = Column(BigInteger, nullable=True)
    file_name = Column(String(255), nullable=True)
    file_type = Column(String(50), nullable=False)  # image, pdf, docx, etc.
    file_size = Column(Integer, nullable=True)
    ocr_text = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    detected_errors = Column(JSON, default=list, nullable=False)
    system_name = Column(String(100), nullable=True)
    if PGVECTOR_AVAILABLE:
        embedding = Column(Vector(3072), nullable=True)
    else:
        embedding = Column(JSON, nullable=True)
    embedding_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    knowledge = relationship("Knowledge", back_populates="attachments")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="Active Chat", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="conversations")
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="ConversationMessage.id")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    tool_calls_json = Column(JSON, nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
    feedbacks = relationship("Feedback", back_populates="message", cascade="all, delete-orphan")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge.id", ondelete="SET NULL"), nullable=True)
    conversation_message_id = Column(Integer, ForeignKey("conversation_messages.id", ondelete="SET NULL"), nullable=True)
    telegram_user_id = Column(BigInteger, nullable=False)
    rating = Column(String(20), nullable=False)  # thumbs_up, thumbs_down
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    knowledge = relationship("Knowledge", back_populates="feedbacks")
    message = relationship("ConversationMessage", back_populates="feedbacks")


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value_json = Column(JSON, nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String(100), nullable=False)
    payload_json = Column(JSON, default=dict, nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
