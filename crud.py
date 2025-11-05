from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, case, desc
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import models, schemas
import json

# ============= TODO CRUD =============

def get_todos(db: Session, skip: int = 0, limit: int = 100, 
              search: str = None, completed: bool = None, priority: str = None,
              category: str = None, status: str = None, sort_by: str = "created_at",
              sort_order: str = "desc", include_archived: bool = False):
    query = db.query(models.Todo).filter(models.Todo.parent_id == None)
    
    # Filter archived
    if not include_archived:
        query = query.filter(models.Todo.is_archived == False)
    
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
        priority_enum = getattr(models.PriorityLevel, priority.upper(), None)
        if priority_enum:
            query = query.filter(models.Todo.priority == priority_enum)
    
    if category:
        query = query.filter(models.Todo.category.has(name=category))
    
    if status:
        status_enum = getattr(models.StatusLevel, status.upper(), None)
        if status_enum:
            query = query.filter(models.Todo.status == status_enum)
    
    # Sorting
    if sort_by == "due_date":
        order_field = models.Todo.due_date
    elif sort_by == "priority":
        priority_order = case(
            (models.Todo.priority == models.PriorityLevel.URGENT, 1),
            (models.Todo.priority == models.PriorityLevel.HIGH, 2),
            (models.Todo.priority == models.PriorityLevel.MEDIUM, 3),
            (models.Todo.priority == models.PriorityLevel.LOW, 4),
            else_=5
        )
        order_field = priority_order
    elif sort_by == "title":
        order_field = models.Todo.title
    else:
        order_field = models.Todo.created_at
    
    if sort_order == "asc":
        query = query.order_by(order_field.asc())
    else:
        query = query.order_by(order_field.desc())

        # Eager load relationships to avoid N+1 queries
    query = query.options(
        joinedload(models.Todo.category),
        joinedload(models.Todo.tags),
        joinedload(models.Todo.subtasks).joinedload(models.Todo.category),
        joinedload(models.Todo.dependencies),
        joinedload(models.Todo.assignees),
        joinedload(models.Todo.comments)
    )
    
    todos = query.offset(skip).limit(limit).all()

    return todos

def get_todo(db: Session, todo_id: int):
    todo = db.query(models.Todo).options(
        joinedload(models.Todo.category),
        joinedload(models.Todo.tags),
        joinedload(models.Todo.subtasks).joinedload(models.Todo.category),
        joinedload(models.Todo.dependencies),
        joinedload(models.Todo.assignees),
        joinedload(models.Todo.comments)
    ).filter(models.Todo.id == todo_id).first()
    return todo

def create_todo(db: Session, todo: schemas.TodoCreate, user_id: Optional[int] = None):
    todo_data = todo.dict(exclude={'tag_ids', 'assignee_ids', 'dependency_ids'})
    
    # Handle enum conversion
    if 'status' in todo_data and isinstance(todo_data['status'], str):
        todo_data['status'] = getattr(models.StatusLevel, todo_data['status'].upper())
    
    if 'priority' in todo_data and isinstance(todo_data['priority'], str):
        todo_data['priority'] = getattr(models.PriorityLevel, todo_data['priority'].upper())
    
    if 'recurrence_pattern' in todo_data and isinstance(todo_data['recurrence_pattern'], str):
        todo_data['recurrence_pattern'] = getattr(models.RecurrencePattern, todo_data['recurrence_pattern'].upper())
    
    # Clean up None values
    if 'category_id' in todo_data and todo_data['category_id'] is None:
        del todo_data['category_id']
    
    # Set creator
    if user_id:
        todo_data['created_by'] = user_id
    
    db_todo = models.Todo(**todo_data)
    
    # Handle relationships
    if todo.tag_ids:
        tags = db.query(models.Tag).filter(models.Tag.id.in_(todo.tag_ids)).all()
        db_todo.tags = tags
    
    if todo.assignee_ids:
        assignees = db.query(models.User).filter(models.User.id.in_(todo.assignee_ids)).all()
        db_todo.assignees = assignees
    
    if todo.dependency_ids:
        dependencies = db.query(models.Todo).filter(models.Todo.id.in_(todo.dependency_ids)).all()
        db_todo.dependencies = dependencies
    
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)

        
    # Store the ID before expunging
    todo_id = db_todo.id
    
    # Expunge from session to clear any lazy-loaded proxies
    db.expunge(db_todo)
    
    # Ensure all relationships are loaded
    db_todo = get_todo(db, todo_id)

    # Log activity
    log_activity(db, todo_id, user_id, "created", {"title": db_todo.title})
    
    return db_todo

