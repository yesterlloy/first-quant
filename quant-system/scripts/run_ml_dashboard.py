"""ML Dashboard启动脚本"""

import yaml
from visual.ml_dashboard import MLDashboard


def main():
    with open("config/settings.yaml") as f:
        config = yaml.safe_load(f)

    dashboard = MLDashboard()
    dashboard.run(port=8052, host=config["dashboard"]["host"])


if __name__ == "__main__":
    main()