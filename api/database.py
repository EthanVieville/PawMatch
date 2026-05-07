import os
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
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
    # Colonne vectorielle — NULL pour l'instant, remplie quand on branche le LLM
    embedding = Column(Vector(1536), nullable=True)

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


def init_db():
    # L'extension vector doit exister avant que create_all crée la colonne embedding
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
