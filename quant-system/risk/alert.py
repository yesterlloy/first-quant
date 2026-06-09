"""告警推送模块"""

import time
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass
from loguru import logger
import requests


@dataclass
class AlertContext:
    """告警上下文"""
    code: str = ""
    position: float = 0.0
    pnl: float = 0.0
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class AlertChannel(ABC):
    """告警通道基类"""

    @abstractmethod
    def send(self, level: str, title: str, message: str, context: Optional[AlertContext] = None):
        """发送告警"""
        pass


class ConsoleAlert(AlertChannel):
    """控制台告警"""

    def send(self, level: str, title: str, message: str, context: Optional[AlertContext] = None):
        log_func = {
            "info": logger.info,
            "warning": logger.warning,
            "block": logger.error,
            "error": logger.error,
        }.get(level, logger.info)

        ctx_info = ""
        if context and context.code:
            ctx_info = f" [{context.code}]"

        log_func(f"[{level.upper()}] {title}{ctx_info}: {message}")


class WeChatWorkAlert(AlertChannel):
    """企业微信机器人告警"""

    LEVEL_COLORS = {
        "info": "info",
        "warning": "warning",
        "block": "comment",
        "error": "comment",
    }

    def __init__(self, webhook_url: str, timeout: int = 10):
        self.webhook_url = webhook_url
        self.timeout = timeout

    def send(self, level: str, title: str, message: str, context: Optional[AlertContext] = None):
        """发送企业微信markdown消息"""
        color = self.LEVEL_COLORS.get(level, "info")
        level_emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "block": "🚫",
            "error": "❌",
        }.get(level, "")

        content = f"""<font color="{color}">{level_emoji} {title}</font>

> {message}
"""

        if context and context.code:
            content += f"""
**股票代码**: {context.code}
"""
            if context.pnl != 0:
                content += f"**盈亏**: {context.pnl:+.2f}%\n"

        content += f"\n*时间: {time.strftime('%Y-%m-%d %H:%M:%S')}*"

        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }

        try:
            resp = requests.post(self.webhook_url, json=data, timeout=self.timeout)
            if resp.status_code != 200:
                logger.warning(f"WeChatWork alert failed: {resp.status_code}")
                return False
            result = resp.json()
            if result.get("errcode") != 0:
                logger.warning(f"WeChatWork alert failed: {result.get('errmsg')}")
                return False
            logger.debug("WeChatWork alert sent successfully")
            return True
        except Exception as e:
            logger.error(f"WeChatWork alert error: {e}")
            return False


class EmailAlert(AlertChannel):
    """邮件告警"""

    def __init__(self, smtp_host: str, smtp_port: int, username: str,
                 password: str, to_addrs: list, use_tls: bool = True):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.to_addrs = to_addrs
        self.use_tls = use_tls

    def send(self, level: str, title: str, message: str, context: Optional[AlertContext] = None):
        """发送邮件告警"""
        subject = f"[量化系统{level.upper()}] {title}"

        body = f"""
量化交易系统告警

级别: {level.upper()}
标题: {title}
时间: {time.strftime('%Y-%m-%d %H:%M:%S')}

详细内容:
{message}
"""

        if context and context.code:
            body += f"""
关联股票: {context.code}
"""
            if context.pnl != 0:
                body += f"当前盈亏: {context.pnl:+.2f}%\n"

        msg = MIMEText(body, 'plain', 'utf-8')
        msg['From'] = Header(f"量化系统 <{self.username}>", 'utf-8')
        msg['To'] = Header(','.join(self.to_addrs), 'utf-8')
        msg['Subject'] = Header(subject, 'utf-8')

        try:
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)

            server.login(self.username, self.password)
            server.sendmail(self.username, self.to_addrs, msg.as_string())
            server.quit()
            logger.debug("Email alert sent successfully")
            return True
        except Exception as e:
            logger.error(f"Email alert error: {e}")
            return False


class AlertDeduplicator:
    """告警去重器 - 防止相同告警短时间内重复发送"""

    def __init__(self, dedup_window_seconds: int = 60):
        self.dedup_window = dedup_window_seconds
        self._last_sent = {}  # (level, title) -> timestamp

    def should_send(self, level: str, title: str) -> bool:
        """检查是否应该发送此告警"""
        key = (level, title)
        now = time.time()

        if key in self._last_sent:
            if now - self._last_sent[key] < self.dedup_window:
                logger.debug(f"Alert '{title}' deduplicated")
                return False

        self._last_sent[key] = now
        self._cleanup()
        return True

    def _cleanup(self):
        """清理过期记录"""
        now = time.time()
        expired_keys = [
            k for k, t in self._last_sent.items()
            if now - t > self.dedup_window * 2
        ]
        for k in expired_keys:
            del self._last_sent[k]


class AlertManager:
    """告警管理器"""

    def __init__(self, dedup_window_seconds: int = 60):
        self.channels: list[AlertChannel] = []
        self.deduplicator = AlertDeduplicator(dedup_window_seconds)
        self.enabled = True

    def add_channel(self, channel: AlertChannel):
        """添加告警通道"""
        self.channels.append(channel)

    def alert(self, level: str, title: str, message: str = "",
              context: Optional[AlertContext] = None, force: bool = False):
        """发送告警到所有通道"""
        if not self.enabled:
            return

        # 去重检查
        if not force and not self.deduplicator.should_send(level, title):
            return

        for channel in self.channels:
            try:
                channel.send(level, title, message, context)
            except Exception as e:
                logger.error(f"Failed to send alert via {channel.__class__.__name__}: {e}")

    def info(self, title: str, message: str = "", context: Optional[AlertContext] = None):
        self.alert("info", title, message, context)

    def warning(self, title: str, message: str = "", context: Optional[AlertContext] = None):
        self.alert("warning", title, message, context)

    def block(self, title: str, message: str = "", context: Optional[AlertContext] = None):
        self.alert("block", title, message, context)

    def error(self, title: str, message: str = "", context: Optional[AlertContext] = None):
        self.alert("error", title, message, context)

    @classmethod
    def from_config(cls, config: dict) -> 'AlertManager':
        """从配置创建AlertManager

        config格式:
        {
            "dedup_window_seconds": 60,
            "channels": {
                "console": {"enabled": true},
                "wechat_work": {"enabled": true, "webhook_url": "xxx"},
                "email": {"enabled": true, "smtp_host": "xxx", ...}
            }
        }
        """
        am = cls(dedup_window_seconds=config.get("dedup_window_seconds", 60))

        channels_config = config.get("channels", {})

        # 控制台告警默认开启
        if channels_config.get("console", {}).get("enabled", True):
            am.add_channel(ConsoleAlert())

        # 企业微信
        wechat_config = channels_config.get("wechat_work", {})
        if wechat_config.get("enabled", False):
            am.add_channel(WeChatWorkAlert(
                webhook_url=wechat_config["webhook_url"],
                timeout=wechat_config.get("timeout", 10)
            ))
            logger.info("WeChatWork alert channel enabled")

        # 邮件
        email_config = channels_config.get("email", {})
        if email_config.get("enabled", False):
            am.add_channel(EmailAlert(
                smtp_host=email_config["smtp_host"],
                smtp_port=email_config["smtp_port"],
                username=email_config["username"],
                password=email_config["password"],
                to_addrs=email_config["to_addrs"],
                use_tls=email_config.get("use_tls", True)
            ))
            logger.info("Email alert channel enabled")

        return am
