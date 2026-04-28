"""
Competitor Monitor — entry point.

Usage:
  python main.py run        # run one monitoring cycle now
  python main.py schedule   # start the scheduler (runs daily at configured cron time)
  python main.py initdb     # create database tables
"""
from __future__ import annotations

import asyncio
import logging

import click
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from competitor_monitor.config import settings
from competitor_monitor.scheduler import run_monitoring_cycle
from competitor_monitor.storage import init_db

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("main")


@click.group()
def cli() -> None:
    pass


@cli.command()
def initdb() -> None:
    """Create all database tables."""
    asyncio.run(init_db())
    click.echo("Database initialised.")


@cli.command()
def run() -> None:
    """Run a single monitoring cycle immediately."""
    asyncio.run(_run())


async def _run() -> None:
    await init_db()
    await run_monitoring_cycle()


@cli.command()
def schedule() -> None:
    """Start the scheduler and run monitoring cycles on the configured cron."""
    asyncio.run(_schedule())


async def _schedule() -> None:
    await init_db()

    scheduler = AsyncIOScheduler()
    trigger = CronTrigger.from_crontab(settings.schedule_cron)
    scheduler.add_job(run_monitoring_cycle, trigger, id="monitor", replace_existing=True)
    scheduler.start()

    logger.info("Scheduler started. Cron: %s", settings.schedule_cron)
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    cli()
