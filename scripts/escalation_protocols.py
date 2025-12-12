#!/usr/bin/env python3
"""Escalation Protocols for Hydra Agent Decision Making.

Defines when the agent should handle issues autonomously vs escalate to humans,
with confidence scoring and threshold management.
"""

import json
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta


class Severity(Enum):
    """Alert/issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ActionType(Enum):
    """Types of actions the agent can take."""
    OBSERVE = "observe"           # Just log and monitor
    NOTIFY = "notify"             # Send notification to user
    RESTART_CONTAINER = "restart_container"
    SCALE_SERVICE = "scale_service"
    CLEAR_CACHE = "clear_cache"
    RESTART_SERVICE = "restart_service"
    FAILOVER = "failover"
    ESCALATE = "escalate"         # Require human intervention


class EscalationLevel(Enum):
    """Escalation levels for human intervention."""
    NONE = 0        # Agent handles autonomously
    INFORM = 1      # Inform user after action taken
    CONFIRM = 2     # Request confirmation before action
    ESCALATE = 3    # Require human to take action


@dataclass
class ConfidenceScore:
    """Confidence scoring for agent decisions."""
    base_score: float           # 0.0-1.0 base confidence
    context_modifiers: Dict[str, float] = field(default_factory=dict)
    final_score: float = 0.0
    reasoning: List[str] = field(default_factory=list)

    def calculate(self) -> float:
        """Calculate final confidence score with modifiers."""
        self.final_score = self.base_score
        for modifier_name, modifier_value in self.context_modifiers.items():
            self.final_score *= modifier_value
            self.reasoning.append(f"{modifier_name}: {modifier_value:.2f}")
        self.final_score = max(0.0, min(1.0, self.final_score))
        return self.final_score


@dataclass
class EscalationRule:
    """A rule defining when to escalate."""
    name: str
    description: str
    severity: Severity
    action_type: ActionType
    base_confidence: float              # Base confidence for this action type
    auto_threshold: float = 0.8         # Above this = auto-handle
    confirm_threshold: float = 0.5      # Above this = confirm, below = escalate
    max_retries: int = 2                # Max autonomous retries before escalate
    cooldown_minutes: int = 30          # Cooldown between same actions
    conditions: Dict[str, Any] = field(default_factory=dict)


# Default escalation rules for common scenarios
DEFAULT_RULES: List[EscalationRule] = [
    # Container management
    EscalationRule(
        name="container_restart_healthy",
        description="Restart a container that was previously healthy",
        severity=Severity.WARNING,
        action_type=ActionType.RESTART_CONTAINER,
        base_confidence=0.9,
        auto_threshold=0.8,
        confirm_threshold=0.5,
        max_retries=2,
        cooldown_minutes=15,
        conditions={"was_healthy": True, "restart_count_24h": {"max": 3}}
    ),
    EscalationRule(
        name="container_restart_flapping",
        description="Restart a container that has been flapping",
        severity=Severity.ERROR,
        action_type=ActionType.RESTART_CONTAINER,
        base_confidence=0.4,  # Lower confidence for flapping containers
        auto_threshold=0.8,
        confirm_threshold=0.5,
        max_retries=1,
        cooldown_minutes=60,
        conditions={"restart_count_24h": {"min": 3}}
    ),

    # Service scaling
    EscalationRule(
        name="scale_up_load",
        description="Scale up service due to high load",
        severity=Severity.WARNING,
        action_type=ActionType.SCALE_SERVICE,
        base_confidence=0.85,
        auto_threshold=0.8,
        confirm_threshold=0.6,
        max_retries=1,
        cooldown_minutes=10,
        conditions={"cpu_threshold": 80, "memory_threshold": 85}
    ),

    # Cache clearing
    EscalationRule(
        name="clear_cache_space",
        description="Clear cache to free disk space",
        severity=Severity.WARNING,
        action_type=ActionType.CLEAR_CACHE,
        base_confidence=0.95,
        auto_threshold=0.9,
        confirm_threshold=0.7,
        max_retries=1,
        cooldown_minutes=60,
        conditions={"disk_threshold": 90}
    ),

    # Critical scenarios - always escalate
    EscalationRule(
        name="data_corruption_risk",
        description="Potential data corruption detected",
        severity=Severity.CRITICAL,
        action_type=ActionType.ESCALATE,
        base_confidence=0.0,  # Always escalate
        auto_threshold=1.0,   # Never auto-handle
        confirm_threshold=1.0,
        max_retries=0,
        cooldown_minutes=0,
        conditions={}
    ),
    EscalationRule(
        name="security_alert",
        description="Security-related alert",
        severity=Severity.CRITICAL,
        action_type=ActionType.ESCALATE,
        base_confidence=0.0,
        auto_threshold=1.0,
        confirm_threshold=1.0,
        max_retries=0,
        cooldown_minutes=0,
        conditions={}
    ),
    EscalationRule(
        name="gpu_thermal_critical",
        description="GPU temperature critical",
        severity=Severity.CRITICAL,
        action_type=ActionType.NOTIFY,
        base_confidence=0.7,
        auto_threshold=0.6,
        confirm_threshold=0.4,
        max_retries=0,
        cooldown_minutes=5,
        conditions={"temp_threshold_c": 85}
    ),
]


class EscalationEngine:
    """Engine for evaluating escalation decisions."""

    def __init__(self, rules: Optional[List[EscalationRule]] = None):
        self.rules = rules or DEFAULT_RULES
        self.action_history: List[Dict[str, Any]] = []
        self.rule_map = {r.name: r for r in self.rules}

    def get_context_modifiers(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Calculate context-based confidence modifiers."""
        modifiers = {}

        # Time of day modifier (more cautious during off-hours)
        hour = datetime.now().hour
        if 2 <= hour <= 6:  # Late night
            modifiers["time_of_day"] = 0.7
        elif 9 <= hour <= 17:  # Business hours
            modifiers["time_of_day"] = 1.0
        else:
            modifiers["time_of_day"] = 0.9

        # Recent failure modifier
        recent_failures = context.get("recent_failures", 0)
        if recent_failures > 5:
            modifiers["recent_failures"] = 0.5
        elif recent_failures > 2:
            modifiers["recent_failures"] = 0.7
        else:
            modifiers["recent_failures"] = 1.0

        # Cluster health modifier
        cluster_health = context.get("cluster_health_pct", 100)
        if cluster_health < 50:
            modifiers["cluster_health"] = 0.5
        elif cluster_health < 80:
            modifiers["cluster_health"] = 0.8
        else:
            modifiers["cluster_health"] = 1.0

        # Historical success rate for similar actions
        success_rate = context.get("historical_success_rate", 1.0)
        modifiers["historical_success"] = success_rate

        return modifiers

    def check_cooldown(self, rule_name: str, target: str) -> bool:
        """Check if action is in cooldown period."""
        rule = self.rule_map.get(rule_name)
        if not rule:
            return False

        cooldown_until = datetime.now() - timedelta(minutes=rule.cooldown_minutes)

        for action in reversed(self.action_history):
            if (action["rule"] == rule_name and
                action["target"] == target and
                action["timestamp"] > cooldown_until):
                return True
        return False

    def count_recent_actions(self, rule_name: str, target: str, hours: int = 24) -> int:
        """Count recent actions of this type on this target."""
        since = datetime.now() - timedelta(hours=hours)
        return sum(
            1 for a in self.action_history
            if a["rule"] == rule_name and a["target"] == target and a["timestamp"] > since
        )

    def evaluate(
        self,
        rule_name: str,
        target: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate whether an action should be taken and at what escalation level.

        Args:
            rule_name: Name of the escalation rule to evaluate
            target: Target of the action (container name, service name, etc.)
            context: Additional context for decision making

        Returns:
            Dict with decision details including:
            - escalation_level: EscalationLevel enum
            - confidence: ConfidenceScore object
            - action_type: ActionType enum
            - reasoning: List of reasons for decision
            - can_auto_execute: bool
        """
        context = context or {}
        rule = self.rule_map.get(rule_name)

        if not rule:
            return {
                "escalation_level": EscalationLevel.ESCALATE,
                "confidence": ConfidenceScore(base_score=0.0),
                "action_type": ActionType.ESCALATE,
                "reasoning": [f"Unknown rule: {rule_name}"],
                "can_auto_execute": False
            }

        # Check cooldown
        if self.check_cooldown(rule_name, target):
            return {
                "escalation_level": EscalationLevel.INFORM,
                "confidence": ConfidenceScore(base_score=0.0),
                "action_type": ActionType.OBSERVE,
                "reasoning": [f"Action in cooldown period ({rule.cooldown_minutes} min)"],
                "can_auto_execute": False
            }

        # Check retry limits
        recent_count = self.count_recent_actions(rule_name, target)
        if recent_count >= rule.max_retries:
            return {
                "escalation_level": EscalationLevel.ESCALATE,
                "confidence": ConfidenceScore(base_score=0.0),
                "action_type": ActionType.ESCALATE,
                "reasoning": [f"Max retries ({rule.max_retries}) exceeded in 24h"],
                "can_auto_execute": False
            }

        # Calculate confidence score
        confidence = ConfidenceScore(base_score=rule.base_confidence)
        confidence.context_modifiers = self.get_context_modifiers(context)
        final_confidence = confidence.calculate()

        # Determine escalation level
        reasoning = list(confidence.reasoning)

        if final_confidence >= rule.auto_threshold:
            escalation_level = EscalationLevel.NONE
            can_auto_execute = True
            reasoning.append(f"Confidence {final_confidence:.2f} >= auto threshold {rule.auto_threshold}")
        elif final_confidence >= rule.confirm_threshold:
            escalation_level = EscalationLevel.CONFIRM
            can_auto_execute = False
            reasoning.append(f"Confidence {final_confidence:.2f} requires confirmation")
        else:
            escalation_level = EscalationLevel.ESCALATE
            can_auto_execute = False
            reasoning.append(f"Confidence {final_confidence:.2f} too low, escalating")

        return {
            "escalation_level": escalation_level,
            "confidence": confidence,
            "action_type": rule.action_type,
            "severity": rule.severity,
            "reasoning": reasoning,
            "can_auto_execute": can_auto_execute,
            "rule": rule
        }

    def record_action(
        self,
        rule_name: str,
        target: str,
        success: bool,
        details: Optional[str] = None
    ):
        """Record an action taken for history tracking."""
        self.action_history.append({
            "rule": rule_name,
            "target": target,
            "success": success,
            "details": details,
            "timestamp": datetime.now()
        })

    def get_decision_summary(self, evaluation: Dict[str, Any]) -> str:
        """Generate a human-readable summary of the decision."""
        level = evaluation["escalation_level"]
        confidence = evaluation["confidence"]
        action = evaluation["action_type"]

        summary = f"Decision: {level.name}\n"
        summary += f"Action Type: {action.value}\n"
        summary += f"Confidence: {confidence.final_score:.2f}\n"
        summary += "Reasoning:\n"
        for reason in evaluation["reasoning"]:
            summary += f"  - {reason}\n"

        return summary


def main():
    """Test escalation protocols."""
    print("Hydra Escalation Protocols Test")
    print("=" * 50)

    engine = EscalationEngine()

    # Test scenarios
    scenarios = [
        {
            "name": "Healthy container restart",
            "rule": "container_restart_healthy",
            "target": "hydra-mcp",
            "context": {"was_healthy": True, "restart_count_24h": 0}
        },
        {
            "name": "Flapping container",
            "rule": "container_restart_flapping",
            "target": "hydra-ollama",
            "context": {"restart_count_24h": 5, "recent_failures": 3}
        },
        {
            "name": "GPU thermal warning",
            "rule": "gpu_thermal_critical",
            "target": "hydra-ai/RTX5090",
            "context": {"temp_c": 82, "cluster_health_pct": 95}
        },
        {
            "name": "Security alert",
            "rule": "security_alert",
            "target": "cluster",
            "context": {}
        },
    ]

    for scenario in scenarios:
        print(f"\n--- {scenario['name']} ---")
        result = engine.evaluate(
            scenario["rule"],
            scenario["target"],
            scenario.get("context", {})
        )
        print(engine.get_decision_summary(result))


if __name__ == "__main__":
    main()
