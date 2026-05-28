# Phase 2 开发计划 — 因子系统 + 因子检验

> 目标：建立因子库，能计算因子、能检验因子有效性，筛选出有alpha的因子。

---

## 1. 因子体系设计

### 1.1 因子分类

| 类别 | 因子 | 计算方式 | 数据依赖 |
|------|------|----------|----------|
| **估值因子** | EP（盈利/价格） | 1/PE | 财务+行情 |
| | BP（账面/价格） | 1/PB | 财务+行情 |
| | DP（分红/价格） | 股息率 | 分红数据 |
| | SP（营收/市值） | 营收/总市值 | 财务+行情 |
| **成长因子** | 营收增长率 | YoY同比 | 财务 |
| | 净利润增长率 | YoY同比 | 财务 |
| | ROE变化率 | ΔROE | 财务 |
| **质量因子** | ROE | 杜邦分解 | 财务 |
| | ROA | 净利润/总资产 | 财务 |
| | 资产负债率 | 负债/总资产 | 财务 |
| | 经营现金流/净利润 | 现金流质量 | 财务 |
| **技术因子** | 动量（MOM） | 过去N日收益 | 行情 |
| | 反转（REV） | 过去N日收益反转 | 行情 |
| | 波动率（VOL） | 日收益标准差 | 行情 |
| | 换手率（TURN） | 日均换手率 | 行情 |
| | 流动性（LIQ） | Amihud非流动性 | 行情 |
| **规模因子** | 市值（MCAP） | 总市值 | 行情 |
| | 流通市值（FCAP） | 流通市值 | 行情 |

> 初期实现约15-20个因子，后期逐步扩展。

### 1.2 因子计算架构

```python
class BaseFactor:
    name: str           # 因子名
    category: str       # 分类（valuation/growth/quality/technical/scale）
    lookback: int       # 回看期（交易日数）
    
    def compute(self, df: pd.DataFrame) -> pd.Series:
        """输入截面数据，输出因子值"""
        raise NotImplementedError
    
    def neutralize(self, factor_df: pd.DataFrame, market_df: pd.DataFrame) -> pd.DataFrame:
        """行业/市值中性化"""
        raise NotImplementedError
```

---

## 2. 因子检验框架

### 2.1 检验指标

| 检验方法 | 指标 | 标准 | 说明 |
|----------|------|------|------|
| **IC分析** | Rank IC | |0.03| ≥ 0.03 有效 | 因子值与未来收益秩相关 |
| | IC均值 | > 0 | 正向预测力 |
| | IC标准差 | 越小越好 | 因子稳定性 |
| | ICIR | IC均值/IC标准差 | ≥ 0.5 较好 | 风险调整后预测力 |
| | IC正比例 | > 50% | IC>0的比例 | 一致性 |
| **分层回测** | 多空收益 | > 0 | top组 - bottom组 | 因子区分度 |
| | 单调性 | 递增/递减 | 各层收益递变 | 因子单调递变 |
| | Top组超额 | > 0 | 相对基准超额 | 可用性 |
| **回归分析** | t值 | |t| > 2 | 截面回归显著性 |
| | β值 | > 0 | 因子溢价 | 因子收益率 |
| **衰减分析** | 半衰期 | 适中 | 因子预测力衰减速度 | 持续性 |

### 2.2 分层回测流程

1. 每月末按因子值排序，分5层（或10层）
2. 各层等权持仓，持有1个月
3. 计算各层收益、多空收益、超额收益
4. 统计单调性、胜率

### 2.3 中性化处理

- **行业中性化**：因子值减去同行业均值
- **市值中性化**：因子值对市值做回归取残差
- 支持可选开关，对比中性化前后效果

---

## 3. 模块设计

### 项目结构扩展

```
quant-system/
├── factor/
│   ├── base.py              # 因子基类
│   ├── registry.py          # 因子注册表（统一管理所有因子）
│   ├── valuation.py         # 估值因子
│   ├── growth.py            # 成长因子
│   ├── quality.py           # 质量因子
│   ├── technical.py         # 技术因子
│   ├── scale.py             # 规模因子
│   ├── processor.py         # 因子计算引擎（批量计算+缓存）
│   └── neutralize.py        # 中性化处理
├── factor_test/
│   ├── ic_test.py           # IC分析
│   ├── layer_test.py        # 分层回测
│   ├── regression_test.py   # 截面回归
│   ├── decay_test.py        # 衰减分析
│   ├── report.py            # 因子检验报告汇总
│   └── screening.py         # 因子筛选（自动过滤无效因子）
├── data/
│   ├── collector/
│   │   ├── financial.py     # 扩展：更完整的财务数据
│   │   ├── dividend.py      # 新增：分红数据
│   │   └── industry.py      # 新增：行业分类数据
│   └── db/
│       ├── duckdb_manager.py # 扩展：因子表读写
├── visual/
│   ├── factor_dashboard.py  # 新增：因子检验看板
│   └── ic_heatmap.py        # IC热力图
│   └── layer_chart.py       # 分层收益图
├── scripts/
│   ├── run_factor_compute.py    # 批量计算因子
│   ├── run_factor_test.py       # 批量因子检验
│   └── run_factor_screening.py  # 因子筛选
```

### 数据表扩展

| 新增表 | 字段 | 说明 |
|--------|------|------|
| `factor_value` | code, date, factor_name, raw_value, neut_value | 因子值日表 |
| `industry_class` | code, industry_sw, industry_csrc | 行业分类 |
| `dividend` | code, year, dividend_per_share | 分红数据 |

---

## 4. 开发顺序

| 步骤 | 内容 | 预估时间 | 产出 |
|------|------|----------|------|
| Step 1 | 扩展数据采集（财务+分红+行业） | 3天 | 数据更完整 |
| Step 2 | 因子基类 + 注册表 + 5个估值/质量因子 | 3天 | 能计算基础因子 |
| Step 3 | 技术因子 + 成长因子 + 规模因子 | 3天 | 因子库约15个 |
| Step 4 | 因子计算引擎（批量+缓存） | 2天 | 高效计算因子 |
| Step 5 | IC分析 + 分层回测模块 | 3天 | 能检验因子 |
| Step 6 | 中性化处理 + 回归分析 + 衰减分析 | 2天 | 检验更全面 |
| Step 7 | 因子筛选 + 检验报告汇总 | 2天 | 自动筛出有效因子 |
| Step 8 | 因子Dashboard可视化 | 2天 | IC热力图、分层图 |
| Step 9 | 集成测试 | 1天 | 全流程跑通 |

**总预估：约20个工作日**

---

## 5. 验收标准

Phase 2 完成标志：
1. ✅ 因子库≥15个因子，覆盖估值/成长/质量/技术/规模五类
2. ✅ 批量计算因子值入库，带缓存机制
3. ✅ IC分析：输出每个因子的IC均值/ICIR/正比例
4. ✅ 分层回测：5层分层，多空收益、单调性可视化
5. ✅ 中性化可选，对比中性前后效果
6. ✅ 因子筛选：自动筛出ICIR≥0.5的有效因子清单
7. ✅ Dashboard展示因子检验结果