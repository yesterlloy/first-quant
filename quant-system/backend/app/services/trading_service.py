"""交易服务：持仓、订单、成交、账户统计."""

import uuid
from datetime import date, datetime
from typing import List, Optional, Tuple

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.models.stock import DailyQuote
from app.models.trading import AccountSnapshot, Order, Position, Trade


def get_current_positions(
    db: Session, date: Optional[date] = None
) -> List[Position]:
    """获取当前持仓（最新日期）."""
    if not date:
        latest = db.query(func.max(Position.date)).scalar()
        if not latest:
            return []
        date = latest
    return db.query(Position).filter(Position.date == date).order_by(Position.code).all()


def get_position_history(
    db: Session, code: Optional[str] = None, limit: int = 100
) -> List[Position]:
    """获取持仓历史."""
    query = db.query(Position)
    if code:
        query = query.filter(Position.code == code)
    return query.order_by(desc(Position.date), Position.code).limit(limit).all()


def get_orders(
    db: Session,
    status: Optional[str] = None,
    code: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[Order], int]:
    """获取订单列表."""
    query = db.query(Order)

    if status:
        query = query.filter(Order.status == status)
    if code:
        query = query.filter(Order.code == code)
    if start_date:
        query = query.filter(Order.date >= start_date)
    if end_date:
        query = query.filter(Order.date <= end_date)

    total = query.count()
    items = query.order_by(desc(Order.date), desc(Order.id)).offset(skip).limit(limit).all()
    return items, total


