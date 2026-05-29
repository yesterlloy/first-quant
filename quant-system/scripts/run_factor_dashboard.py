"""因子Dashboard启动脚本"""

import yaml
from visual.factor_dashboard import FactorDashboard


def main():
    with open("config/settings.yaml") as f:
        config = yaml.safe_load(f)

    dashboard = FactorDashboard()
    dashboard.run(
        port=8051,
        host=config["dashboard"]["host"],
    )


if __name__ == "__main__":
    main()