def update_todo(db: Session, todo_id: int, todo: schemas.TodoUpdate, user_id: Optional[int] = None):
    db_todo = get_todo(db, todo_id)
    if not db_todo:
        return None
    
    update_data = todo.dict(exclude_unset=True, exclude={'tag_ids', 'assignee_ids', 'dependency_ids'})
    
    # Track changes for activity log
    changes = {}
    
    # Handle enum conversion
    if 'status' in update_data and isinstance(update_data['status'], str):
        update_data['status'] = getattr(models.StatusLevel, update_data['status'].upper())
    
    if 'priority' in update_data and isinstance(update_data['priority'], str):
        update_data['priority'] = getattr(models.PriorityLevel, update_data['priority'].upper())
    
    if 'recurrence_pattern' in update_data and isinstance(update_data['recurrence_pattern'], str):
        update_data['recurrence_pattern'] = getattr(models.RecurrencePattern, update_data['recurrence_pattern'].upper())
    
    for key, value in update_data.items():
        old_value = getattr(db_todo, key)
        if old_value != value:
            changes[key] = {"old": str(old_value), "new": str(value)}
        setattr(db_todo, key, value)
    
    # Handle relationships
    if 'tag_ids' in todo.dict(exclude_unset=True):
        tag_ids = todo.dict(exclude_unset=True).get('tag_ids')
        if tag_ids is not None:
            tags = db.query(models.Tag).filter(models.Tag.id.in_(tag_ids)).all()
            db_todo.tags = tags
    
    if 'assignee_ids' in todo.dict(exclude_unset=True):
        assignee_ids = todo.dict(exclude_unset=True).get('assignee_ids')
        if assignee_ids is not None:
            assignees = db.query(models.User).filter(models.User.id.in_(assignee_ids)).all()
            db_todo.assignees = assignees
    
    if 'dependency_ids' in todo.dict(exclude_unset=True):
        dependency_ids = todo.dict(exclude_unset=True).get('dependency_ids')
        if dependency_ids is not None:
            dependencies = db.query(models.Todo).filter(models.Todo.id.in_(dependency_ids)).all()
            db_todo.dependencies = dependencies
    
    # Update completed_at if status changed to completed
    if 'status' in update_data and update_data['status'] == models.StatusLevel.COMPLETED:
        if db_todo.completed_at is None:
            db_todo.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_todo)
    
    # Ensure relationships are loaded
    if db_todo.category_id:
        db.refresh(db_todo, ['category'])
    db.refresh(db_todo, ['tags', 'subtasks', 'dependencies', 'assignees', 'comments'])
    
    # Log activity
    if changes:
        log_activity(db, todo_id, user_id, "updated", changes)
    
    return db_todo

def delete_todo(db: Session, todo_id: int, user_id: Optional[int] = None):
    db_todo = get_todo(db, todo_id)
    if db_todo:
        title = db_todo.title
        db.delete(db_todo)
        db.commit()
        log_activity(db, todo_id, user_id, "deleted", {"title": title})
    return db_todo

def bulk_update_todos(db: Session, todo_ids: List[int], update_data: dict, user_id: Optional[int] = None):
    # Handle enum conversion
    if 'status' in update_data and isinstance(update_data['status'], str):
        update_data['status'] = getattr(models.StatusLevel, update_data['status'].upper())
    
    if 'priority' in update_data and isinstance(update_data['priority'], str):
        update_data['priority'] = getattr(models.PriorityLevel, update_data['priority'].upper())
    
    db.query(models.Todo).filter(models.Todo.id.in_(todo_ids)).update(update_data, synchronize_session=False)
    db.commit()
    
    # Log bulk activity
    for todo_id in todo_ids:
        log_activity(db, todo_id, user_id, "bulk_updated", update_data)
    
    return len(todo_ids)

# ============= TIMER FUNCTIONS =============

def start_timer(db: Session, todo_id: int):
    db_todo = get_todo(db, todo_id)
    if not db_todo:
        return None
    
    db_todo.timer_started_at = datetime.utcnow()
    db_todo.status = models.StatusLevel.IN_PROGRESS
    db.commit()
    db.refresh(db_todo)
    return db_todo

def stop_timer(db: Session, todo_id: int):
    db_todo = get_todo(db, todo_id)
    if not db_todo or not db_todo.timer_started_at:
        return None
    
    # Calculate duration
    duration_seconds = int((datetime.utcnow() - db_todo.timer_started_at).total_seconds())
    
    # Add to time entries
    time_entries = db_todo.time_entries or []
    if isinstance(time_entries, str):
        time_entries = json.loads(time_entries)
    
    time_entries.append({
        "start": db_todo.timer_started_at.isoformat(),
        "end": datetime.utcnow().isoformat(),
        "duration": duration_seconds
    })
    
    db_todo.time_entries = json.dumps(time_entries)
    
    # Update actual duration
    total_duration_minutes = sum(entry['duration'] for entry in time_entries) // 60
    db_todo.actual_duration = total_duration_minutes
    
    db_todo.timer_started_at = None
    db.commit()
    db.refresh(db_todo)
    return db_todo

