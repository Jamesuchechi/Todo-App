from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import engine, Base
from routers import todo

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Uchechi`s Todo App",
    description="A robust task management application made just for You",
    version="1.0.0"
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")

# Include routers
app.include_router(todo.router)

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}