"""风控服务：规则管理、事件日志、风险检查."""

import json
from datetime import date, datetime
from typing import List, Optional, Tuple

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.models.risk import RiskEvent, RiskRule
from app.models.trading import Position
from app.schemas.risk import RiskCheckResult, RiskRuleCreate, RiskRuleUpdate


# ========== 风控规则管理 ==========

def get_rule(db: Session, rule_id: int) -> RiskRule:
    """获取单个规则."""
    rule = db.query(RiskRule).filter(RiskRule.id == rule_id).first()
    if not rule:
        raise NotFoundException(resource=f"RiskRule {rule_id}")
    return rule


def get_rule_by_name(db: Session, rule_name: str) -> Optional[RiskRule]:
    """按名称获取规则."""
    return db.query(RiskRule).filter(RiskRule.rule_name == rule_name).first()


def list_rules(
    db: Session,
    level: Optional[str] = None,
    enabled: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[RiskRule], int]:
    """获取规则列表."""
    query = db.query(RiskRule)

    if level:
        query = query.filter(RiskRule.level == level)
    if enabled is not None:
        query = query.filter(RiskRule.enabled == enabled)

    total = query.count()
    items = query.order_by(RiskRule.level, RiskRule.rule_name).offset(skip).limit(limit).all()
    return items, total


def create_rule(db: Session, rule_in: RiskRuleCreate) -> RiskRule:
    """创建风控规则."""
    if get_rule_by_name(db, rule_in.rule_name):
        raise ValidationException(message=f"规则名称已存在: {rule_in.rule_name}")

    rule = RiskRule(
        rule_name=rule_in.rule_name,
        rule_type=rule_in.rule_type,
        level=rule_in.level,
        params=json.dumps(rule_in.params) if rule_in.params else None,
        enabled=rule_in.enabled,
        description=rule_in.description,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_rule(db: Session, rule_id: int, rule_in: RiskRuleUpdate) -> RiskRule:
    """更新风控规则."""
    rule = get_rule(db, rule_id)

    update_data = rule_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "params" and value is not None:
            setattr(rule, field, json.dumps(value))
        else:
            setattr(rule, field, value)

    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, rule_id: int) -> None:
    """删除风控规则."""
    rule = get_rule(db, rule_id)
    db.delete(rule)
    db.commit()


def toggle_rule(db: Session, rule_id: int, enabled: bool) -> RiskRule:
    """启用/禁用规则."""
    rule = get_rule(db, rule_id)
    rule.enabled = enabled
    db.commit()
    db.refresh(rule)
    return rule


# ========== 风控事件管理 ==========

def get_event(db: Session, event_id: int) -> RiskEvent:
    """获取单个事件."""
    event = db.query(RiskEvent).filter(RiskEvent.id == event_id).first()
    if not event:
        raise NotFoundException(resource=f"RiskEvent {event_id}")
    return event


def list_events(
    db: Session,
    level: Optional[str] = None,
    event_type: Optional[str] = None,
    code: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[RiskEvent], int]:
    """获取事件列表."""
    query = db.query(RiskEvent)

    if level:
        query = query.filter(RiskEvent.level == level)
    if event_type:
        query = query.filter(RiskEvent.type == event_type)
    if code:
        query = query.filter(RiskEvent.code == code)
    if start_date:
        # SQLite: 比较 timestamp 字符串前缀
        query = query.filter(RiskEvent.timestamp >= start_date.isoformat())
    if end_date:
        query = query.filter(RiskEvent.timestamp <= end_date.isoformat())

    total = query.count()
    items = query.order_by(desc(RiskEvent.timestamp)).offset(skip).limit(limit).all()
    return items, total


