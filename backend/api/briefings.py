import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from backend.api.core import OUTPUT_DIR, datetime

router = APIRouter()

@router.get("/api/briefings")
def list_briefings():
    """Lists generated briefings saved in output directory."""
    briefings = []
    if os.path.exists(OUTPUT_DIR):
        for filename in os.listdir(OUTPUT_DIR):
            if filename.endswith(".md"):
                filepath = os.path.join(OUTPUT_DIR, filename)
                stat = os.stat(filepath)
                briefings.append({
                    "name": filename,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
    return sorted(briefings, key=lambda x: x["created_at"], reverse=True)

@router.get("/api/briefings/{filename}")
def get_briefing(filename: str):
    """Serves the briefing file content."""
    filename = os.path.basename(filename)
    filepath = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="text/markdown", filename=filename)
    else:
        raise HTTPException(status_code=404, detail="Briefing file not found")
