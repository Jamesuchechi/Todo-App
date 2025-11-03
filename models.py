from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, ForeignKey, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import enum

class PriorityLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class StatusLevel(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# Many-to-many relationship for todo tags
todo_tags = Table('todo_tags', Base.metadata,
    Column('todo_id', Integer, ForeignKey('todos.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    color = Column(String(7), default="#6B7280")  # Hex color

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    color = Column(String(7), default="#6B7280")

class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(Enum(StatusLevel), default=StatusLevel.PENDING, index=True)
    priority = Column(Enum(PriorityLevel), default=PriorityLevel.MEDIUM, index=True)
    due_date = Column(DateTime, nullable=True, index=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    is_archived = Column(Boolean, default=False, index=True)
    estimated_duration = Column(Integer, nullable=True)  # in minutes
    actual_duration = Column(Integer, nullable=True)  # in minutes
    notes = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey('todos.id'), nullable=True, index=True)
    position = Column(Integer, default=0)  # For manual ordering
    
    # Relationships
    category = relationship("Category")
    tags = relationship("Tag", secondary=todo_tags, backref="todos")
    subtasks = relationship("Todo", backref="parent", remote_side=[id])