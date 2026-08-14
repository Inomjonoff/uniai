"""
SQLAlchemy ORM Models for UNICON-SOFT AI Assistant.
"""
from datetime import datetime
import enum
from typing import Optional, List
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
    Enum as SQLEnum,
    Table
)
from sqlalchemy.orm import relationship
from app.db.session import Base


class TrustLevel(int, enum.Enum):
    USER = 3              # Direct instructions from user (Highest priority)
    TELEGRAM_GROUP = 2    # Verified technical solutions from Telegram groups
    FILE = 1              # External uploaded files / documents


class SourceType(str, enum.Enum):
    USER = "USER"
    USER_INSTRUCTION = "USER"
    TELEGRAM_GROUP = "TELEGRAM_GROUP"
    SCREENSHOT = "SCREENSHOT"
    FILE = "FILE"
    FILE_UPLOAD = "FILE"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    full_name = Column(String(255), nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class TelegramGroup(Base):
    __tablename__ = "telegram_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    username = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    learning_enabled = Column(Boolean, default=True, nullable=False)
    reply_enabled = Column(Boolean, default=False, nullable=False)  # Silent listener by default
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    messages = relationship("TelegramMessage", back_populates="group", cascade="all, delete-orphan")


class TelegramMessage(Base):
    __tablename__ = "telegram_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(BigInteger, nullable=False, index=True)
    chat_id = Column(BigInteger, ForeignKey("telegram_groups.chat_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=True)
    sender_name = Column(String(255), nullable=True)
    username = Column(String(100), nullable=True)
    text = Column(Text, nullable=True)
    media_type = Column(String(50), default="text", nullable=False)  # text, photo, document, voice
    file_id = Column(String(255), nullable=True)
    reply_to_message_id = Column(BigInteger, nullable=True)
    is_processed = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    group = relationship("TelegramGroup", back_populates="messages")


class VerificationStatus(str, enum.Enum):
    VERIFIED_BY_USER = "verified_by_user"
    UNVERIFIED = "unverified"


class Knowledge(Base):
    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    problem = Column(Text, nullable=True)
    possible_cause = Column(Text, nullable=True)
    solution = Column(Text, nullable=False)
    raw_content = Column(Text, nullable=True)
    category = Column(String(100), default="general", nullable=False, index=True)
    system_name = Column(String(100), nullable=True, index=True)
    trust_level = Column(SQLEnum(TrustLevel), default=TrustLevel.TELEGRAM_GROUP, nullable=False, index=True)
    confidence = Column(Float, default=1.0, nullable=False)
    confidence_score = Column(Float, default=1.0, nullable=False)
    trust_score = Column(Float, default=0.8, nullable=False)
    verified_by_user = Column(Boolean, default=False, nullable=False)
    verification_status = Column(SQLEnum(VerificationStatus), default=VerificationStatus.UNVERIFIED, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    tags = Column(JSON, default=list, nullable=False)
    tags_list = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    embeddings = relationship("KnowledgeEmbedding", back_populates="knowledge", cascade="all, delete-orphan")
    sources = relationship("KnowledgeSource", back_populates="knowledge", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="knowledge", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="knowledge", cascade="all, delete-orphan")


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(SQLEnum(SourceType), nullable=False)
    source_id = Column(String(255), nullable=True)
    source_message_id = Column(BigInteger, nullable=True)
    chat_id = Column(BigInteger, nullable=True)
    message_id = Column(BigInteger, nullable=True)
    author = Column(String(255), nullable=True)
    author_name = Column(String(255), nullable=True)
    source_group_name = Column(String(255), nullable=True)
    group_title = Column(String(255), nullable=True)
    message_link = Column(String(500), nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    knowledge = relationship("Knowledge", back_populates="sources")


class KnowledgeEmbedding(Base):
    __tablename__ = "knowledge_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding = Column(JSON, nullable=True)
    embedding_json = Column(JSON, nullable=True)
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
    embedding = Column(JSON, nullable=True)
    embedding_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    knowledge = relationship("Knowledge", back_populates="attachments")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="New Session", nullable=False)
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


class UnresolvedQuery(Base):
    """
    Tracks questions, technical issues, or requests that the AI did not know or could not answer.
    Presented as interactive buttons to the admin for manual teaching and knowledge ingestion.
    """
    __tablename__ = "unresolved_queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_text = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    chat_id = Column(BigInteger, nullable=True)
    user_id = Column(BigInteger, nullable=True)
    sender_name = Column(String(255), nullable=True)
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, learned, dismissed
    admin_solution = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
