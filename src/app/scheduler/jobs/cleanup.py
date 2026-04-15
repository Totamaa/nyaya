from app.core.config.logs import get_logger

logger = get_logger()


def cleanup_old_messages():
    logger.info("TASK:cleanup_old_messages", "Task started")
    logger.info("TASK:cleanup_old_messages", "Task finished")
