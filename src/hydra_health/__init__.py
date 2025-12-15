"""
Hydra Health Aggregator

A unified API for cluster-wide health monitoring.
"""

from .server import app, HealthAggregator
from .checks import ServiceCheck, CheckResult

__all__ = ["app", "HealthAggregator", "ServiceCheck", "CheckResult"]
__version__ = "1.0.0"
