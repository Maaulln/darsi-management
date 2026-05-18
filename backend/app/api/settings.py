"""Router untuk manajemen settings superadmin (API & Simulator)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from app.services.postgres import engine

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SimulatorRequest(BaseModel):
    enabled: bool


class IncomingAPIRequest(BaseModel):
    name: str
    endpoint: str
    metabase_url: str


@router.get("/simulator")
async def get_simulator_status() -> dict[str, bool]:
    """Mengambil status simulator aktif/nonaktif."""
    try:
        with engine.connect() as conn:
            val = conn.execute(
                text("SELECT value FROM darsi_settings WHERE key = 'simulator_enabled'")
            ).scalar()
            return {"enabled": val == "true"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.post("/simulator")
async def set_simulator_status(payload: SimulatorRequest) -> dict[str, object]:
    """Mengubah status simulator aktif/nonaktif."""
    try:
        val_str = "true" if payload.enabled else "false"
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO darsi_settings (key, value)
                    VALUES ('simulator_enabled', :val)
                    ON CONFLICT (key) DO UPDATE SET value = :val
                """),
                {"val": val_str}
            )
            conn.commit()
            return {"status": "ok", "enabled": payload.enabled}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/incoming-apis")
async def list_incoming_apis() -> dict[str, list[dict[str, object]]]:
    """Daftar semua API masuk dinamis yang dibuat superadmin."""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT id, name, endpoint, metabase_url, created_at FROM darsi_incoming_apis ORDER BY id ASC")
            )
            apis = []
            for row in result:
                apis.append({
                    "id": row[0],
                    "name": row[1],
                    "endpoint": row[2],
                    "metabase_url": row[3],
                    "created_at": str(row[4])
                })
            return {"apis": apis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.post("/incoming-apis")
async def add_incoming_api(payload: IncomingAPIRequest) -> dict[str, str]:
    """Menambahkan API masuk dinamis baru."""
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO darsi_incoming_apis (name, endpoint, metabase_url)
                    VALUES (:name, :endpoint, :metabase_url)
                """),
                {
                    "name": payload.name,
                    "endpoint": payload.endpoint,
                    "metabase_url": payload.metabase_url
                }
            )
            conn.commit()
            return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.delete("/incoming-apis/{api_id}")
async def delete_incoming_api(api_id: int) -> dict[str, str]:
    """Menghapus API masuk dinamis berdasarkan ID."""
    try:
        with engine.connect() as conn:
            conn.execute(
                text("DELETE FROM darsi_incoming_apis WHERE id = :id"),
                {"id": api_id}
            )
            conn.commit()
            return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
