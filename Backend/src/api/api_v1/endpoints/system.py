from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_system_status():
    """
    Get system status (placeholder)
    """
    return {
        "status": "running",
        "version": "0.1.0"
    }