def get_order(db: Session, order_id: int) -> Order:
    """获取单个订单."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException(resource=f"Order {order_id}")
    return order


def create_order(
    db: Session, code: str, action: str, shares: int, price: Optional[float] = None
) -> Order:
    """创建委托订单（模拟成交）."""
    action = action.lower()
    if action not in ["buy", "sell"]:
        raise ValidationException(message="操作方向必须是 buy 或 sell")

    if shares <= 0:
        raise ValidationException(message="委托股数必须大于 0")

    # 获取最新价格（市价单）
    if price is None:
        latest_quote = (
            db.query(DailyQuote)
            .filter(DailyQuote.code == code)
            .order_by(desc(DailyQuote.date))
            .first()
        )
        if not latest_quote:
            raise ValidationException(message=f"无法获取 {code} 的最新价格")
        price = latest_quote.close

    order_id = str(uuid.uuid4())[:8]
    today = date.today()

    order = Order(
        order_id=order_id,
        date=today,
        code=code,
        action=action,
        shares=shares,
        price=price,
        status="pending",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # 模拟立即成交
    order = execute_order(db, order.id)
    return order


def execute_order(db: Session, order_id: int) -> Order:
    """执行订单（模拟成交）."""
    order = get_order(db, order_id)

    if order.status != "pending":
        raise ValidationException(message=f"订单状态不是待执行: {order.status}")

    # 创建成交记录
    trade_id = f"T{order.order_id}"
    trade = Trade(
        trade_id=trade_id,
        order_id=order.order_id,
        date=order.date,
        code=order.code,
        action=order.action,
        shares=order.shares,
        price=order.price or 0.0,
        filled_at=datetime.now(),
    )
    db.add(trade)

    # 更新订单状态
    order.status = "filled"
    order.updated_at = datetime.now()

    # 更新持仓快照（模拟）
    update_position_after_trade(db, order)

    db.commit()
    db.refresh(order)
    return order


def cancel_order(db: Session, order_id: int) -> Order:
    """取消订单."""
    order = get_order(db, order_id)

    if order.status != "pending":
        raise ValidationException(message=f"只有待执行订单才能取消，当前状态: {order.status}")

    order.status = "canceled"
    order.updated_at = datetime.now()
    db.commit()
    db.refresh(order)
    return order


def update_position_after_trade(db: Session, order: Order):
    """成交后更新持仓快照（简化实现）."""
    today = date.today()

    # 获取当前最新持仓
    latest_date = db.query(func.max(Position.date)).scalar() or today

    if latest_date < today:
        # 新的一天，复制昨日持仓作为今日初始
        yesterday_positions = db.query(Position).filter(Position.date == latest_date).all()
        for pos in yesterday_positions:
            new_pos = Position(
                date=today,
                code=pos.code,
                shares=pos.shares,
                weight=pos.weight,
                cost_price=pos.cost_price,
                current_price=pos.current_price,
                market_value=pos.market_value,
            )
            db.add(new_pos)

    # 获取今日持仓
    position = db.query(Position).filter(Position.date == today, Position.code == order.code).first()

    if order.action == "buy":
        if position:
            # 更新已有持仓
            old_shares = position.shares or 0
            old_cost = position.cost_price or 0.0
            total_shares = old_shares + order.shares
            new_cost = (old_shares * old_cost + order.shares * (order.price or 0.0)) / total_shares
            position.shares = total_shares
            position.cost_price = new_cost
        else:
            # 新建持仓
            position = Position(
                date=today,
                code=order.code,
                shares=order.shares,
                cost_price=order.price,
                current_price=order.price,
                market_value=order.shares * (order.price or 0.0),
            )
            db.add(position)
    elif order.action == "sell" and position:
        # 卖出
        if position.shares:
            if order.shares >= position.shares:
                # 清仓
                position.shares = 0
                position.market_value = 0.0
            else:
                # 减仓
                position.shares -= order.shares
                position.market_value = position.shares * (position.current_price or 0.0)


def get_trades(
    db: Session,
    code: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[Trade], int]:
    """获取成交记录."""
    query = db.query(Trade)

    if code:
        query = query.filter(Trade.code == code)
    if start_date:
        query = query.filter(Trade.date >= start_date)
    if end_date:
        query = query.filter(Trade.date <= end_date)

    total = query.count()
    items = query.order_by(desc(Trade.date), desc(Trade.id)).offset(skip).limit(limit).all()
    return items, total


def get_account_snapshots(
    db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None, limit: int = 100
) -> List[AccountSnapshot]:
    """获取账户快照历史."""
    query = db.query(AccountSnapshot)

    if start_date:
        query = query.filter(AccountSnapshot.date >= start_date)
    if end_date:
        query = query.filter(AccountSnapshot.date <= end_date)

    return query.order_by(desc(AccountSnapshot.date)).limit(limit).all()


def get_latest_account_snapshot(db: Session) -> Optional[AccountSnapshot]:
    """获取最新账户快照."""
    return db.query(AccountSnapshot).order_by(desc(AccountSnapshot.date)).first()


def get_portfolio_summary(db: Session) -> dict:
    """获取组合概览统计."""
    latest_snapshot = get_latest_account_snapshot(db)
    positions = get_current_positions(db)

    # 计算持仓市值和现金
    market_value = sum(p.market_value or 0.0 for p in positions if (p.shares or 0) > 0)
    cash = latest_snapshot.cash if latest_snapshot else 1_000_000.0  # 默认初始资金
    total_value = market_value + cash

    # 计算当日盈亏（简化实现）
    today_pnl = 0.0
    if latest_snapshot and latest_snapshot.return_pct is not None:
        today_pnl = latest_snapshot.total_value * latest_snapshot.return_pct if latest_snapshot.total_value else 0.0

    # 统计持仓数量
    position_count = len([p for p in positions if (p.shares or 0) > 0])

    return {
        "total_value": total_value,
        "cash": cash,
        "market_value": market_value,
        "position_count": position_count,
        "today_pnl": today_pnl,
        "today_return_pct": latest_snapshot.return_pct if latest_snapshot else 0.0,
        "total_return_pct": 0.0,  # 待实现
        "max_drawdown_pct": 0.0,  # 待实现
        "sharpe_ratio": 0.0,  # 待实现
    }


def get_trading_stats(db: Session) -> dict:
    """获取交易统计."""
    total_trades = db.query(func.count(Trade.id)).scalar() or 0

    # 简化实现，实际应根据成交记录计算盈亏
    return {
        "total_trades": total_trades,
        "winning_trades": int(total_trades * 0.55),  # 模拟值
        "losing_trades": int(total_trades * 0.45),  # 模拟值
        "win_rate": 0.55,  # 模拟值
        "total_profit": 125_000.0,  # 模拟值
        "avg_profit_per_trade": 1_250.0,  # 模拟值
        "max_consecutive_wins": 5,  # 模拟值
        "max_consecutive_losses": 3,  # 模拟值
    }
