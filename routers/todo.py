from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
import crud, schemas
from database import SessionLocal
from typing import List, Optional
from datetime import datetime, timedelta
import csv
import io
import json

router = APIRouter(prefix="/todos", tags=["Todos"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============= TODO ENDPOINTS =============

@router.get("/", response_model=List[schemas.TodoResponse])
def read_todos(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    completed: Optional[bool] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = Query("created_at", regex="^(created_at|due_date|priority|title)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    include_archived: bool = False,
    db: Session = Depends(get_db)
):
    """Get all todos with optional filters and sorting"""
    return crud.get_todos(
        db, skip=skip, limit=limit, search=search, 
        completed=completed, priority=priority, category=category,
        status=status, sort_by=sort_by, sort_order=sort_order,
        include_archived=include_archived
    )

@router.post("/", response_model=schemas.TodoResponse)
def create_todo(todo: schemas.TodoCreate, db: Session = Depends(get_db)):
    """Create a new todo"""
    return crud.create_todo(db, todo)

@router.get("/{todo_id}", response_model=schemas.TodoResponse)
def read_todo(todo_id: int, db: Session = Depends(get_db)):
    """Get a specific todo by ID"""
    db_todo = crud.get_todo(db, todo_id)
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return db_todo

@router.put("/{todo_id}", response_model=schemas.TodoResponse)
def update_todo(todo_id: int, todo: schemas.TodoUpdate, db: Session = Depends(get_db)):
    """Update a todo"""
    db_todo = crud.update_todo(db, todo_id, todo)
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return db_todo

@router.delete("/{todo_id}")
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    """Delete a todo"""
    db_todo = crud.delete_todo(db, todo_id)
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": "Todo deleted successfully"}

# ============= TIMER ENDPOINTS =============

@router.post("/{todo_id}/timer/start", response_model=schemas.TodoResponse)
def start_todo_timer(todo_id: int, db: Session = Depends(get_db)):
    """Start timer for a todo"""
    db_todo = crud.start_timer(db, todo_id)
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return db_todo

@router.post("/{todo_id}/timer/stop", response_model=schemas.TodoResponse)
def stop_todo_timer(todo_id: int, db: Session = Depends(get_db)):
    """Stop timer for a todo"""
    db_todo = crud.stop_timer(db, todo_id)
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found or timer not running")
    return db_todo

@router.get("/{todo_id}/timer/status", response_model=schemas.TimerResponse)
def get_timer_status(todo_id: int, db: Session = Depends(get_db)):
    """Get timer status for a todo"""
    db_todo = crud.get_todo(db, todo_id)
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    elapsed_seconds = 0
    if db_todo.timer_started_at:
        elapsed_seconds = int((datetime.utcnow() - db_todo.timer_started_at).total_seconds())
    
    return {
        "todo_id": todo_id,
        "started_at": db_todo.timer_started_at,
        "is_running": db_todo.timer_started_at is not None,
        "elapsed_seconds": elapsed_seconds
    }

# ============= POMODORO ENDPOINTS =============

@router.post("/{todo_id}/pomodoro/complete", response_model=schemas.TodoResponse)
def complete_pomodoro(todo_id: int, db: Session = Depends(get_db)):
    """Mark a pomodoro as completed for a todo"""
    db_todo = crud.complete_pomodoro(db, todo_id)
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return db_todo

# ============= TEMPLATE ENDPOINTS =============

@router.get("/templates/list", response_model=List[schemas.TemplateResponse])
def get_templates(db: Session = Depends(get_db)):
    """Get all task templates"""
    return crud.get_templates(db)

@router.post("/{todo_id}/make-template")
def make_template(todo_id: int, template_name: str, db: Session = Depends(get_db)):
    """Convert a todo into a template"""
    db_todo = crud.create_template(db, todo_id, template_name)
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": f"Template '{template_name}' created successfully"}

@router.post("/templates/{template_id}/create", response_model=schemas.TodoResponse)
def create_from_template(template_id: int, db: Session = Depends(get_db)):
    """Create a new todo from a template"""
    db_todo = crud.create_from_template(db, template_id)
    if not db_todo:
        raise HTTPException(status_code=404, detail="Template not found")
    return db_todo

# ============= RECURRING TASK ENDPOINTS =============

@router.post("/{todo_id}/recurring/create-next", response_model=schemas.TodoResponse)
def create_next_recurring_instance(todo_id: int, db: Session = Depends(get_db)):
    """Create the next instance of a recurring task"""
    db_todo = crud.create_recurring_instance(db, todo_id)
    if not db_todo:
        raise HTTPException(status_code=400, detail="Cannot create recurring instance")
    return db_todo

# ============= COMMENT ENDPOINTS =============

@router.post("/comments/", response_model=schemas.CommentResponse)
def create_comment(comment: schemas.CommentCreate, db: Session = Depends(get_db)):
    """Add a comment to a todo"""
    return crud.create_comment(db, comment)

@router.get("/{todo_id}/comments/", response_model=List[schemas.CommentResponse])
def get_comments(todo_id: int, db: Session = Depends(get_db)):
    """Get all comments for a todo"""
    return crud.get_comments(db, todo_id)

# ============= ACTIVITY LOG ENDPOINTS =============

@router.get("/{todo_id}/activity/")
def get_activity_log(todo_id: int, db: Session = Depends(get_db)):
    """Get activity log for a todo"""
    activities = crud.get_activity_log(db, todo_id)
    return [
        {
            "id": activity.id,
            "action": activity.action,
            "details": json.loads(activity.details) if isinstance(activity.details, str) else activity.details,
            "timestamp": activity.timestamp,
            "user_id": activity.user_id
        }
        for activity in activities
    ]

# ============= STATS & ANALYTICS ENDPOINTS =============

@router.get("/stats/", response_model=schemas.StatsResponse)
def get_stats(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get comprehensive statistics"""
    return crud.get_todo_stats(db, user_id)

@router.get("/analytics/productivity-trends/", response_model=schemas.ProductivityTrend)
def get_productivity_trends(days: int = 7, user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get productivity trends over time"""
    return crud.get_productivity_trends(db, days, user_id)

@router.get("/analytics/time-by-category/")
def get_time_by_category(db: Session = Depends(get_db)):
    """Get time spent breakdown by category"""
    categories = crud.get_categories(db)
    result = {}
    
    for category in categories:
        todos = db.query(crud.models.Todo).filter(
            crud.models.Todo.category_id == category.id,
            crud.models.Todo.actual_duration.isnot(None)
        ).all()
        
        total_time = sum(todo.actual_duration or 0 for todo in todos)
        result[category.name] = total_time
    
    return result

# ============= BULK OPERATIONS =============

@router.post("/bulk/complete")
def bulk_complete_todos(operation: schemas.BulkOperation, db: Session = Depends(get_db)):
    """Mark multiple todos as completed"""
    updated = crud.bulk_update_todos(db, operation.todo_ids, {"status": schemas.StatusLevel.COMPLETED})
    return {"message": f"{updated} todos marked as completed"}

@router.post("/bulk/archive")
def bulk_archive_todos(operation: schemas.BulkOperation, db: Session = Depends(get_db)):
    """Archive multiple todos"""
    updated = crud.bulk_update_todos(db, operation.todo_ids, {"is_archived": True})
    return {"message": f"{updated} todos archived"}

@router.post("/bulk/delete")
def bulk_delete_todos(operation: schemas.BulkOperation, db: Session = Depends(get_db)):
    """Delete multiple todos"""
    for todo_id in operation.todo_ids:
        crud.delete_todo(db, todo_id)
    return {"message": f"{len(operation.todo_ids)} todos deleted"}

@router.post("/bulk/move")
def bulk_move_todos(operation: schemas.BulkOperation, category_id: int, db: Session = Depends(get_db)):
    """Move multiple todos to a new category"""
    updated = crud.bulk_update_todos(db, operation.todo_ids, {"category_id": category_id})
    return {"message": f"{updated} todos moved to new category"}

@router.post("/bulk/update")
def bulk_update(operation: schemas.BulkUpdateOperation, db: Session = Depends(get_db)):
    """Bulk update multiple todos with custom fields"""
    updated = crud.bulk_update_todos(db, operation.todo_ids, operation.updates)
    return {"message": f"{updated} todos updated"}

# ============= EXPORT ENDPOINTS =============

@router.get("/export/json")
def export_json(
    status: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Export todos as JSON"""
    todos = crud.get_todos(db, status=status, category=category, limit=10000)
    
    export_data = []
    for todo in todos:
        export_data.append({
            "id": todo.id,
            "title": todo.title,
            "description": todo.description,
            "status": todo.status.value if todo.status else None,
            "priority": todo.priority.value if todo.priority else None,
            "due_date": todo.due_date.isoformat() if todo.due_date else None,
            "category": todo.category.name if todo.category else None,
            "tags": [tag.name for tag in todo.tags],
            "created_at": todo.created_at.isoformat() if todo.created_at else None,
            "completed_at": todo.completed_at.isoformat() if todo.completed_at else None
        })
    
    return export_data

@router.get("/export/csv")
def export_csv(
    status: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Export todos as CSV"""
    todos = crud.get_todos(db, status=status, category=category, limit=10000)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "ID", "Title", "Description", "Status", "Priority", 
        "Due Date", "Category", "Tags", "Created At", "Completed At"
    ])
    
    # Write data
    for todo in todos:
        writer.writerow([
            todo.id,
            todo.title,
            todo.description or "",
            todo.status.value if todo.status else "",
            todo.priority.value if todo.priority else "",
            todo.due_date.isoformat() if todo.due_date else "",
            todo.category.name if todo.category else "",
            ", ".join([tag.name for tag in todo.tags]),
            todo.created_at.isoformat() if todo.created_at else "",
            todo.completed_at.isoformat() if todo.completed_at else ""
        ])
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=todos.csv"}
    )

@router.get("/export/ics")
def export_ics(db: Session = Depends(get_db)):
    """Export todos as ICS calendar format"""
    todos = crud.get_todos(db, limit=10000)
    
    ics_content = "BEGIN:VCALENDAR\n"
    ics_content += "VERSION:2.0\n"
    ics_content += "PRODID:-//Todo App//EN\n"
    
    for todo in todos:
        if todo.due_date:
            ics_content += "BEGIN:VEVENT\n"
            ics_content += f"UID:{todo.id}@todoapp.com\n"
            ics_content += f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\n"
            ics_content += f"DTSTART:{todo.due_date.strftime('%Y%m%dT%H%M%SZ')}\n"
            ics_content += f"SUMMARY:{todo.title}\n"
            if todo.description:
                ics_content += f"DESCRIPTION:{todo.description}\n"
            ics_content += f"STATUS:{'COMPLETED' if todo.status == crud.models.StatusLevel.COMPLETED else 'NEEDS-ACTION'}\n"
            ics_content += "END:VEVENT\n"
    
    ics_content += "END:VCALENDAR\n"
    
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=todos.ics"}
    )

# ============= CATEGORY & TAG ENDPOINTS =============

@router.get("/categories/", response_model=List[schemas.CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    """Get all categories"""
    return crud.get_categories(db)

@router.post("/categories/", response_model=schemas.CategoryResponse)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    """Create a new category"""
    return crud.create_category(db, category)

@router.get("/tags/", response_model=List[schemas.TagResponse])
def get_tags(db: Session = Depends(get_db)):
    """Get all tags"""
    return crud.get_tags(db)

@router.post("/tags/", response_model=schemas.TagResponse)
def create_tag(tag: schemas.TagCreate, db: Session = Depends(get_db)):
    """Create a new tag"""
    return crud.create_tag(db, tag)

# ============= SMART SUGGESTIONS =============

@router.get("/{todo_id}/suggestions/")
def get_smart_suggestions(todo_id: int, db: Session = Depends(get_db)):
    """Get AI-powered suggestions for task optimization"""
    todo = crud.get_todo(db, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    suggestions = []
    
    # Check if overdue
    if todo.due_date and todo.due_date < datetime.utcnow() and todo.status != crud.models.StatusLevel.COMPLETED:
        suggestions.append({
            "type": "warning",
            "message": "This task is overdue. Consider rescheduling or marking as high priority."
        })
    
    # Check if estimated duration is set
    if not todo.estimated_duration:
        suggestions.append({
            "type": "info",
            "message": "Set an estimated duration to better plan your day."
        })
    
    # Check dependencies
    if todo.dependencies:
        incomplete_deps = [d for d in todo.dependencies if d.status != crud.models.StatusLevel.COMPLETED]
        if incomplete_deps:
            suggestions.append({
                "type": "warning",
                "message": f"This task has {len(incomplete_deps)} incomplete dependencies."
            })
    
    # Suggest breaking down large tasks
    if todo.estimated_duration and todo.estimated_duration > 120:
        suggestions.append({
            "type": "tip",
            "message": "This task might benefit from being broken down into smaller subtasks."
        })
    
    return {"suggestions": suggestions}

# ============= DASHBOARD =============

@router.get("/dashboard/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Get comprehensive dashboard summary"""
    stats = crud.get_todo_stats(db)
    trends = crud.get_productivity_trends(db, days=7)
    
    # Get upcoming tasks
    upcoming = db.query(crud.models.Todo).filter(
        crud.models.Todo.due_date >= datetime.utcnow(),
        crud.models.Todo.status != crud.models.StatusLevel.COMPLETED
    ).order_by(crud.models.Todo.due_date).limit(5).all()
    
    # Get recent activity
    recent_activity = db.query(crud.models.ActivityLog).order_by(
        crud.models.ActivityLog.timestamp.desc()
    ).limit(10).all()
    
    return {
        "stats": stats,
        "trends": trends,
        "upcoming_tasks": [
            {
                "id": todo.id,
                "title": todo.title,
                "due_date": todo.due_date.isoformat(),
                "priority": todo.priority.value
            }
            for todo in upcoming
        ],
        "recent_activity": [
            {
                "action": activity.action,
                "details": json.loads(activity.details) if isinstance(activity.details, str) else activity.details,
                "timestamp": activity.timestamp.isoformat()
            }
            for activity in recent_activity
        ]
    }