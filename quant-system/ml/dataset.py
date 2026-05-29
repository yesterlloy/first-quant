"""训练数据集构建 - 滚动窗口+时间切分防泄露"""

import pandas as pd
import numpy as np
from loguru import logger
from ml.feature_engine import FeatureEngine


class DatasetBuilder:
    """训练数据集构建器

    核心原则：严格时间切分，防止未来信息泄露。

    滚动训练策略：
    - 训练窗口：24个月
    - 验证窗口：6个月
    - 预测窗口：1个月
    - 每月滚动更新
    """

    def __init__(self, train_months: int = 24, val_months: int = 6,
                 forward_period: int = 20, feature_engine: FeatureEngine = None):
        """
        Args:
            train_months: 训练窗口月数
            val_months: 验证窗口月数
            forward_period: 前瞻收益期（交易日）
            feature_engine: 特征工程引擎
        """
        self.train_months = train_months
        self.val_months = val_months
        self.forward_period = forward_period
        self.fe = feature_engine or FeatureEngine()

    def build_dataset(self, factor_df: pd.DataFrame,
                      price_df: pd.DataFrame,
                      industry_df: pd.Series = None,
                      start_date: str = None,
                      end_date: str = None) -> pd.DataFrame:
        """构建完整训练数据集

        Args:
            factor_df: [code, date, factor_name, raw_value]
            price_df: [code, date, close]
            industry_df: 行业分类 Series（index=code）
            start_date/end_date: 数据范围

        Returns:
            DataFrame [code, date, label, feature1, feature2, ...]
        """
        logger.info("Building training dataset...")

        # 1. 计算前瞻收益作为标签
        price_df = price_df.sort_values(["code", "date"])
        price_df["close_future"] = price_df.groupby("code")["close"].shift(-self.forward_period)
        price_df["label"] = price_df["close_future"] / price_df["close"] - 1.0

        # 2. 构宽表：每行(code, date) 对应所有因子值
        factor_pivot = factor_df.pivot_table(
            index=["code", "date"],
            columns="factor_name",
            values="raw_value",
        ).reset_index()

        # 3. 合并标签
        label_df = price_df[["code", "date", "label"]].dropna()
        dataset = factor_pivot.merge(label_df, on=["code", "date"], how="inner")

        # 4. 特征工程处理
        feature_cols = [c for c in dataset.columns if c not in ["code", "date", "label"]]
        features = dataset[feature_cols]

        # 填充 + winsorize + zscore
        processed = self.fe.build_features(
            dataset[["code"] + feature_cols],
            industry_df=industry_df,
        )

        # 5. 合回标签
        processed["date"] = dataset["date"]
        processed["label"] = dataset["label"]

        # 6. 过滤日期范围
        if start_date:
            processed = processed[processed["date"] >= start_date]
        if end_date:
            processed = processed[processed["date"] <= end_date]

        # 7. 去掉label为NaN的行
        processed = processed.dropna(subset=["label"])

        logger.info(f"Dataset built: {processed.shape[0]} rows, {processed.shape[1]-2} features")
        return processed

    def split_rolling(self, dataset: pd.DataFrame,
                      eval_date: str = None) -> dict:
        """滚动窗口切分

        Args:
            dataset: 完整数据集 [code, date, label, features...]
            eval_date: 评估日期，验证窗口和预测窗口的开始

        Returns:
            dict: train_df, val_df, test_df
        """
        dataset["date"] = pd.to_datetime(dataset["date"])
        dates = sorted(dataset["date"].unique())

        if eval_date:
            eval_dt = pd.Timestamp(eval_date)
        else:
            # 默认：最后一个验证窗口的结束日期
            eval_dt = dates[-1]

        # 训练窗口结束 = 验证窗口开始
        val_start = eval_dt - pd.DateOffset(months=self.val_months)
        train_end = val_start - pd.DateOffset(days=1)
        train_start = train_end - pd.DateOffset(months=self.train_months)

        # 切分
        train_df = dataset[
            (dataset["date"] >= train_start) & (dataset["date"] <= train_end)
        ]
        val_df = dataset[
            (dataset["date"] >= val_start) & (dataset["date"] < eval_dt)
        ]
        test_df = dataset[dataset["date"] >= eval_dt]

        logger.info(f"Rolling split: train={len(train_df)}, "
                    f"val={len(val_df)}, test={len(test_df)}")
        logger.info(f"Train: {train_start.date()} ~ {train_end.date()}, "
                    f"Val: {val_start.date()} ~ {eval_dt.date()}, "
                    f"Test: from {eval_dt.date()}")

        return {
            "train": train_df,
            "val": val_df,
            "test": test_df,
            "train_start": str(train_start.date()),
            "train_end": str(train_end.date()),
            "val_start": str(val_start.date()),
            "eval_date": str(eval_dt.date()),
        }

    def generate_rolling_windows(self, dataset: pd.DataFrame,
                                  step_months: int = 1) -> list:
        """生成所有滚动窗口

        Args:
            dataset: 完整数据集
            step_months: 滚动步长（月）

        Returns:
            list of dict: 每个窗口的 {train, val, test, dates}
        """
        dataset["date"] = pd.to_datetime(dataset["date"])
        dates = sorted(dataset["date"].unique())

        # 从足够早的日期开始滚动
        total_needed = self.train_months + self.val_months
        first_valid_idx = total_needed

        windows = []
        for i in range(first_valid_idx, len(dates), step_months):
            eval_dt = dates[i]
            split = self.split_rolling(dataset, eval_date=str(eval_dt))
            if len(split["train"]) > 100 and len(split["val"]) > 50:
                windows.append(split)

        logger.info(f"Generated {len(windows)} rolling windows")
        return windows

    def prepare_xy(self, df: pd.DataFrame) -> tuple:
        """从 DataFrame 提取 X, y

        Returns:
            (X_df, y_series) — X是特征矩阵，y是标签
        """
        exclude_cols = ["code", "date", "label"]
        feature_cols = [c for c in df.columns if c not in exclude_cols]
        X = df[feature_cols].copy()
        y = df["label"].copy()
        return X, y