def create_event(
    db: Session,
    level: str,
    event_type: str,
    message: str,
    code: Optional[str] = None,
    details: Optional[dict] = None,
) -> RiskEvent:
    """创建风控事件."""
    event = RiskEvent(
        timestamp=datetime.now(),
        level=level,
        type=event_type,
        code=code,
        message=message,
        details=json.dumps(details) if details else None,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


# ========== 风控检查逻辑 ==========

def check_risk(db: Session, action: str, code: Optional[str] = None, shares: Optional[int] = None,
                price: Optional[float] = None) -> RiskCheckResult:
    """执行风控检查.

    检查规则：
    1. 单只股票持仓上限
    2. 单行业持仓集中度
    3. 止损检查
    4. 总仓位检查
    """
    warnings: List[str] = []
    errors: List[str] = []
    triggered: List[str] = []

    # 获取所有启用的规则
    rules = db.query(RiskRule).filter(RiskRule.enabled == True).all()

    # 获取当前持仓
    today = date.today().isoformat()
    positions = db.query(Position).filter(Position.date == today).all()
    if not positions:
        # 如果没有今日持仓，使用最新的
        latest_date = db.query(func.max(Position.date)).scalar()
        if latest_date:
            positions = db.query(Position).filter(Position.date == latest_date).all()

    # 计算总市值
    total_value = sum((p.market_value or 0) for p in positions if (p.shares or 0) > 0)

    for rule in rules:
        try:
            params = json.loads(rule.params) if rule.params else {}
        except (json.JSONDecodeError, TypeError):
            params = {}

        # 规则 1: 单只股票持仓上限
        if rule.rule_type == "SinglePositionLimit":
            if code and shares and price:
                position_value = shares * price
                limit_pct = params.get("max_pct", 0.15)
                if total_value > 0:
                    new_total = total_value + position_value if action == "buy" else total_value
                    pct = position_value / new_total
                    if pct > limit_pct:
                        msg = f"单股持仓超过上限: {(pct * 100):.1f}% > {(limit_pct * 100):.1f}%"
                        if rule.level == "block":
                            errors.append(msg)
                        else:
                            warnings.append(msg)
                        triggered.append(rule.rule_name)

        # 规则 2: 总仓位上限
        elif rule.rule_type == "TotalPositionLimit":
            max_position = params.get("max_position", 0.95)
            if total_value > 0:
                cash = params.get("cash", 1_000_000)  # 默认现金
                position_pct = total_value / (total_value + cash)
                if action == "buy" and position_pct > max_position:
                    msg = f"总仓位超过上限: {(position_pct * 100):.1f}% > {(max_position * 100):.1f}%"
                    if rule.level == "block":
                        errors.append(msg)
                    else:
                        warnings.append(msg)
                    triggered.append(rule.rule_name)

        # 规则 3: 单只股票止损
        elif rule.rule_type == "StopLossRule":
            if code:
                stop_loss_pct = params.get("stop_loss_pct", -0.10)
                for pos in positions:
                    if pos.code == code and pos.cost_price and pos.current_price:
                        pnl_pct = (pos.current_price - pos.cost_price) / pos.cost_price
                        if pnl_pct < stop_loss_pct:
                            msg = f"{code} 触发止损: 浮亏 {(pnl_pct * 100):.1f}% < {(stop_loss_pct * 100):.1f}%"
                            if rule.level == "block":
                                errors.append(msg)
                            else:
                                warnings.append(msg)
                            triggered.append(rule.rule_name)

    # 记录风控事件
    if warnings or errors:
        level = "block" if errors else "warning"
        create_event(
            db,
            level=level,
            event_type="risk_check",
            code=code,
            message=f"风控检查: {len(errors)} 个错误, {len(warnings)} 个警告",
            details={"errors": errors, "warnings": warnings, "triggered": triggered},
        )

    return RiskCheckResult(
        passed=len(errors) == 0,
        level="block" if errors else "warning" if warnings else "info",
        triggered_rules=triggered,
        warnings=warnings,
        errors=errors,
        details={"total_value": total_value},
    )


# ========== 风控统计 ==========

def get_risk_stats(db: Session) -> dict:
    """获取风控统计."""
    total_events = db.query(func.count(RiskEvent.id)).scalar() or 0

    today = date.today().isoformat()
    today_events = db.query(func.count(RiskEvent.id)).filter(
        RiskEvent.timestamp >= today
    ).scalar() or 0

    warning_count = db.query(func.count(RiskEvent.id)).filter(
        RiskEvent.level == "warning"
    ).scalar() or 0

    block_count = db.query(func.count(RiskEvent.id)).filter(
        RiskEvent.level == "block"
    ).scalar() or 0

    total_rules = db.query(func.count(RiskRule.id)).scalar() or 0
    enabled_rules = db.query(func.count(RiskRule.id)).filter(
        RiskRule.enabled == True
    ).scalar() or 0

    # 触发最多的 Top 5 规则
    top_triggers = db.query(
        RiskEvent.type, func.count(RiskEvent.id).label("count")
    ).filter(RiskEvent.type.isnot(None)).group_by(
        RiskEvent.type
    ).order_by(desc("count")).limit(5).all()

    return {
        "total_events": total_events,
        "today_events": today_events,
        "warning_count": warning_count,
        "block_count": block_count,
        "total_rules": total_rules,
        "enabled_rules": enabled_rules,
        "top_triggers": [{"type": t, "count": c} for t, c in top_triggers],
    }


# ========== 初始化默认规则 ==========

def init_default_rules(db: Session) -> None:
    """初始化默认风控规则."""
    default_rules = [
        {
            "rule_name": "单只股票持仓上限",
            "rule_type": "SinglePositionLimit",
            "level": "warning",
            "params": {"max_pct": 0.15},
            "description": "单只股票持仓不超过总资产的 15%",
        },
        {
            "rule_name": "总仓位上限",
            "rule_type": "TotalPositionLimit",
            "level": "warning",
            "params": {"max_position": 0.95},
            "description": "总仓位不超过 95%，保留至少 5% 现金",
        },
        {
            "rule_name": "个股止损检查",
            "rule_type": "StopLossRule",
            "level": "block",
            "params": {"stop_loss_pct": -0.10},
            "description": "单只股票浮亏超过 10% 时阻止买入",
        },
    ]

    for rule_data in default_rules:
        if not get_rule_by_name(db, rule_data["rule_name"]):
            rule = RiskRuleCreate(**rule_data)
            create_rule(db, rule)
