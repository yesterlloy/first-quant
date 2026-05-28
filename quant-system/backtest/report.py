"""回测报告生成"""

import os
from loguru import logger
from backtest.analyzer import BacktestAnalyzer


class BacktestReport:
    """生成回测报告（文本 + 图表文件）"""

    def __init__(self, output_dir: str = "data/reports"):
        self.output_dir = output_dir
        self.analyzer = BacktestAnalyzer()
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, results: list) -> str:
        """生成对比报告"""
        if not results:
            return "无回测结果"

        # 生成对比表
        compare_df = self.analyzer.compare(results)

        # 文本报告
        report_lines = [
            "=" * 60,
            "           A股因子选股量化系统 — 回测报告",
            "=" * 60,
            "",
            compare_df.to_string(index=False),
            "",
            "详细指标:",
            "",
        ]

        for result in results:
            summary = self.analyzer.summarize(result)
            report_lines.append(f"--- {result['strategy_name']} ---")
            for key, val in summary.items():
                report_lines.append(f"  {key}: {val}")
            report_lines.append("")

        report = "\n".join(report_lines)

        # 保存到文件
        report_path = os.path.join(self.output_dir, "backtest_report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(f"Report saved to {report_path}")
        return report