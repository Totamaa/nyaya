import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import threading
from typing import Optional

from app.core.config.settings import get_settings

class LoggerManager:
    _instance: Optional['LoggerManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls, log_file_path="logs/app.log"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(LoggerManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, log_file_path="logs/app.log"):
        if self._initialized:
            return
            
        self.settings = get_settings()
        self.log_file_path = log_file_path
        self.max_bytes = self.settings.LOG_MAX_BYTES
        self.backup_count = self.settings.LOG_BACKUP_COUNT

        # Use a single logger name for the singleton
        self._logger = logging.getLogger("app_logger")
        self._logger.setLevel(self.settings.LOG_LEVEL)
        
        if not self._logger.hasHandlers():
            self._setup_handlers()
            
        self._initialized = True

    def _setup_handlers(self):
        log_dir = os.path.dirname(self.log_file_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s', 
            datefmt="%Y-%m-%d %H:%M:%S %z"
        )
        
        file_handler = RotatingFileHandler(
            self.log_file_path, 
            maxBytes=self.max_bytes, 
            backupCount=self.backup_count
        )
        file_handler.setFormatter(formatter)
        self._logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

    def _format(self, tag: str, message: str, extra: str = None) -> str:
        log_message = f"[{tag}] {message}"
        if extra:
            log_message += f" ({extra})"
        return log_message
    
    
    def log(self, level: int, tag: str, message: str, extra: str = None, exc: Exception = None):
        msg = self._format(tag, message, extra)
        self._logger.log(level, msg, exc_info=exc)

    def debug(self, tag: str, message: str, extra: str = None, exc: Exception = None):
        msg = self._format(tag, message, extra)
        self._logger.debug(msg, exc_info=exc)

    def info(self, tag: str, message: str, extra: str = None, exc: Exception = None):
        msg = self._format(tag, message, extra)
        self._logger.info(msg, exc_info=exc)

    def warning(self, tag: str, message: str, extra: str = None, exc: Exception = None):
        msg = self._format(tag, message, extra)
        self._logger.warning(msg, exc_info=exc)

    def error(self, tag: str, message: str, extra: str = None, exc: Exception = None):
        msg = self._format(tag, message, extra)
        self._logger.error(msg, exc_info=exc)

    def critical(self, tag: str, message: str, extra: str = None, exc: Exception = None):
        msg = self._format(tag, message, extra)
        self._logger.critical(msg, exc_info=exc)

def get_logger() -> LoggerManager:
    return LoggerManager()
