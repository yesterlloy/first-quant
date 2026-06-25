"""回测服务：任务 CRUD + 执行.

执行部分通过懒加载 quant-system 的回测引擎（``backtest.engine``）实现：
当完整量化环境（vectorbt 等）可用时真实运行回测并落库结果；
环境不可用时将任务标记为 failed 并抛出业务异常，便于前端展示与后续接入 Celery。
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessException, NotFoundException, ValidationException
from app.models.backtest import BacktestResult, BacktestTask
from app.schemas.backtest import BacktestTaskCreate, BacktestTaskUpdate, BacktestListParams

# quant-system 项目根目录（backend 的上一级），用于懒加载量化引擎
_QUANT_ROOT: Path = Path(__file__).resolve().parents[3]


def list_backtests(db: Session, params: BacktestListParams) -> tuple[list[BacktestTask], int]:
    """分页查询回测任务."""
    query = db.query(BacktestTask)
    if params.status:
        query = query.filter(BacktestTask.status == params.status)
    if params.strategy_name:
        query = query.filter(BacktestTask.strategy_name == params.strategy_name)

    total = query.count()
    items = (
        query.order_by(BacktestTask.created_at.desc())
        .offset(params.offset)
        .limit(params.limit)
        .all()
    )
    return items, total


def get_backtest(db: Session, task_id: int) -> BacktestTask:
    """查询单个回测任务."""
    task = db.query(BacktestTask).filter(BacktestTask.id == task_id).first()
    if not task:
        raise NotFoundException(resource=f"BacktestTask {task_id}")
    return task


def create_backtest(db: Session, task_in: BacktestTaskCreate, user_id: Optional[int] = None) -> BacktestTask:
    """创建回测任务（状态 pending，等待执行）."""
    if task_in.start_date >= task_in.end_date:
        raise ValidationException(message="开始日期必须早于结束日期")

    task = BacktestTask(
        name=task_in.name,
        strategy_name=task_in.strategy_name,
        strategy_params=json.dumps(task_in.strategy_params, ensure_ascii=False) if task_in.strategy_params else None,
        status="pending",
        start_date=task_in.start_date,
        end_date=task_in.end_date,
        benchmark=task_in.benchmark,
        initial_capital=task_in.initial_capital,
        commission=task_in.commission,
        slippage=task_in.slippage,
        created_by=user_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_backtest(db: Session, task_id: int, task_in: BacktestTaskUpdate) -> BacktestTask:
    """更新回测任务（仅 pending 状态可改）."""
    task = get_backtest(db, task_id)
    if task.status != "pending":
        raise BusinessException(code=5006, message="仅待执行（pending）任务可更新")

    if task_in.name is not None:
        task.name = task_in.name
    if task_in.strategy_params is not None:
        task.strategy_params = json.dumps(task_in.strategy_params, ensure_ascii=False)
    if task_in.start_date is not None:
        task.start_date = task_in.start_date
    if task_in.end_date is not None:
        task.end_date = task_in.end_date

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def delete_backtest(db: Session, task_id: int) -> None:
    """删除回测任务及其结果."""
    task = get_backtest(db, task_id)
    db.delete(task)
    db.commit()


def get_backtest_result(db: Session, task_id: int) -> BacktestResult:
    """获取回测结果."""
    get_backtest(db, task_id)  # 校验任务存在
    result = db.query(BacktestResult).filter(BacktestResult.task_id == task_id).first()
    if not result:
        raise NotFoundException(resource=f"BacktestResult for task {task_id}")
    return result


# ---------- 执行 ----------
def _ensure_quant_path() -> None:
    """将 quant-system 根目录加入 sys.path，以便导入量化模块."""
    root = str(_QUANT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _build_strategy(strategy_name: str, params: dict):
    """根据策略名与参数构造策略实例（懒加载）."""
    import inspect

    _ensure_quant_path()
    try:
        from strategy.ma_cross import MACrossStrategy
        from strategy.momentum import MomentumStrategy
        from strategy.mean_revert import MeanRevertStrategy
    except ImportError as e:
        raise BusinessException(code=5010, message=f"策略模块不可用：{e}")

    registry = {
        "ma_cross": MACrossStrategy,
        "momentum": MomentumStrategy,
        "mean_revert": MeanRevertStrategy,
    }
    cls = registry.get(strategy_name)
    if cls is None:
        raise ValidationException(
            message=f"不支持的策略：{strategy_name}，可选：{list(registry.keys())}"
        )

    # 仅传递该策略构造函数支持的参数，避免意外报错
    sig = inspect.signature(cls.__init__)
    valid_keys = {k for k in sig.parameters if k != "self"}
    filtered = {k: v for k, v in (params or {}).items() if k in valid_keys}
    return cls(**filtered)


def _load_price_df(code: str, start_date, end_date):
    """从 quant DuckDB 加载价格序列（date, close），优先指数表，其次个股表."""
    _ensure_quant_path()
    try:
        from data.db.duckdb_manager import DuckDBManager
    except ImportError as e:
        raise BusinessException(code=5011, message=f"数据模块不可用：{e}")

    db_path = str(_QUANT_ROOT / "data" / "db" / "quant.duckdb")
    start_str = start_date.strftime("%Y%m%d") if start_date else None
    end_str = end_date.strftime("%Y%m%d") if end_date else None

    with DuckDBManager(db_path=db_path, read_only=True) as mgr:
        # 先查指数行情
        df = mgr.query(
            "SELECT date, close FROM index_quote WHERE code = ? "
            "AND (? IS NULL OR date >= ?) AND (? IS NULL OR date <= ?) ORDER BY date",
            [code, start_str, start_str, end_str, end_str],
        )
        if df.empty:
            # 回退到个股行情
            df = mgr.query(
                "SELECT date, close FROM daily_quote WHERE code = ? "
                "AND (? IS NULL OR date >= ?) AND (? IS NULL OR date <= ?) ORDER BY date",
                [code, start_str, start_str, end_str, end_str],
            )

    if df.empty:
        raise BusinessException(code=5012, message=f"代码 {code} 在指定区间无行情数据")
    return df


def run_backtest(db: Session, task_id: int) -> BacktestTask:
    """执行回测任务.

    懒加载 quant 回测引擎运行策略；成功则落库 ``BacktestResult`` 并置任务为 success，
    任何异常均置任务为 failed 并记录错误信息。
    """
    task = get_backtest(db, task_id)
    if task.status == "running":
        raise BusinessException(code=5007, message="任务正在执行中")

    params = json.loads(task.strategy_params) if task.strategy_params else {}

    task.status = "running"
    task.started_at = datetime.utcnow()
    task.error_message = None
    db.commit()

    try:
        _ensure_quant_path()
        from backtest.engine import BacktestEngine  # noqa: WPS433 懒加载

        strategy = _build_strategy(task.strategy_name, params)
        # 回测标的无显式字段时，使用基准指数作为价格序列
        code = params.get("code") or task.benchmark
        df = _load_price_df(code, task.start_date, task.end_date)

        engine = BacktestEngine(
            initial_capital=task.initial_capital,
            commission=task.commission,
            slippage=task.slippage,
        )
        result_dict = engine.run(strategy, df)

        # 落库结果（覆盖旧结果）
        existing = db.query(BacktestResult).filter(BacktestResult.task_id == task_id).first()
        if existing:
            db.delete(existing)
            db.commit()

        result = BacktestResult(
            task_id=task_id,
            total_return=_to_float(result_dict.get("total_return")),
            annualized_return=_to_float(result_dict.get("annualized_return")),
            sharpe_ratio=_to_float(result_dict.get("sharpe_ratio")),
            max_drawdown=_to_float(result_dict.get("max_drawdown")),
            win_rate=_to_float(result_dict.get("win_rate")),
            total_trades=_to_int(result_dict.get("total_trades")),
            result_data=json.dumps(
                {
                    "strategy_name": result_dict.get("strategy_name"),
                    "strategy_params": result_dict.get("strategy_params"),
                },
                ensure_ascii=False,
                default=str,
            ),
        )
        db.add(result)

        task.status = "success"
        task.finished_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
        return task

    except BusinessException:
        # 业务异常向上透传，同时记录失败状态
        task.status = "failed"
        task.finished_at = datetime.utcnow()
        task.error_message = "回测执行失败（环境或数据不可用）"
        db.commit()
        raise
    except Exception as exc:  # noqa: BLE001 捕获引擎内部任意异常
        task.status = "failed"
        task.finished_at = datetime.utcnow()
        task.error_message = str(exc)[:1000]
        db.commit()
        raise BusinessException(code=5008, message=f"回测执行失败：{exc}") from exc


def _to_float(val) -> Optional[float]:
    """安全转 float."""
    try:
        if val is None:
            return None
        return float(val)
    except (TypeError, ValueError):
        return None


def _to_int(val) -> Optional[int]:
    """安全转 int."""
    try:
        if val is None:
            return None
        return int(val)
    except (TypeError, ValueError):
        return None
