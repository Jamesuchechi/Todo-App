from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, ForeignKey, Table, JSON, Float
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

class RecurrencePattern(enum.Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

# Many-to-many relationship for todo tags
todo_tags = Table('todo_tags', Base.metadata,
    Column('todo_id', Integer, ForeignKey('todos.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

# Many-to-many relationship for todo dependencies
todo_dependencies = Table('todo_dependencies', Base.metadata,
    Column('todo_id', Integer, ForeignKey('todos.id')),
    Column('depends_on_id', Integer, ForeignKey('todos.id'))
)

# Many-to-many relationship for todo assignees
todo_assignees = Table('todo_assignees', Base.metadata,
    Column('todo_id', Integer, ForeignKey('todos.id')),
    Column('user_id', Integer, ForeignKey('users.id'))
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100))
    avatar_url = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Preferences
    theme = Column(String(20), default="light")  # light, dark
    notification_enabled = Column(Boolean, default=True)

class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    color = Column(String(7), default="#6B7280")

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    color = Column(String(7), default="#6B7280")
    icon = Column(String(50), default="fa-folder")

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
    position = Column(Integer, default=0)
    
    # NEW: Recurring tasks
    recurrence_pattern = Column(Enum(RecurrencePattern), default=RecurrencePattern.NONE)
    recurrence_end_date = Column(DateTime, nullable=True)
    original_todo_id = Column(Integer, ForeignKey('todos.id'), nullable=True)  # Link to original recurring task
    
    # NEW: Template feature
    is_template = Column(Boolean, default=False, index=True)
    template_name = Column(String(100), nullable=True)
    
    # NEW: Time tracking
    time_entries = Column(JSON, nullable=True)  # [{"start": "", "end": "", "duration": 0}]
    timer_started_at = Column(DateTime, nullable=True)
    
    # NEW: Attachments
    attachments = Column(JSON, nullable=True)  # [{"name": "", "url": "", "size": 0, "type": ""}]
    
    # NEW: Reminders
    reminder_datetime = Column(DateTime, nullable=True)
    reminder_sent = Column(Boolean, default=False)
    
    # NEW: Pomodoro tracking
    pomodoro_count = Column(Integer, default=0)
    pomodoro_target = Column(Integer, nullable=True)
    
    # NEW: Owner/Creator
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relationships
    category = relationship("Category")
    tags = relationship("Tag", secondary=todo_tags, backref="todos")
    subtasks = relationship("Todo", backref="parent", remote_side=[id], foreign_keys=[parent_id])
    dependencies = relationship(
        "Todo",
        secondary=todo_dependencies,
        primaryjoin=id == todo_dependencies.c.todo_id,
        secondaryjoin=id == todo_dependencies.c.depends_on_id,
        backref="dependent_tasks"
    )
    assignees = relationship("User", secondary=todo_assignees, backref="assigned_todos")
    comments = relationship("Comment", back_populates="todo", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    todo_id = Column(Integer, ForeignKey('todos.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    todo = relationship("Todo", back_populates="comments")
    user = relationship("User")

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    todo_id = Column(Integer, ForeignKey('todos.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    action = Column(String(50), nullable=False)  # created, updated, completed, etc.
    details = Column(JSON, nullable=True)  # What changed
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    todo = relationship("Todo")
    user = relationship("User")

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    todo_id = Column(Integer, ForeignKey('todos.id'), nullable=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
    todo = relationship("Todo")

class Analytics(Base):
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    date = Column(DateTime, nullable=False, index=True)
    tasks_completed = Column(Integer, default=0)
    tasks_created = Column(Integer, default=0)
    total_time_spent = Column(Integer, default=0)  # in minutes
    pomodoros_completed = Column(Integer, default=0)
    categories_breakdown = Column(JSON, nullable=True)
    productivity_score = Column(Float, nullable=True)
    
    # Relationships
    user = relationship("User")