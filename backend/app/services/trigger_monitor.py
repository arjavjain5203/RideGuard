# Removed old static check_triggers. Implementing asyncio worker.
import asyncio
import logging

from app.core.celery_app import enqueue_task
from app.database import SessionLocal
from app.models import Zone
from app.tasks.jobs import process_trigger_event

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
                try:
                    task = enqueue_task(process_trigger_event, z_name)
                    logger.info(f"Trigger Monitor queued check for {z_name}: {task.id}")
                except Exception as e:
                    logger.error(f"Error checking triggers for {z_name}: {e}")
            
        except Exception as e:
            logger.error(f"Error in monitor loop: {e}")
            
        # 15 minutes = 900 seconds
        await asyncio.sleep(900)
