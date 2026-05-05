import logging
from fastapi import status

from app.core.errors.exceptions.base import BusinessException


class EvaluationNotFoundException(BusinessException):
    def __init__(self, message_external_id: str):
        super().__init__(
            message_front="Evaluation not found.",
            message_log=f"Evaluation for message external_id={message_external_id} not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            log_level=logging.WARNING,
            tag="SERVICE:Evaluation",
        )

class LLMAuthenticationException(BusinessException):
    """Clé API invalide ou absente — aucun appel LLM ne fonctionnera."""

    def __init__(self):
        super().__init__(
            message_front="Service d'évaluation temporairement indisponible.",
            message_log="LLM authentication failed: invalid or missing API key.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            log_level=logging.CRITICAL,
            tag="SERVICE:LLM",
        )


class LLMQuotaExceededException(BusinessException):
    """Crédits ou plafond mensuel épuisés."""

    def __init__(self):
        super().__init__(
            message_front="Service d'évaluation temporairement indisponible.",
            message_log="LLM quota exhausted: no remaining credits or monthly cap reached.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            log_level=logging.CRITICAL,
            tag="SERVICE:LLM",
        )


class LLMRateLimitException(BusinessException):
    """429 renvoyé par le provider — trop de requêtes simultanées."""

    def __init__(self):
        super().__init__(
            message_front="Service d'évaluation temporairement surchargé, réessayez dans quelques instants.",
            message_log="LLM rate limit exceeded (HTTP 429).",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            log_level=logging.ERROR,
            tag="SERVICE:LLM",
        )


class LLMTimeoutException(BusinessException):
    """La requête LLM a dépassé le délai maximal d'attente.

    À lever en catchant asyncio.TimeoutError depuis asyncio.wait_for().
    """

    def __init__(self, timeout_seconds: int):
        super().__init__(
            message_front="Le service d'évaluation a mis trop de temps à répondre.",
            message_log=f"LLM request timed out after {timeout_seconds}s.",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            log_level=logging.ERROR,
            tag="SERVICE:LLM",
        )


class LLMUnavailableException(BusinessException):
    """502 / 503 renvoyé par le provider — service indisponible."""

    def __init__(self):
        super().__init__(
            message_front="Service d'évaluation temporairement indisponible.",
            message_log="LLM provider returned 502/503: service unavailable.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            log_level=logging.ERROR,
            tag="SERVICE:LLM",
        )


class LLMInvalidResponseException(BusinessException):
    """La réponse du LLM n'a pas pu être parsée (format inattendu ou incomplet)."""

    def __init__(self, detail: str = ""):
        super().__init__(
            message_front="Erreur interne lors de l'évaluation.",
            message_log=f"LLM returned an unparseable or unexpected response. {detail}".strip(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            log_level=logging.ERROR,
            tag="SERVICE:LLM",
        )


class LLMContextLengthException(BusinessException):
    """Le texte soumis dépasse la fenêtre de contexte du modèle."""

    def __init__(self):
        super().__init__(
            message_front="Le message est trop long pour être évalué.",
            message_log="LLM context length exceeded: input is too long for the model.",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            log_level=logging.WARNING,
            tag="SERVICE:LLM",
        )
