"""配置模块"""

import yaml


def get_config(path: str = "config/settings.yaml") -> dict:
    """获取配置"""
    with open(path) as f:
        return yaml.safe_load(f)
