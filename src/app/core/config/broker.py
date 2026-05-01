from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.core.config.redis import REDIS_URL

broker = ListQueueBroker(url=REDIS_URL, queue_name="main_queue").with_result_backend(
    RedisAsyncResultBackend(redis_url=REDIS_URL, result_ex_time=3600)
)
