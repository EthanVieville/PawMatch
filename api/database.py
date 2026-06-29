import os
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://pawmatch:pawmatch@localhost:5432/pawmatch",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Animal(Base):
    __tablename__ = "animals"
    __table_args__ = (UniqueConstraint("source", "source_url", name="uq_animals_source_url"),)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String, nullable=False)
    source_url = Column(String, nullable=False)
    name = Column(String, nullable=False)
    species = Column(String)
    race = Column(String)
    sex = Column(String)
    birth_date = Column(String)
    age = Column(Integer)
    refuge = Column(String)
    description = Column(Text)
    incompatibilities = Column(ARRAY(String))
    scraped_at = Column(TIMESTAMP, server_default="NOW()")
    embedding = Column(Vector(384), nullable=True)
    race_predicted = Column(String, nullable=True)
    race_confidence = Column(Float, nullable=True)
    description_rewritten = Column(Text, nullable=True)

    images = relationship(
        "AnimalImage",
        back_populates="animal",
        cascade="all, delete-orphan",
        order_by="AnimalImage.position",
    )


class AnimalImage(Base):
    __tablename__ = "animal_images"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    animal_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("animals.id", ondelete="CASCADE"),
        nullable=False,
    )
    url = Column(String, nullable=False)
    position = Column(Integer, default=0)

    animal = relationship("Animal", back_populates="images")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(String, nullable=False)  # adoption_process | care_advice | shelter_info
    source = Column(String)                    # la-spa | secondechance | general
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=True)
    created_at = Column(TIMESTAMP, server_default="NOW()")


class Refuge(Base):
    __tablename__ = "refuges"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    source = Column(String)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    geocoded_at = Column(TIMESTAMP, nullable=True)


class LLMCache(Base):
    __tablename__ = "llm_cache"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_text = Column(Text, nullable=False)
    query_embedding = Column(Vector(384), nullable=False)
    response_text = Column(Text, nullable=False)
    feature = Column(String, nullable=False, default="chat")
    hit_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default="NOW()")
    last_hit_at = Column(TIMESTAMP, server_default="NOW()")
    expires_at = Column(TIMESTAMP, nullable=False)


class LLMTrace(Base):
    __tablename__ = "llm_traces"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature = Column(String, nullable=False)      # chat | description_rewrite
    model_id = Column(String, nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)
    tool_calls = Column(JSONB, nullable=True)      # [{"name": "search_animals", ...}]
    rag_chunks_used = Column(Integer, default=0)
    error = Column(Boolean, default=False)
    feedback = Column(String, nullable=True)       # "positive" | "negative" | null
    user_message = Column(Text, nullable=True)
    assistant_response = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default="NOW()")


def init_db():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Migration safe : ajoute les colonnes si elles n'existent pas encore
        conn.execute(text(
            "ALTER TABLE animals ADD COLUMN IF NOT EXISTS race_predicted VARCHAR"
        ))
        conn.execute(text(
            "ALTER TABLE animals ADD COLUMN IF NOT EXISTS race_confidence FLOAT"
        ))
        conn.execute(text(
            "ALTER TABLE animals ADD COLUMN IF NOT EXISTS description_rewritten TEXT"
        ))
        conn.execute(text(
            "ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS feedback VARCHAR"
        ))
        conn.execute(text(
            "ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS user_message TEXT"
        ))
        conn.execute(text(
            "ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS assistant_response TEXT"
        ))
        conn.commit()
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
