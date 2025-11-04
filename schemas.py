from pydantic import BaseModel, validator
from typing import List, Optional
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

class TagBase(BaseModel):
    name: str
    color: Optional[str] = "#6B7280"

class TagCreate(TagBase):
    pass

class TagResponse(TagBase):
    id: int
    
    class Config:
        from_attributes = True

class CategoryBase(BaseModel):
    name: str
    color: Optional[str] = "#6B7280"

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    
    class Config:
        from_attributes = True

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

class TodoCreate(TodoBase):
    tag_ids: Optional[List[int]] = None

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
    
    @validator('subtasks', pre=True, always=True)
    def ensure_subtasks_list(cls, v):
        return v if v is not None else []
    
    class Config:
        from_attributes = True

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

class BulkOperation(BaseModel):
    todo_ids: List[int]


TodoResponse.model_rebuild()