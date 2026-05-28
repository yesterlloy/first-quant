"""数据采集运行入口"""

import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.collector.scheduler import CollectorScheduler


def main():
    scheduler = CollectorScheduler()

    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        # 全量采集
        scheduler.run_initial_collection()
    else:
        # 增量更新
        scheduler.run_daily_collection()


if __name__ == "__main__":
    main()