import logging

from fastapi import status

from app.core.errors.exceptions.base import BusinessException


class LLMAuthenticationException(BusinessException):
    def __init__(self):
        super().__init__(
            message_front="Service d'évaluation temporairement indisponible.",
            message_log="LLM authentication failed: invalid or missing API key.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            log_level=logging.CRITICAL,
            tag="SERVICE:LLM",
        )


class LLMQuotaExceededException(BusinessException):
    def __init__(self):
        super().__init__(
            message_front="Service d'évaluation temporairement indisponible.",
            message_log="LLM quota exhausted: no remaining credits or monthly cap reached.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            log_level=logging.CRITICAL,
            tag="SERVICE:LLM",
        )


class LLMRateLimitException(BusinessException):
    def __init__(self):
        super().__init__(
            message_front="Service d'évaluation temporairement surchargé, réessayez dans quelques instants.",
            message_log="LLM rate limit exceeded (HTTP 429).",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            log_level=logging.ERROR,
            tag="SERVICE:LLM",
        )


class LLMTimeoutException(BusinessException):
    def __init__(self, timeout_seconds: int | float, detail: str = ""):
        log_msg = f"LLM request timed out after {timeout_seconds}s."
        if detail:
            log_msg += f" {detail}"
        super().__init__(
            message_front="Le service LLM a mis trop de temps à répondre.",
            message_log=log_msg,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            log_level=logging.ERROR,
            tag="SERVICE:LLM",
        )


class LLMUnavailableException(BusinessException):
    def __init__(self):
        super().__init__(
            message_front="Service d'évaluation temporairement indisponible.",
            message_log="LLM provider returned 502/503: service unavailable.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            log_level=logging.ERROR,
            tag="SERVICE:LLM",
        )


class LLMInvalidResponseException(BusinessException):
    def __init__(self, detail: str = ""):
        super().__init__(
            message_front="Erreur interne lors de l'évaluation.",
            message_log=f"LLM returned an unparseable or unexpected response. {detail}".strip(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            log_level=logging.ERROR,
            tag="SERVICE:LLM",
        )


class LLMContextLengthException(BusinessException):
    def __init__(self):
        super().__init__(
            message_front="Le message est trop long pour être évalué.",
            message_log="LLM context length exceeded: input is too long for the model.",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            log_level=logging.WARNING,
            tag="SERVICE:LLM",
        )
