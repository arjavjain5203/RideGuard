# Removed old static check_triggers. Implementing asyncio worker.
import asyncio
import logging
from app.database import SessionLocal
from app.models import User, Zone
from app.schemas import TriggerSimulateRequest
from app.routers.triggers import check_zone_triggers

# Basic Observability (Part 19)
logger = logging.getLogger("trigger_monitor")
logger.setLevel(logging.INFO)

async def start_monitor_loop():
    """Background worker that runs every 15 minutes, loops over zones, runs checks."""
    logger.info("Starting automated trigger monitor loop.")
    while True:
        try:
            db = SessionLocal()
            try:
                zones = db.query(Zone).all()
                zone_names = [z.name for z in zones]
            finally:
                db.close()

            # If no zones, use defaults
            if not zone_names:
                zone_names = ["Koramangala", "Indiranagar", "HSR Layout"]

            for z_name in zone_names:
                loop_db = SessionLocal()
                try:
                    system_actor = (
                        loop_db.query(User)
                        .filter(User.role == "admin")
                        .order_by(User.created_at.asc())
                        .first()
                    )
                    if system_actor is None:
                        logger.warning("Skipping trigger monitor run because no admin/system actor exists.")
                        break
                    req = TriggerSimulateRequest(zone=z_name)
                    res = await check_zone_triggers(req, loop_db, system_actor)
                    logger.info(f"Trigger Monitor check for {z_name}: {res.message}")
                except Exception as e:
                    logger.error(f"Error checking triggers for {z_name}: {e}")
                finally:
                    loop_db.close()
            
        except Exception as e:
            logger.error(f"Error in monitor loop: {e}")
            
        # 15 minutes = 900 seconds
        await asyncio.sleep(900)
