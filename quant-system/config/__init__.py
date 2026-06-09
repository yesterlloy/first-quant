"""配置模块"""

import yaml


def get_config(path: str = "config/settings.yaml") -> dict:
    """获取配置"""
    with open(path) as f:
        return yaml.safe_load(f)


def get_alarm_config(path: str = "config/alarm.yaml") -> dict:
    """获取告警配置"""
    with open(path) as f:
        return yaml.safe_load(f).get("alert", {})


def get_alert_manager_from_config(config_path: str = "config/alarm.yaml"):
    """从配置创建AlertManager"""
    from risk.alert import AlertManager
    config = get_alarm_config(config_path)
    return AlertManager.from_config(config)
