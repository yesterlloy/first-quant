"""风控规则定义"""

from dataclasses import dataclass
from abc import ABC, abstractmethod
import pandas as pd


@dataclass
class RuleResult:
    """规则检查结果"""
    passed: bool
    level: str  # info / warning / block
    message: str
    rule_name: str = ""
    code: str = ""


class RiskRule(ABC):
    """风控规则基类"""

    @abstractmethod
    def check(self, context: dict) -> RuleResult:
        """执行规则检查"""
        pass


class SinglePositionLimit(RiskRule):
    """单票仓位上限规则"""

    def __init__(self, max_ratio: float = 0.1):
        self.max_ratio = max_ratio
        self.rule_name = "SinglePositionLimit"

    def check(self, context: dict) -> RuleResult:
        target_weight = context.get("target_weight", 0)

        if target_weight > self.max_ratio:
            return RuleResult(
                passed=False,
                level="block",
                message=f"单票仓位 {target_weight:.1%} 超过上限 {self.max_ratio:.1%}",
                rule_name=self.rule_name,
                code=context.get("code", ""),
            )

        return RuleResult(
            passed=True,
            level="info",
            message=f"单票仓位 {target_weight:.1%} 合规",
            rule_name=self.rule_name,
        )


class IndustryConcentration(RiskRule):
    """行业集中度规则"""

    def __init__(self, max_ratio: float = 0.3):
        self.max_ratio = max_ratio
        self.rule_name = "IndustryConcentration"

    def check(self, context: dict) -> RuleResult:
        industry_weights = context.get("industry_weights", {})

        violations = []
        for industry, weight in industry_weights.items():
            if weight > self.max_ratio:
                violations.append(f"{industry}: {weight:.1%}")

        if violations:
            return RuleResult(
                passed=False,
                level="warning",
                message=f"行业集中度超标: {', '.join(violations)}",
                rule_name=self.rule_name,
            )

        return RuleResult(
            passed=True,
            level="info",
            message="行业集中度合规",
            rule_name=self.rule_name,
        )


class StopLossRule(RiskRule):
    """个股止损规则"""

    def __init__(self, max_loss_ratio: float = -0.05):
        self.max_loss_ratio = max_loss_ratio
        self.rule_name = "StopLossRule"

    def check(self, context: dict) -> RuleResult:
        pnl_ratio = context.get("pnl_ratio", 0)
        code = context.get("code", "")

        if pnl_ratio <= self.max_loss_ratio:
            return RuleResult(
                passed=False,
                level="block",
                message=f"{code} 触发止损: 浮亏 {pnl_ratio:.1%}，超过阈值 {self.max_loss_ratio:.1%}",
                rule_name=self.rule_name,
                code=code,
            )

        return RuleResult(
            passed=True,
            level="info",
            message=f"{code} 浮亏 {pnl_ratio:.1%} 未触发止损",
            rule_name=self.rule_name,
            code=code,
        )
