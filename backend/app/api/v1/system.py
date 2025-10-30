from fastapi import APIRouter

router = APIRouter()


@router.get("/system/status")
async def system_status():
    return {"uptime_seconds": 12345, "cpu_percent": 12.3, "mem_percent": 42.1}
