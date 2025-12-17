"""
Structured JSON Logging Configuration for Hydra Tools API

Provides:
- JSON formatted logs for easy parsing (Loki, ELK, etc.)
- Request ID tracking across log entries
- Automatic context injection (method, path, duration)
- Log level filtering via environment variable
"""

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Optional

# Context variable for request ID tracking
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Output format:
    {
        "timestamp": "2025-12-17T19:30:00.000Z",
        "level": "INFO",
        "logger": "hydra_tools.api",
        "message": "Request completed",
        "request_id": "abc-123",
        "extra": { ... }
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add request ID if available
        request_id = request_id_ctx.get()
        if request_id:
            log_obj["request_id"] = request_id

        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message", "taskName"
            ):
                extra_fields[key] = value

        if extra_fields:
            log_obj["extra"] = extra_fields

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, default=str)


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    log_to_file: Optional[str] = None
) -> logging.Logger:
    """
    Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON formatting (True) or standard format (False)
        log_to_file: Optional file path for log output

    Returns:
        Configured root logger
    """
    import os

    # Allow environment override
    level = os.environ.get("HYDRA_LOG_LEVEL", level).upper()
    json_format = os.environ.get("HYDRA_LOG_JSON", str(json_format)).lower() == "true"

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level, logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_to_file:
        file_handler = logging.FileHandler(log_to_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Configure uvicorn loggers to use our formatter
    for uvicorn_logger_name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.handlers = []  # Remove default handlers
        if json_format:
            uvicorn_handler = logging.StreamHandler(sys.stdout)
            uvicorn_handler.setFormatter(formatter)
            uvicorn_logger.addHandler(uvicorn_handler)

    # Suppress uvicorn access logs entirely (we use our middleware instead)
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers = []
    uvicorn_access.setLevel(logging.CRITICAL)
    uvicorn_access.propagate = False

    return root_logger


def get_uvicorn_log_config(json_format: bool = True) -> dict:
    """
    Get uvicorn logging configuration compatible with our setup.

    Pass this to uvicorn.run(log_config=...) to ensure consistent logging.
    """
    if not json_format:
        # Standard format - just disable access logs
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
                "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
                "uvicorn.access": {"handlers": [], "level": "CRITICAL", "propagate": False},
            },
        }

    # JSON format with disabled access logs (we use middleware instead)
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "hydra_tools.logging_config.JSONFormatter",
            },
        },
        "handlers": {
            "default": {
                "formatter": "json",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.access": {"handlers": [], "level": "CRITICAL", "propagate": False},
        },
    }


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)


class LogContext:
    """
    Context manager for adding temporary context to logs.

    Usage:
        with LogContext(user_id="123", action="login"):
            logger.info("User action")  # Will include user_id and action
    """

    def __init__(self, **kwargs):
        self.context = kwargs
        self.old_factory = None

    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        context = self.context

        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in context.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())[:8]


def set_request_id(request_id: str) -> None:
    """Set the request ID for the current context."""
    request_id_ctx.set(request_id)


def get_request_id() -> Optional[str]:
    """Get the request ID for the current context."""
    return request_id_ctx.get()


# Convenience function for request logging
def log_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **extra
) -> None:
    """
    Log a completed HTTP request with standard fields.

    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        **extra: Additional fields to include
    """
    log_data = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        **extra
    }

    # Determine log level based on status code
    if status_code >= 500:
        logger.error("Request failed", extra=log_data)
    elif status_code >= 400:
        logger.warning("Request client error", extra=log_data)
    else:
        logger.info("Request completed", extra=log_data)
