"""启动所有Dashboard - 统一入口脚本"""

import sys
import subprocess
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# Dashboard配置
DASHBOARDS = [
    {
        "name": "策略回测看板",
        "port": 8050,
        "script": "visual/dashboard.py",
    },
    {
        "name": "因子分析看板",
        "port": 8051,
        "script": "visual/factor_dashboard.py",
    },
    {
        "name": "ML模型看板",
        "port": 8052,
        "script": "visual/ml_dashboard.py",
    },
    {
        "name": "实盘监控看板",
        "port": 8053,
        "script": "visual/trading_dashboard.py",
    },
    {
        "name": "统一门户",
        "port": 8055,
        "script": "visual/portal_dashboard.py",
    },
]


def run_single_dashboard(dashboard_info, wait: bool = False):
    """启动单个Dashboard"""
    script_path = Path(__file__).parent.parent / dashboard_info["script"]

    cmd = [
        sys.executable,
        str(script_path),
    ]

    logger.info(f"Starting {dashboard_info['name']} on port {dashboard_info['port']}...")

    # 设置PYTHONPATH，确保子进程能找到模块
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent.parent)

    if wait:
        subprocess.run(cmd, cwd=str(Path(__file__).parent.parent), env=env)
    else:
        subprocess.Popen(cmd, cwd=str(Path(__file__).parent.parent), env=env)


def run_all():
    """启动所有Dashboard"""
    logger.info("=" * 60)
    logger.info("启动所有量化平台Dashboard")
    logger.info("=" * 60)

    # 先启动子Dashboard
    for dashboard in DASHBOARDS[:-1]:
        run_single_dashboard(dashboard, wait=False)
        time.sleep(2)  # 间隔启动

    # 最后启动主门户
    logger.info(f"\n等待子Dashboard启动...")
    time.sleep(3)
    logger.info("\n" + "=" * 60)
    logger.info("🚀 所有Dashboard启动完成！")
    logger.info("=" * 60)
    logger.info("\n访问地址:")
    for dashboard in DASHBOARDS:
        logger.info(f"  - {dashboard['name']}: http://localhost:{dashboard['port']}")
    logger.info("\n" + "=" * 60)
    logger.info("统一门户: http://localhost:8055")
    logger.info("按 Ctrl+C 停止所有服务")
    logger.info("=" * 60 + "\n")

    # 保持主进程运行
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("\n正在停止所有服务...")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "portal":
        # 只启动统一门户
        run_single_dashboard(DASHBOARDS[-1], wait=True)
    else:
        run_all()
