"""告警推送模块"""

from abc import ABC, abstractmethod
from loguru import logger


class AlertChannel(ABC):
    """告警通道基类"""

    @abstractmethod
    def send(self, level: str, title: str, message: str):
        """发送告警"""
        pass


class ConsoleAlert(AlertChannel):
    """控制台告警"""

    def send(self, level: str, title: str, message: str):
        log_func = {
            "info": logger.info,
            "warning": logger.warning,
            "block": logger.error,
        }.get(level, logger.info)

        log_func(f"[{level.upper()}] {title}: {message}")


class AlertManager:
    """告警管理器"""

    def __init__(self):
        self.channels: list[AlertChannel] = []

    def add_channel(self, channel: AlertChannel):
        """添加告警通道"""
        self.channels.append(channel)

    def alert(self, level: str, title: str, message: str):
        """发送告警到所有通道"""
        for channel in self.channels:
            try:
                channel.send(level, title, message)
            except Exception as e:
                logger.error(f"Failed to send alert via {channel}: {e}")

    def info(self, title: str, message: str = ""):
        self.alert("info", title, message)

    def warning(self, title: str, message: str = ""):
        self.alert("warning", title, message)

    def block(self, title: str, message: str = ""):
        self.alert("block", title, message)
