from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.core.config.redis import REDIS_URL

broker = ListQueueBroker(url=REDIS_URL).with_result_backend(
    RedisAsyncResultBackend(redis_url=REDIS_URL)
)
