"""因子服务：CRUD、因子值查询、有效性评估."""

from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessException, NotFoundException, ValidationException
from app.models.factor import Factor, FactorValue
from app.models.stock import DailyQuote
from app.schemas.factor import (
    FactorCreate,
    FactorEvaluateResult,
    FactorListParams,
    FactorUpdate,
    FactorValueQuery,
)


# ---------- 因子元信息 CRUD ----------
def list_factors(db: Session, params: FactorListParams) -> tuple[list[Factor], int]:
    """分页查询因子列表."""
    query = db.query(Factor)

    if params.category:
        query = query.filter(Factor.category == params.category)
    if params.enabled is not None:
        query = query.filter(Factor.enabled == params.enabled)
    if params.keyword:
        keyword = f"%{params.keyword}%"
        query = query.filter(
            or_(Factor.name.ilike(keyword), Factor.description.ilike(keyword))
        )

    total = query.count()
    items = (
        query.order_by(Factor.category, Factor.name)
        .offset(params.offset)
        .limit(params.limit)
        .all()
    )
    return items, total


def get_factor(db: Session, name: str) -> Factor:
    """按名称查询因子."""
    factor = db.query(Factor).filter(Factor.name == name).first()
    if not factor:
        raise NotFoundException(resource=f"Factor {name}")
    return factor


def create_factor(db: Session, factor_in: FactorCreate) -> Factor:
    """创建因子."""
    if db.query(Factor).filter(Factor.name == factor_in.name).first():
        raise ValidationException(message=f"因子 {factor_in.name} 已存在")

    factor = Factor(
        name=factor_in.name,
        category=factor_in.category,
        description=factor_in.description,
        lookback=factor_in.lookback,
        freq=factor_in.freq,
        depends=factor_in.depends,
        enabled=True,
    )
    db.add(factor)
    db.commit()
    db.refresh(factor)
    return factor


def update_factor(db: Session, name: str, factor_in: FactorUpdate) -> Factor:
    """更新因子."""
    factor = get_factor(db, name)
    update_data = factor_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(factor, field, value)

    db.add(factor)
    db.commit()
    db.refresh(factor)
    return factor


def delete_factor(db: Session, name: str) -> None:
    """删除因子（同时清理其因子值）."""
    factor = get_factor(db, name)
    db.query(FactorValue).filter(FactorValue.factor_name == name).delete()
    db.delete(factor)
    db.commit()


# ---------- 因子值查询 ----------
def get_factor_values(db: Session, query: FactorValueQuery) -> list[FactorValue]:
    """查询因子值，支持按日期/股票/区间筛选."""
    q = db.query(FactorValue).filter(FactorValue.factor_name == query.factor_name)

    if query.code:
        q = q.filter(FactorValue.code == query.code)
    if query.on_date:
        q = q.filter(FactorValue.date == query.on_date)
    if query.start_date:
        q = q.filter(FactorValue.date >= query.start_date)
    if query.end_date:
        q = q.filter(FactorValue.date <= query.end_date)

    # 未指定具体日期时按日期倒序，便于取最新截面
    order = FactorValue.date.desc() if not query.on_date else FactorValue.code
    return q.order_by(order).limit(query.limit).all()


# ---------- 因子有效性评估 ----------
def evaluate_factor(
    db: Session,
    name: str,
    forward_period: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> FactorEvaluateResult:
    """评估因子有效性（IC / ICIR / IC 胜率）.

    思路：取因子值与前瞻 N 日收益，按截面计算 Spearman 秩相关 IC，
    再汇总 IC 均值、标准差、ICIR、胜率。依赖 pandas / numpy。

    Args:
        name: 因子名称
        forward_period: 前瞻收益期（交易日），默认取配置 FACTOR_FORWARD_PERIOD
        start_date: 评估区间开始
        end_date: 评估区间结束
    """
    period = forward_period or settings.FACTOR_FORWARD_PERIOD

    # 拉取因子值
    fv_query = db.query(FactorValue).filter(FactorValue.factor_name == name)
    if start_date:
        fv_query = fv_query.filter(FactorValue.date >= start_date)
    if end_date:
        fv_query = fv_query.filter(FactorValue.date <= end_date)
    factor_rows = fv_query.all()

    if not factor_rows:
        raise BusinessException(code=5002, message=f"因子 {name} 无可用数据")

    factor_df = pd.DataFrame(
        [
            {"code": r.code, "date": r.date, "value": r.raw_value}
            for r in factor_rows
        ]
    )
    factor_df["date"] = pd.to_datetime(factor_df["date"])

    # 拉取收盘价用于计算前瞻收益
    codes = factor_df["code"].unique().tolist()
    quote_rows = (
        db.query(DailyQuote)
        .filter(DailyQuote.code.in_(codes))
        .order_by(DailyQuote.code, DailyQuote.date)
        .all()
    )
    if not quote_rows:
        raise BusinessException(code=5003, message="无行情数据用于计算前瞻收益")

    price_df = pd.DataFrame(
        [{"code": r.code, "date": r.date, "close": r.close} for r in quote_rows]
    )
    price_df["date"] = pd.to_datetime(price_df["date"])
    price_df = price_df.sort_values(["code", "date"])
    # 前瞻收益 = 未来第 N 日收盘价 / 当日收盘价 - 1
    price_df["forward_return"] = (
        price_df.groupby("code")["close"].shift(-period) / price_df["close"] - 1
    )

    # 合并因子值与前瞻收益
    merged = pd.merge(factor_df, price_df, on=["code", "date"], how="inner")
    merged = merged.dropna(subset=["value", "forward_return"])

    if merged.empty:
        raise BusinessException(code=5004, message="因子值与行情数据无交集")

    # 按日期截面计算 Spearman IC
    ic_series: list[float] = []
    for date_val, group in merged.groupby("date"):
        if len(group) < 5:  # 截面样本过少则跳过
            continue
        ic = group["value"].corr(group["forward_return"], method="spearman")
        if pd.notna(ic):
            ic_series.append(float(ic))

    if not ic_series:
        raise BusinessException(code=5005, message="IC 计算失败，样本不足")

    ic_arr = np.array(ic_series)
    ic_mean = float(np.mean(ic_arr))
    ic_std = float(np.std(ic_arr, ddof=1)) if len(ic_arr) > 1 else 0.0
    icir = float(ic_mean / ic_std) if ic_std > 0 else 0.0
    ic_win_rate = float((ic_arr > 0).mean())

    return FactorEvaluateResult(
        factor_name=name,
        ic_mean=ic_mean,
        ic_std=ic_std,
        icir=icir,
        ic_win_rate=ic_win_rate,
        effective=abs(icir) >= settings.FACTOR_ICIR_THRESHOLD,
    )
