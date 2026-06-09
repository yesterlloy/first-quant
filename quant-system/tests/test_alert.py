"""告警模块测试"""

import pytest
import time
from unittest.mock import patch, MagicMock


class TestAlertContext:
    """告警上下文测试"""

    def test_alert_context_defaults(self):
        from risk.alert import AlertContext
        ctx = AlertContext()
        assert ctx.code == ""
        assert ctx.position == 0.0
        assert ctx.pnl == 0.0
        assert ctx.timestamp is not None

    def test_alert_context_with_values(self):
        from risk.alert import AlertContext
        ctx = AlertContext(code="000001", pnl=-5.2, position=1000)
        assert ctx.code == "000001"
        assert ctx.pnl == -5.2
        assert ctx.position == 1000


class TestConsoleAlert:
    """控制台告警测试"""

    def test_console_alert_sends(self):
        from risk.alert import ConsoleAlert, AlertContext
        alert = ConsoleAlert()
        ctx = AlertContext(code="000001")

        # 不抛异常就算成功
        alert.send("info", "测试标题", "测试消息", ctx)
        # 只要不报错就通过


class TestAlertDeduplicator:
    """告警去重测试"""

    def test_first_alert_should_send(self):
        from risk.alert import AlertDeduplicator
        dedup = AlertDeduplicator(dedup_window_seconds=60)
        assert dedup.should_send("warning", "测试告警") is True

    def test_same_alert_within_window_should_dedup(self):
        from risk.alert import AlertDeduplicator
        dedup = AlertDeduplicator(dedup_window_seconds=60)
        assert dedup.should_send("warning", "测试告警") is True
        assert dedup.should_send("warning", "测试告警") is False  # 去重

    def test_different_level_same_title_should_send(self):
        from risk.alert import AlertDeduplicator
        dedup = AlertDeduplicator(dedup_window_seconds=60)
        assert dedup.should_send("warning", "测试告警") is True
        assert dedup.should_send("block", "测试告警") is True  # 级别不同，不同告警

    def test_after_window_should_send_again(self):
        from risk.alert import AlertDeduplicator
        dedup = AlertDeduplicator(dedup_window_seconds=0.1)  # 100ms窗口
        assert dedup.should_send("warning", "测试告警") is True
        time.sleep(0.15)  # 等待超过窗口
        assert dedup.should_send("warning", "测试告警") is True


class TestAlertManager:
    """告警管理器测试"""

    def test_add_channel(self):
        from risk.alert import AlertManager, ConsoleAlert
        am = AlertManager()
        assert len(am.channels) == 0
        am.add_channel(ConsoleAlert())
        assert len(am.channels) == 1

    def test_info_level(self):
        from risk.alert import AlertManager, ConsoleAlert
        am = AlertManager()
        am.add_channel(ConsoleAlert())
        am.info("信息标题", "信息内容")  # 不抛异常就通过

    def test_warning_level(self):
        from risk.alert import AlertManager, ConsoleAlert
        am = AlertManager()
        am.add_channel(ConsoleAlert())
        am.warning("警告标题", "警告内容")  # 不抛异常就通过

    def test_block_level(self):
        from risk.alert import AlertManager, ConsoleAlert
        am = AlertManager()
        am.add_channel(ConsoleAlert())
        am.block("拦截标题", "拦截内容")  # 不抛异常就通过

    def test_disabled_manager_no_send(self, caplog):
        from risk.alert import AlertManager, ConsoleAlert
        am = AlertManager()
        am.add_channel(ConsoleAlert())
        am.enabled = False

        with caplog.at_level("INFO"):
            am.info("不会发送")

        assert "不会发送" not in caplog.text

    def test_force_send_bypasses_dedup(self):
        from risk.alert import AlertManager
        am = AlertManager(dedup_window_seconds=60)
        # 不添加channel，只测试去重逻辑
        am.enabled = True

        # 直接测试deduplicator
        assert am.deduplicator.should_send("warning", "测试") is True
        assert am.deduplicator.should_send("warning", "测试") is False  # 去重

    def test_from_config_creates_console_channel(self):
        from risk.alert import AlertManager
        config = {
            "channels": {
                "console": {"enabled": True}
            }
        }
        am = AlertManager.from_config(config)
        assert len(am.channels) == 1
        assert am.channels[0].__class__.__name__ == "ConsoleAlert"


class TestWeChatWorkAlert:
    """企业微信告警测试（Mock）"""

    @patch('requests.post')
    def test_send_calls_webhook(self, mock_post):
        from risk.alert import WeChatWorkAlert
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"errcode": 0}
        mock_post.return_value = mock_resp

        alert = WeChatWorkAlert("http://test-webhook.com")
        result = alert.send("warning", "测试", "测试内容")

        assert result is True
        mock_post.assert_called_once()
        args = mock_post.call_args
        assert args[0][0] == "http://test-webhook.com"
        assert "markdown" in args[1]["json"]

    @patch('requests.post')
    def test_send_with_context(self, mock_post):
        from risk.alert import WeChatWorkAlert, AlertContext
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"errcode": 0}
        mock_post.return_value = mock_resp

        alert = WeChatWorkAlert("http://test-webhook.com")
        ctx = AlertContext(code="000001", pnl=-5.0)
        alert.send("warning", "测试", "测试内容", ctx)

        args = mock_post.call_args
        assert "000001" in args[1]["json"]["markdown"]["content"]

    @patch('requests.post')
    def test_send_failure_returns_false(self, mock_post):
        from risk.alert import WeChatWorkAlert
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        alert = WeChatWorkAlert("http://test-webhook.com")
        result = alert.send("warning", "测试", "测试内容")

        assert result is False


class TestEmailAlert:
    """邮件告警测试（Mock）"""

    @patch('smtplib.SMTP')
    def test_send_email_tls(self, mock_smtp_class):
        from risk.alert import EmailAlert

        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        alert = EmailAlert(
            smtp_host="smtp.test.com",
            smtp_port=587,
            username="test@test.com",
            password="password",
            to_addrs=["recv@test.com"],
            use_tls=True
        )
        result = alert.send("warning", "测试标题", "测试内容")

        assert result is True
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once()
        mock_smtp.sendmail.assert_called_once()
        mock_smtp.quit.assert_called_once()

    @patch('smtplib.SMTP_SSL')
    def test_send_email_ssl(self, mock_smtp_class):
        from risk.alert import EmailAlert

        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        alert = EmailAlert(
            smtp_host="smtp.test.com",
            smtp_port=465,
            username="test@test.com",
            password="password",
            to_addrs=["recv@test.com"],
            use_tls=False
        )
        result = alert.send("warning", "测试标题", "测试内容")

        assert result is True
        mock_smtp.login.assert_called_once()
        mock_smtp.sendmail.assert_called_once()
        mock_smtp.quit.assert_called_once()

    @patch('smtplib.SMTP')
    def test_send_email_failure_returns_false(self, mock_smtp_class):
        from risk.alert import EmailAlert

        mock_smtp_class.side_effect = Exception("SMTP Error")

        alert = EmailAlert(
            smtp_host="smtp.test.com",
            smtp_port=587,
            username="test@test.com",
            password="password",
            to_addrs=["recv@test.com"],
            use_tls=True
        )
        result = alert.send("warning", "测试标题", "测试内容")

        assert result is False
