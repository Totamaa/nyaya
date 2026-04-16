from taskiq_redis import ListQueueBroker

from app.core.config.redis import REDIS_URL

broker = ListQueueBroker(
    url=REDIS_URL,
    queue_name="main_queue",
)