# ============= POMODORO FUNCTIONS =============

def complete_pomodoro(db: Session, todo_id: int):
    db_todo = get_todo(db, todo_id)
    if not db_todo:
        return None
    
    db_todo.pomodoro_count += 1
    db.commit()
    db.refresh(db_todo)
    return db_todo

# ============= TEMPLATE FUNCTIONS =============

def create_template(db: Session, todo_id: int, template_name: str):
    db_todo = get_todo(db, todo_id)
    if not db_todo:
        return None
    
    db_todo.is_template = True
    db_todo.template_name = template_name
    db.commit()
    db.refresh(db_todo)
    return db_todo

def get_templates(db: Session):
    templates = db.query(models.Todo).filter(models.Todo.is_template == True).all()
    for template in templates:
        db.refresh(template, ['category', 'tags'])
    return templates

def create_from_template(db: Session, template_id: int, user_id: Optional[int] = None):
    template = get_todo(db, template_id)
    if not template or not template.is_template:
        return None
    
    # Create new todo from template
    new_todo_data = {
        "title": template.title,
        "description": template.description,
        "priority": template.priority,
        "estimated_duration": template.estimated_duration,
        "category_id": template.category_id,
        "notes": template.notes,
        "is_template": False,
        "created_by": user_id
    }
    
    new_todo = models.Todo(**new_todo_data)
    
    # Copy tags
    if template.tags:
        new_todo.tags = template.tags
    
    db.add(new_todo)
    db.commit()
    db.refresh(new_todo)
    db.refresh(new_todo, ['category', 'tags', 'subtasks', 'dependencies', 'assignees', 'comments'])
    
    return new_todo

# ============= RECURRING TASK FUNCTIONS =============

def create_recurring_instance(db: Session, original_todo_id: int):
    original = get_todo(db, original_todo_id)
    if not original or original.recurrence_pattern == models.RecurrencePattern.NONE:
        return None
    
    # Calculate next due date
    if original.due_date:
        if original.recurrence_pattern == models.RecurrencePattern.DAILY:
            next_due = original.due_date + timedelta(days=1)
        elif original.recurrence_pattern == models.RecurrencePattern.WEEKLY:
            next_due = original.due_date + timedelta(weeks=1)
        elif original.recurrence_pattern == models.RecurrencePattern.MONTHLY:
            next_due = original.due_date + timedelta(days=30)
        elif original.recurrence_pattern == models.RecurrencePattern.YEARLY:
            next_due = original.due_date + timedelta(days=365)
        else:
            next_due = None
        
        # Check if we should create instance
        if original.recurrence_end_date and next_due > original.recurrence_end_date:
            return None
        
        # Create new instance
        new_todo_data = {
            "title": original.title,
            "description": original.description,
            "priority": original.priority,
            "status": models.StatusLevel.PENDING,
            "due_date": next_due,
            "category_id": original.category_id,
            "estimated_duration": original.estimated_duration,
            "notes": original.notes,
            "original_todo_id": original_todo_id,
            "recurrence_pattern": original.recurrence_pattern,
            "recurrence_end_date": original.recurrence_end_date
        }
        
        new_todo = models.Todo(**new_todo_data)
        
        # Copy relationships
        if original.tags:
            new_todo.tags = original.tags
        if original.assignees:
            new_todo.assignees = original.assignees
        
        db.add(new_todo)
        db.commit()
        db.refresh(new_todo)
        db.refresh(new_todo, ['category', 'tags', 'subtasks', 'dependencies', 'assignees', 'comments'])
        
        return new_todo
    
    return None

# ============= STATS FUNCTIONS =============

