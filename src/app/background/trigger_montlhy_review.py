import asyncio

from app.background.tasks.review import orchestrate_monthly_reviews
from app.core.config.broker import broker


async def main() -> None:
    await broker.startup()
    try:
        task = await orchestrate_monthly_reviews.kiq()
        print(f"Enqueued orchestrate_monthly_reviews (task_id={task.task_id})")
    finally:
        await broker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
