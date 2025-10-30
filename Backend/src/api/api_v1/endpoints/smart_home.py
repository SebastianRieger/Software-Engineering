from fastapi import APIRouter

router = APIRouter()

@router.get("/devices")
async def get_devices():
    """
    Get list of smart home devices (placeholder)
    """
    return {"message": "Smart home functionality coming soon"}