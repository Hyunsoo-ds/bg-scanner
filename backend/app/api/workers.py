from fastapi import APIRouter
from app.workers.celery_app import celery_app

router = APIRouter()

@router.get("")
def get_worker_status():
    inspect_opts = celery_app.control.inspect()
    
    if not inspect_opts:
        return {"status": "error", "message": "Could not connect to Celery task queue."}
        
    try:
        active = inspect_opts.active() or {}
        reserved = inspect_opts.reserved() or {}
        scheduled = inspect_opts.scheduled() or {}
        stats = inspect_opts.stats() or {}
        
        return {
            "status": "success",
            "data": {
                "active": active,
                "reserved": reserved,
                "scheduled": scheduled,
                "stats": stats
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