def get_todo_stats(db: Session, user_id: Optional[int] = None):
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    
    query = db.query(models.Todo)
    if user_id:
        query = query.filter(models.Todo.created_by == user_id)
    
    total = query.count()
    completed = query.filter(models.Todo.status == models.StatusLevel.COMPLETED).count()
    pending = query.filter(models.Todo.status == models.StatusLevel.PENDING).count()
    in_progress = query.filter(models.Todo.status == models.StatusLevel.IN_PROGRESS).count()
    
    overdue = query.filter(
        and_(
            models.Todo.due_date < now,
            models.Todo.status != models.StatusLevel.COMPLETED
        )
    ).count()
    
    due_today = query.filter(
        and_(
            models.Todo.due_date >= today_start,
            models.Todo.due_date < today_start + timedelta(days=1),
            models.Todo.status != models.StatusLevel.COMPLETED
        )
    ).count()
    
    # Priority stats
    by_priority = {}
    for priority in models.PriorityLevel:
        count = query.filter(models.Todo.priority == priority).count()
        by_priority[priority.value] = count
    
    # Category stats
    by_category = {}
    categories = db.query(models.Category).all()
    for category in categories:
        count = query.filter(models.Todo.category_id == category.id).count()
        by_category[category.name] = count
    
    # Status stats
    by_status = {}
    for status in models.StatusLevel:
        count = query.filter(models.Todo.status == status).count()
        by_status[status.value] = count
    
    completion_rate = (completed / total * 100) if total > 0 else 0
    
    # Average completion time
    avg_completion = db.query(
        func.avg(func.extract('epoch', models.Todo.completed_at - models.Todo.created_at))
    ).filter(models.Todo.completed_at.isnot(None)).scalar()
    
    # Total time tracked
    todos_with_time = query.filter(models.Todo.actual_duration.isnot(None)).all()
    total_time_tracked = sum(todo.actual_duration or 0 for todo in todos_with_time)
    
    # Total pomodoros
    total_pomodoros = sum(todo.pomodoro_count or 0 for todo in query.all())
    
    # Streak calculation (consecutive days with completed tasks)
    streak_days = calculate_streak(db, user_id)
    
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
        "average_completion_time": round(avg_completion / 3600, 2) if avg_completion else None,
        "total_time_tracked": total_time_tracked,
        "pomodoros_completed": total_pomodoros,
        "streak_days": streak_days
    }

def calculate_streak(db: Session, user_id: Optional[int] = None):
    query = db.query(models.Todo).filter(
        models.Todo.status == models.StatusLevel.COMPLETED,
        models.Todo.completed_at.isnot(None)
    )
    
    if user_id:
        query = query.filter(models.Todo.created_by == user_id)
    
    completed_todos = query.order_by(desc(models.Todo.completed_at)).all()
    
    if not completed_todos:
        return 0
    
    streak = 0
    current_date = datetime.utcnow().date()
    
    for todo in completed_todos:
        todo_date = todo.completed_at.date()
        if todo_date == current_date or todo_date == current_date - timedelta(days=streak):
            if todo_date == current_date - timedelta(days=streak):
                streak += 1
                current_date = todo_date
        else:
            break
    
    return streak

# ============= ANALYTICS FUNCTIONS =============

def get_productivity_trends(db: Session, days: int = 7, user_id: Optional[int] = None):
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    labels = []
    completed = []
    created = []
    time_spent = []
    
    for i in range(days):
        date = start_date + timedelta(days=i)
        date_start = datetime(date.year, date.month, date.day)
        date_end = date_start + timedelta(days=1)
        
        query = db.query(models.Todo)
        if user_id:
            query = query.filter(models.Todo.created_by == user_id)
        
        # Completed tasks
        completed_count = query.filter(
            and_(
                models.Todo.completed_at >= date_start,
                models.Todo.completed_at < date_end
            )
        ).count()
        
        # Created tasks
        created_count = query.filter(
            and_(
                models.Todo.created_at >= date_start,
                models.Todo.created_at < date_end
            )
        ).count()
        
        # Time spent
        todos_on_date = query.filter(
            and_(
                models.Todo.completed_at >= date_start,
                models.Todo.completed_at < date_end,
                models.Todo.actual_duration.isnot(None)
            )
        ).all()
        
        time_on_date = sum(todo.actual_duration or 0 for todo in todos_on_date)
        
        labels.append(date.strftime("%m/%d"))
        completed.append(completed_count)
        created.append(created_count)
        time_spent.append(time_on_date)
    
    return {
        "labels": labels,
        "completed": completed,
        "created": created,
        "time_spent": time_spent
    }

# ============= COMMENT FUNCTIONS =============

def create_comment(db: Session, comment: schemas.CommentCreate):
    db_comment = models.Comment(**comment.dict())
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

def get_comments(db: Session, todo_id: int):
    return db.query(models.Comment).filter(models.Comment.todo_id == todo_id).all()

# ============= ACTIVITY LOG FUNCTIONS =============

def log_activity(db: Session, todo_id: int, user_id: Optional[int], action: str, details: Dict[str, Any]):
    activity = models.ActivityLog(
        todo_id=todo_id,
        user_id=user_id,
        action=action,
        details=json.dumps(details)
    )
    db.add(activity)
    db.commit()
    return activity

def get_activity_log(db: Session, todo_id: int):
    return db.query(models.ActivityLog).filter(models.ActivityLog.todo_id == todo_id).order_by(desc(models.ActivityLog.timestamp)).all()

# ============= CATEGORY & TAG FUNCTIONS =============

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

# ============= USER FUNCTIONS =============

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()