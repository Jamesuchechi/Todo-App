from pydantic import BaseModel, validator, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class PriorityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class StatusLevel(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class RecurrencePattern(str, Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

# User Schemas
class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    avatar_url: Optional[str] = None
    is_active: bool
    theme: str = "light"
    notification_enabled: bool = True
    created_at: datetime
    
    class Config:
        from_attributes = True

# Tag Schemas
class TagBase(BaseModel):
    name: str
    color: Optional[str] = "#6B7280"

class TagCreate(TagBase):
    pass

class TagResponse(TagBase):
    id: int
    
    class Config:
        from_attributes = True

# Category Schemas
class CategoryBase(BaseModel):
    name: str
    color: Optional[str] = "#6B7280"
    icon: Optional[str] = "fa-folder"

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    
    class Config:
        from_attributes = True

# Comment Schemas
class CommentBase(BaseModel):
    content: str

class CommentCreate(CommentBase):
    todo_id: int
    user_id: Optional[int] = None

class CommentResponse(CommentBase):
    id: int
    todo_id: int
    user_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    user: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True

# Time Entry Schema
class TimeEntry(BaseModel):
    start: datetime
    end: Optional[datetime] = None
    duration: int = 0  # in seconds

# Attachment Schema
class Attachment(BaseModel):
    name: str
    url: str
    size: int
    type: str

# Todo Schemas
class TodoBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: StatusLevel = StatusLevel.PENDING
    priority: PriorityLevel = PriorityLevel.MEDIUM
    due_date: Optional[datetime] = None
    category_id: Optional[int] = None
    estimated_duration: Optional[int] = None
    notes: Optional[str] = None
    parent_id: Optional[int] = None
    recurrence_pattern: RecurrencePattern = RecurrencePattern.NONE
    recurrence_end_date: Optional[datetime] = None
    is_template: bool = False
    template_name: Optional[str] = None
    reminder_datetime: Optional[datetime] = None
    pomodoro_target: Optional[int] = None

class TodoCreate(TodoBase):
    tag_ids: Optional[List[int]] = None
    assignee_ids: Optional[List[int]] = None
    dependency_ids: Optional[List[int]] = None

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[StatusLevel] = None
    priority: Optional[PriorityLevel] = None
    due_date: Optional[datetime] = None
    category_id: Optional[int] = None
    is_archived: Optional[bool] = None
    estimated_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    notes: Optional[str] = None
    tag_ids: Optional[List[int]] = None
    assignee_ids: Optional[List[int]] = None
    dependency_ids: Optional[List[int]] = None
    recurrence_pattern: Optional[RecurrencePattern] = None
    recurrence_end_date: Optional[datetime] = None
    reminder_datetime: Optional[datetime] = None
    pomodoro_target: Optional[int] = None

class TodoResponse(TodoBase):
    id: int
    is_archived: bool
    actual_duration: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    category: Optional[CategoryResponse] = None
    tags: List[TagResponse] = []
    subtasks: List['TodoResponse'] = []
    dependencies: List['TodoResponse'] = []
    assignees: List[UserResponse] = []
    comments: List[CommentResponse] = []
    time_entries: Optional[List[Dict[str, Any]]] = None
    timer_started_at: Optional[datetime] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    pomodoro_count: int = 0
    pomodoro_target: Optional[int] = None
    created_by: Optional[int] = None
    
    @validator('subtasks', 'dependencies', 'assignees', 'comments', pre=True, always=True)
    def ensure_list(cls, v):
        return v if v is not None else []
    
    @validator('time_entries', 'attachments', pre=True, always=True)
    def ensure_json_list(cls, v):
        return v if v is not None else []
    
    class Config:
        from_attributes = True

# Notification Schemas
class NotificationBase(BaseModel):
    title: str
    message: str

class NotificationCreate(NotificationBase):
    user_id: int
    todo_id: Optional[int] = None

class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    todo_id: Optional[int]
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Analytics Schemas
class AnalyticsResponse(BaseModel):
    date: datetime
    tasks_completed: int
    tasks_created: int
    total_time_spent: int
    pomodoros_completed: int
    categories_breakdown: Optional[Dict[str, int]]
    productivity_score: Optional[float]
    
    class Config:
        from_attributes = True

class ProductivityTrend(BaseModel):
    labels: List[str]
    completed: List[int]
    created: List[int]
    time_spent: List[int]

# Stats Schemas
class StatsResponse(BaseModel):
    total: int
    completed: int
    pending: int
    in_progress: int
    overdue: int
    due_today: int
    by_priority: dict
    by_category: dict
    by_status: dict
    completion_rate: float
    average_completion_time: Optional[float]
    total_time_tracked: Optional[int] = 0
    pomodoros_completed: Optional[int] = 0
    streak_days: Optional[int] = 0

# Bulk Operation Schemas
class BulkOperation(BaseModel):
    todo_ids: List[int]

class BulkUpdateOperation(BaseModel):
    todo_ids: List[int]
    updates: Dict[str, Any]

# Timer Schemas
class TimerStart(BaseModel):
    todo_id: int

class TimerStop(BaseModel):
    todo_id: int

class TimerResponse(BaseModel):
    todo_id: int
    started_at: Optional[datetime]
    is_running: bool
    elapsed_seconds: Optional[int] = 0

# Template Schemas
class TemplateCreate(BaseModel):
    template_name: str
    todo_id: int

class TemplateResponse(BaseModel):
    id: int
    template_name: str
    title: str
    description: Optional[str]
    priority: PriorityLevel
    estimated_duration: Optional[int]
    category_id: Optional[int]
    tags: List[TagResponse] = []
    
    class Config:
        from_attributes = True

# Export Schema
class ExportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    ICS = "ics"

class ExportRequest(BaseModel):
    format: ExportFormat
    filter_status: Optional[str] = None
    filter_category: Optional[str] = None

TodoResponse.model_rebuild()