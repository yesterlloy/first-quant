"""回测分析模块 - 统计指标汇总"""

import pandas as pd
from loguru import logger


class BacktestAnalyzer:
    """回测结果分析，输出标准化指标"""

    def summarize(self, result: dict) -> dict:
        """汇总单个策略回测指标"""
        summary = {
            "策略名称": result["strategy_name"],
            "策略参数": str(result["strategy_params"]),
            "总收益率": self._fmt_pct(result["total_return"]),
            "年化收益率": self._fmt_pct(result["annualized_return"]),
            "夏普比率": self._fmt_num(result["sharpe_ratio"]),
            "最大回撤": self._fmt_pct(result["max_drawdown"]),
            "交易次数": result["total_trades"],
        }

        # 赢率（可能为 None）
        if result["win_rate"] is not None:
            summary["胜率"] = self._fmt_pct(result["win_rate"])

        return summary

    def compare(self, results: list) -> pd.DataFrame:
        """多策略对比表"""
        summaries = [self.summarize(r) for r in results]
        df = pd.DataFrame(summaries)
        return df

    def _fmt_pct(self, val) -> str:
        """格式化百分比"""
        if val is None:
            return "N/A"
        return f"{val:.2%}"

    def _fmt_num(self, val) -> str:
        """格式化数值"""
        if val is None:
            return "N/A"
        return f"{val:.2f}"