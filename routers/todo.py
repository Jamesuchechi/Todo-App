from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import crud, schemas
from database import SessionLocal
from typing import List, Optional

router = APIRouter(prefix="/todos", tags=["Todos"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
    db: Session = Depends(get_db)
):
    return crud.get_todos(
        db, skip=skip, limit=limit, search=search, 
        completed=completed, priority=priority, category=category,
        status=status, sort_by=sort_by, sort_order=sort_order
    )

@router.post("/", response_model=schemas.TodoResponse)
def create_todo(todo: schemas.TodoCreate, db: Session = Depends(get_db)):
    return crud.create_todo(db, todo)

@router.get("/{todo_id}", response_model=schemas.TodoResponse)
def read_todo(todo_id: int, db: Session = Depends(get_db)):
    db_todo = crud.get_todo(db, todo_id)
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return db_todo

@router.put("/{todo_id}", response_model=schemas.TodoResponse)
def update_todo(todo_id: int, todo: schemas.TodoUpdate, db: Session = Depends(get_db)):
    db_todo = crud.update_todo(db, todo_id, todo)
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return db_todo

@router.delete("/{todo_id}")
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    db_todo = crud.delete_todo(db, todo_id)
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": "Todo deleted successfully"}

@router.get("/stats/", response_model=schemas.StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    return crud.get_todo_stats(db)

@router.get("/categories/", response_model=List[schemas.CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    return crud.get_categories(db)

@router.get("/tags/", response_model=List[schemas.TagResponse])
def get_tags(db: Session = Depends(get_db)):
    return crud.get_tags(db)

@router.post("/categories/", response_model=schemas.CategoryResponse)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    return crud.create_category(db, category)

@router.post("/tags/", response_model=schemas.TagResponse)
def create_tag(tag: schemas.TagCreate, db: Session = Depends(get_db)):
    return crud.create_tag(db, tag)

@router.post("/bulk/complete")
def bulk_complete_todos(operation: schemas.BulkOperation, db: Session = Depends(get_db)):
    updated = crud.bulk_update_todos(db, operation.todo_ids, {"status": schemas.StatusLevel.COMPLETED})
    return {"message": f"{updated} todos marked as completed"}

@router.post("/bulk/archive")
def bulk_archive_todos(operation: schemas.BulkOperation, db: Session = Depends(get_db)):
    updated = crud.bulk_update_todos(db, operation.todo_ids, {"is_archived": True})
    return {"message": f"{updated} todos archived"}

@router.post("/bulk/delete")
def bulk_delete_todos(operation: schemas.BulkOperation, db: Session = Depends(get_db)):
    for todo_id in operation.todo_ids:
        crud.delete_todo(db, todo_id)
    return {"message": f"{len(operation.todo_ids)} todos deleted"}

@router.post("/bulk/move")
def bulk_move_todos(operation: schemas.BulkOperation, category_id: int, db: Session = Depends(get_db)):
    updated = crud.bulk_update_todos(db, operation.todo_ids, {"category_id": category_id})
    return {"message": f"{updated} todos moved to new category"}