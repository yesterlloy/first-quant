"""因子注册表 - 统一管理所有因子"""

from typing import Dict, Type, List
from factor.base import BaseFactor, FactorInfo
from loguru import logger


class FactorRegistry:
    """因子注册与查找

    所有因子实例化后注册到此表，支持：
    - 按名称查找因子
    - 按分类列出因子
    - 批量计算所有因子
    """

    _factors: Dict[str, BaseFactor] = {}

    @classmethod
    def register(cls, factor: BaseFactor):
        """注册一个因子实例"""
        info = factor.info()
        name = info.name
        if name in cls._factors:
            logger.warning(f"Factor {name} already registered, overwriting")
        cls._factors[name] = factor
        logger.info(f"Registered factor: {name} ({info.category})")

    @classmethod
    def get(cls, name: str) -> BaseFactor:
        """按名称获取因子"""
        factor = cls._factors.get(name)
        if factor is None:
            raise KeyError(f"Factor '{name}' not found. Available: {list(cls._factors.keys())}")
        return factor

    @classmethod
    def list_factors(cls, category: str = None) -> List[FactorInfo]:
        """列出所有因子信息，可按分类筛选"""
        infos = [f.info() for f in cls._factors.values()]
        if category:
            infos = [i for i in infos if i.category == category]
        return infos

    @classmethod
    def list_names(cls, category: str = None) -> List[str]:
        """列出因子名称"""
        return [i.name for i in cls.list_factors(category)]

    @classmethod
    def count(cls) -> int:
        """已注册因子数量"""
        return len(cls._factors)

    @classmethod
    def clear(cls):
        """清空注册表（测试用）"""
        cls._factors = {}


def auto_register():
    """自动注册所有因子模块

    导入各因子模块，实例化并注册到 FactorRegistry
    """
    from factor.valuation import EP, BP, DP, SP
    from factor.quality import ROE, ROA, DebtRatio, CashFlowQuality
    from factor.growth import RevenueGrowth, ProfitGrowth, ROEChange
    from factor.technical import MOM, REV, VOL, TURN, LIQ
    from factor.scale import MCAP, FCAP

    factors = [
        # 估值
        EP(), BP(), DP(), SP(),
        # 质量
        ROE(), ROA(), DebtRatio(), CashFlowQuality(),
        # 成长
        RevenueGrowth(), ProfitGrowth(), ROEChange(),
        # 技术
        MOM(), REV(), VOL(), TURN(), LIQ(),
        # 规模
        MCAP(), FCAP(),
    ]

    for f in factors:
        FactorRegistry.register(f)

    logger.info(f"Auto-registered {FactorRegistry.count()} factors")