"""
FastAPI application entrypoint for UNICON-SOFT AI Technical Assistant.
Handles health checks, Telegram Webhook/Polling lifecycle, and background services.
Optimized for deployment on Render.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from aiogram.types import Update

from app.config import settings
from app.utils.logger import logger
from app.db.init_db import init_database
from app.db.session import engine
from app.bot.bot import bot, dp
from app.bot.middlewares.auth import AuthMiddleware
from app.bot.handlers import main_router
from app.workers.queue import task_queue
from app.workers.tasks import periodic_group_learning_cron

# Background tasks tracking
_background_tasks = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle manager."""
    logger.info("Starting UNICON-SOFT AI Technical Assistant...")

    # 1. Initialize Database & Extensions
    try:
        await init_database()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)

    # 2. Initialize Background Task Queue
    await task_queue.initialize()

    # 3. Start Periodic Group Learning Scanner
    cron_task = asyncio.create_task(periodic_group_learning_cron())
    _background_tasks.add(cron_task)
    cron_task.add_done_callback(_background_tasks.discard)

    # 4. Configure aiogram Middlewares and Routers
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.include_router(main_router)

    ALLOWED_UPDATES = [
        "message",
        "edited_message",
        "callback_query",
        "business_connection",
        "business_message",
        "edited_business_message",
        "deleted_business_messages"
    ]

    # 5. Configure Webhook or Polling mode
    if settings.webhook_url and settings.full_webhook_url:
        logger.info(f"Setting Telegram Webhook to: {settings.full_webhook_url}")
        try:
            await bot.set_webhook(
                url=settings.full_webhook_url,
                secret_token=settings.webhook_secret,
                drop_pending_updates=False,
                allowed_updates=ALLOWED_UPDATES
            )
            logger.info("Telegram Webhook set successfully with Business Mode support.")
        except Exception as e:
            logger.error(f"Failed to set Telegram Webhook: {e}", exc_info=True)
    else:
        logger.info("WEBHOOK_URL is not set. Starting Telegram Long Polling mode...")
        polling_task = asyncio.create_task(
            dp.start_polling(bot, allowed_updates=ALLOWED_UPDATES)
        )
        _background_tasks.add(polling_task)
        polling_task.add_done_callback(_background_tasks.discard)

    yield

    # Shutdown sequence
    logger.info("Shutting down UNICON-SOFT AI Technical Assistant...")
    for t in list(_background_tasks):
        t.cancel()

    await bot.session.close()
    await task_queue.shutdown()
    await engine.dispose()
    logger.info("Application successfully stopped.")


app = FastAPI(
    title="UNICON-SOFT AI Technical Assistant API",
    description="Personal Technical AI Assistant for UNICON-SOFT engineers on Telegram.",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/healthz", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint for Render monitoring."""
    return {
        "status": "ok",
        "app": "unicon-ai-assistant",
        "environment": settings.environment,
        "model": settings.gemini_model
    }


@app.post(settings.webhook_path)
async def telegram_webhook(request: Request):
    """Processes incoming updates from Telegram Webhook."""
    # Verify secret token if configured
    if settings.webhook_secret:
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if token != settings.webhook_secret:
            logger.warning("Invalid Telegram webhook secret token received.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")

    try:
        body = await request.json()
        update = Update.model_validate(body, context={"bot": bot})
        await dp.feed_update(bot, update)
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}", exc_info=True)
        return JSONResponse(content={"status": "ok", "error": str(e)})


@app.post("/admin/seed")
async def trigger_seed_knowledge(request: Request):
    """Admin endpoint to wipe and re-seed knowledge base."""
    from app.knowledge.seeder import seed_knowledge_base
    count = await seed_knowledge_base(clear_existing=True)
    return {"status": "ok", "seeded_count": count}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=not settings.is_production
    )
