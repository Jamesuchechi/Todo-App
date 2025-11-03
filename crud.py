from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, case
from datetime import datetime, timedelta
from typing import List
import models, schemas

def get_todos(db: Session, skip: int = 0, limit: int = 100, 
              search: str = None, completed: bool = None, priority: str = None,
              category: str = None, status: str = None, sort_by: str = "created_at",
              sort_order: str = "desc"):
    query = db.query(models.Todo).filter(models.Todo.parent_id == None)
    
    # Filters
    if search:
        query = query.filter(
            or_(
                models.Todo.title.ilike(f"%{search}%"),
                models.Todo.description.ilike(f"%{search}%"),
                models.Todo.notes.ilike(f"%{search}%")
            )
        )
    
    if completed is not None:
        status_filter = models.StatusLevel.COMPLETED if completed else models.StatusLevel.PENDING
        query = query.filter(models.Todo.status == status_filter)
    
    if priority:
        query = query.filter(models.Todo.priority == priority)
    
    if category:
        query = query.filter(models.Todo.category.has(name=category))
    
    if status:
        query = query.filter(models.Todo.status == status)
    
    # Sorting
    if sort_by == "due_date":
        order_field = models.Todo.due_date
    elif sort_by == "priority":
        priority_order = case(
            (models.Todo.priority == "urgent", 1),
            (models.Todo.priority == "high", 2),
            (models.Todo.priority == "medium", 3),
            (models.Todo.priority == "low", 4),
            else_=5
        )
        order_field = priority_order
    elif sort_by == "title":
        order_field = models.Todo.title
    else:  # created_at
        order_field = models.Todo.created_at
    
    if sort_order == "asc":
        query = query.order_by(order_field.asc())
    else:
        query = query.order_by(order_field.desc())
    
    return query.offset(skip).limit(limit).all()

def get_todo(db: Session, todo_id: int):
    return db.query(models.Todo).filter(models.Todo.id == todo_id).first()

def create_todo(db: Session, todo: schemas.TodoCreate):
    db_todo = models.Todo(**todo.dict(exclude={'tag_ids'}))
    
    if todo.tag_ids:
        tags = db.query(models.Tag).filter(models.Tag.id.in_(todo.tag_ids)).all()
        db_todo.tags = tags
    
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo

def update_todo(db: Session, todo_id: int, todo: schemas.TodoUpdate):
    db_todo = get_todo(db, todo_id)
    if not db_todo:
        return None
    
    update_data = todo.dict(exclude_unset=True, exclude={'tag_ids'})
    
    for key, value in update_data.items():
        setattr(db_todo, key, value)
    
    # Handle tags update
    if 'tag_ids' in todo.dict(exclude_unset=True):
        tag_ids = todo.dict(exclude_unset=True).get('tag_ids')
        if tag_ids is not None:
            tags = db.query(models.Tag).filter(models.Tag.id.in_(tag_ids)).all()
            db_todo.tags = tags
    
    # Update completed_at if status changed to completed
    if todo.status == schemas.StatusLevel.COMPLETED and db_todo.status != schemas.StatusLevel.COMPLETED:
        db_todo.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_todo)
    return db_todo

def delete_todo(db: Session, todo_id: int):
    db_todo = get_todo(db, todo_id)
    if db_todo:
        db.delete(db_todo)
        db.commit()
    return db_todo

def bulk_update_todos(db: Session, todo_ids: List[int], update_data: dict):
    db.query(models.Todo).filter(models.Todo.id.in_(todo_ids)).update(update_data, synchronize_session=False)
    db.commit()
    return len(todo_ids)

def get_todo_stats(db: Session):
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    
    total = db.query(models.Todo).count()
    completed = db.query(models.Todo).filter(models.Todo.status == models.StatusLevel.COMPLETED).count()
    pending = db.query(models.Todo).filter(models.Todo.status == models.StatusLevel.PENDING).count()
    in_progress = db.query(models.Todo).filter(models.Todo.status == models.StatusLevel.IN_PROGRESS).count()
    
    overdue = db.query(models.Todo).filter(
        and_(
            models.Todo.due_date < now,
            models.Todo.status != models.StatusLevel.COMPLETED
        )
    ).count()
    
    due_today = db.query(models.Todo).filter(
        and_(
            models.Todo.due_date >= today_start,
            models.Todo.due_date < today_start + timedelta(days=1),
            models.Todo.status != models.StatusLevel.COMPLETED
        )
    ).count()
    
    # Priority stats
    by_priority = {}
    for priority in models.PriorityLevel:
        count = db.query(models.Todo).filter(models.Todo.priority == priority).count()
        by_priority[priority.value] = count
    
    # Category stats
    by_category = {}
    categories = db.query(models.Category).all()
    for category in categories:
        count = db.query(models.Todo).filter(models.Todo.category_id == category.id).count()
        by_category[category.name] = count
    
    # Status stats
    by_status = {}
    for status in models.StatusLevel:
        count = db.query(models.Todo).filter(models.Todo.status == status).count()
        by_status[status.value] = count
    
    completion_rate = (completed / total * 100) if total > 0 else 0
    
    # Average completion time
    avg_completion = db.query(
        func.avg(func.extract('epoch', models.Todo.completed_at - models.Todo.created_at))
    ).filter(models.Todo.completed_at.isnot(None)).scalar()
    
    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "in_progress": in_progress,
        "overdue": overdue,
        "due_today": due_today,
        "by_priority": by_priority,
        "by_category": by_category,
        "by_status": by_status,
        "completion_rate": round(completion_rate, 2),
        "average_completion_time": round(avg_completion / 3600, 2) if avg_completion else None  # in hours
    }

def get_categories(db: Session):
    return db.query(models.Category).all()

def get_tags(db: Session):
    return db.query(models.Tag).all()

def create_category(db: Session, category: schemas.CategoryCreate):
    db_category = models.Category(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

def create_tag(db: Session, tag: schemas.TagCreate):
    db_tag = models.Tag(**tag.dict())
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag