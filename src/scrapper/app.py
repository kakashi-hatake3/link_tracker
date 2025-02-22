import asyncio
import logging
import aiohttp
from fastapi import FastAPI
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from src.scrapper.api import router
from src.scrapper.storage import ScrapperStorage
from src.scrapper.clients import UpdateChecker
from src.scrapper.scheduler import UpdateScheduler

logger = logging.getLogger(__name__)

BOT_BASE_URL = "http://localhost:7777"
CHECK_INTERVAL = 10

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.storage = ScrapperStorage()

    async with aiohttp.ClientSession() as session:
        app.state.session = session
        app.state.update_checker = UpdateChecker(session)

        scheduler = UpdateScheduler(
            storage=app.state.storage,
            update_checker=app.state.update_checker,
            bot_base_url=BOT_BASE_URL
        )
        await scheduler.start(check_interval=CHECK_INTERVAL)
        app.state.scheduler = scheduler

        logger.info("Application started with update scheduler (bot URL: %s)", BOT_BASE_URL)
        yield

        await scheduler.stop()
        logger.info("Application shutdown complete")

app = FastAPI(
    title="Scrapper API",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080,
                log_config='log_conf.yaml'
                )