"""Dashboard 启动入口"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visual.dashboard import run_server


if __name__ == "__main__":
    run_server()