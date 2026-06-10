"""具体任务实现"""

import sys
from loguru import logger


def data_collection_task(db, days: int = 5):
    """增量数据采集任务

    Args:
        db: 数据库连接
        days: 更新最近N天的数据，默认5天（包含周末补数据）
    """
    logger.info("Starting incremental data collection task...")

    try:
        sys.path.insert(0, ".")
        from data.incremental import IncrementalUpdater

        updater = IncrementalUpdater(db)

        # 运行增量更新（只更新行情，因子计算在单独任务中）
        days_updated, rows_updated = updater.update_daily_quotes(days=days)

        logger.info(f"Data collection completed: {days_updated} days, {rows_updated} rows")
        return True  # Keep backward compatibility with tests

    except Exception as e:
        logger.error(f"Data collection failed: {e}")
        raise


def factor_compute_task(db):
    """增量因子计算任务"""
    logger.info("Starting incremental factor compute task...")

    try:
        sys.path.insert(0, ".")
        from data.incremental import IncrementalUpdater

        updater = IncrementalUpdater(db)

        # 运行增量因子计算
        days_updated, rows_updated = updater.update_factors()

        logger.info(f"Factor compute completed: {days_updated} days, {rows_updated} rows")
        return True  # Keep backward compatibility with tests

    except Exception as e:
        logger.error(f"Factor compute failed: {e}")
        raise


def monthly_rebalance_task(db):
    """月度调仓任务"""
    logger.info("Starting monthly rebalance task...")

    try:
        # Import rebalancer dynamically
        sys.path.insert(0, ".")
        from executor import Rebalancer
        from executor.broker import SimulatedBroker

        broker = SimulatedBroker(db)
        rebalancer = Rebalancer(db, broker)

        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")

        result = rebalancer.run(current_date)

        logger.info(f"Monthly rebalance completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Monthly rebalance failed: {e}")
        raise


def daily_report_task(db):
    """每日持仓报告任务"""
    logger.info("Starting daily report task...")

    try:
        # Import PnL calculator dynamically
        sys.path.insert(0, ".")
        from executor import PnLCalculator

        pnl_calc = PnLCalculator(db)

        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")

        portfolio_pnl = pnl_calc.calculate_portfolio_pnl(current_date)

        # Format report
        report = f"""
===== 每日持仓报告 {current_date} =====

持仓数量: {portfolio_pnl.get('position_count', 0)} 只
总市值: ¥{portfolio_pnl.get('total_market_value', 0):,.2f}
浮动盈亏: ¥{portfolio_pnl.get('total_unrealized_pnl', 0):,.2f} ({portfolio_pnl.get('total_unrealized_pnl_pct', 0):+.2f}%)
"""
        logger.info(f"\n{report}")
        return report

    except Exception as e:
        logger.error(f"Daily report generation failed: {e}")
        raise


def data_validation_task(db):
    """数据完整性校验任务"""
    logger.info("Starting data integrity validation task...")

    try:
        sys.path.insert(0, ".")
        from data.incremental import IncrementalUpdater

        updater = IncrementalUpdater(db)

        # 运行数据完整性校验
        result = updater.validate_data_integrity()

        if result["status"] == "ok":
            logger.info("Data integrity validation passed")
        else:
            logger.warning(f"Data integrity validation found {len(result['issues'])} issues")
            for issue in result["issues"]:
                logger.warning(f"  - {issue['type']}: {issue['message']}")

        return result

    except Exception as e:
        logger.error(f"Data validation failed: {e}")
        raise


def db_backup_task(db):
    """数据库备份任务"""
    logger.info("Starting database backup task...")

    try:
        sys.path.insert(0, ".")
        from utils.db_backup import backup_scheduler_job

        # 获取数据库路径
        db_path = getattr(db, 'db_path', 'data/db/quant.duckdb')

        # 执行备份
        result = backup_scheduler_job(db_path)

        if result["success"]:
            logger.info(f"Database backup completed: {result['size_mb']:.2f} MB")
        else:
            logger.error(f"Database backup failed: {result.get('error', 'Unknown error')}")

        return result

    except Exception as e:
        logger.error(f"Database backup task failed: {e}")
        raise
