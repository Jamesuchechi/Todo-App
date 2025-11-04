from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import todo
import os

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Ultimate Todo Manager",
    description="A comprehensive task management application with advanced features",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create static directory if it doesn't exist
if not os.path.exists("static"):
    os.makedirs("static")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    """Serve the main application"""
    return FileResponse("static/index.html")

# Include routers
app.include_router(todo.router)

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "features": [
            "Task Management",
            "Time Tracking",
            "Pomodoro Timer",
            "Recurring Tasks",
            "Task Templates",
            "Comments & Activity Log",
            "Analytics & Trends",
            "Export (JSON, CSV, ICS)",
            "Smart Suggestions",
            "Bulk Operations",
            "Task Dependencies"
        ]
    }

@app.get("/api/info")
def api_info():
    """Get API information"""
    return {
        "name": "Ultimate Todo Manager API",
        "version": "2.0.0",
        "endpoints": {
            "todos": "/todos/",
            "stats": "/todos/stats/",
            "analytics": "/todos/analytics/productivity-trends/",
            "templates": "/todos/templates/list",
            "export": {
                "json": "/todos/export/json",
                "csv": "/todos/export/csv",
                "ics": "/todos/export/ics"
            },
            "timer": {
                "start": "/todos/{todo_id}/timer/start",
                "stop": "/todos/{todo_id}/timer/stop",
                "status": "/todos/{todo_id}/timer/status"
            },
            "dashboard": "/todos/dashboard/summary"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)