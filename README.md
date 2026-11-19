# bidmaster-pricing-check

**投标报价算术核查** —— 一个技能，一个职责：把报价表里那些「人工核必漏」的算术错误查出来。

零第三方依赖，纯规则判定，不调用任何大模型。`pip install` 后三行代码可用。

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)](pyproject.toml)

---

## 为什么需要它

投标报价表里的算术错误是**真实废标风险**，而且人眼极难查全：

- 单价 × 数量 ≠ 合价（一项算错，整表连锁错）
- 大写金额与小写金额不一致
- 投标总价超过最高限价（一分钱也是废标）
- 报价落在「明显不合理」区间，被评标质疑

一份几百行的清单，人工核对一遍要几十分钟，还容易漏。这个技能 1 秒跑完，逐条给结论。

## 四项检查

| 检查项 | 判定依据 | 输出 |
|---|---|---|
| `price_limit` | 投标总价 ≤ 最高限价 | 超出即 `fail` |
| `upper_lower_case` | 大写金额与小写金额对照是否存在 | 未找到即 `warning`（一致性仍需人工确认） |
| `arithmetic` | 逐行 `单价 × 数量 = 合价` | 误差 > 0.01 即 `fail`，报出具体行号 |
| `safe_range` | 报价/限价比例是否落在 95%~98% | 超出即 `fail` |

每项返回 `status ∈ {pass, warning, fail}` + `detail` 说明。

## 安装

```bash
pip install git+https://github.com/maning636/bidmaster-pricing-check.git
```

本技能**零运行时依赖**（只用标准库），安装很快。

## 快速开始

```python
import asyncio
from skill_engine import SkillContext
from skills.pricing_check import PricingCheckSkill

bid_text = """
投标总价：98.5万

总金额：玖拾捌万伍仟元（985000）

1. 服务器 12.50 × 8 = 100.00
2. 交换机 3.20 × 10 = 35.00
"""

ctx = SkillContext(
    project_id="demo",
    db=None,
    llm=None,                      # 本技能不用大模型
    parameters={
        "bid_text": bid_text,
        "max_price": 100.0,        # 最高限价（万元），可选
    },
)

result = asyncio.run(PricingCheckSkill().execute(ctx))
print(result.data["risk_level"])   # high
for c in result.data["checks"]:
    print(c["status"], c["check_type"], c["detail"])
```

输出：

```
high
pass    price_limit      投标总价98.5万未超过限价100.0万
warning upper_lower_case 未检测到大小写金额对照
fail    arithmetic       第2项: 3.2×10.0=32.00≠35.0
fail    safe_range       报价为限价98.5%，超出98%安全带上限
```

上面这个例子里，第 2 项单价×数量算错了 3 万，报价又踩在安全带外 —— 两处都会被人工漏掉。

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `bid_text` | `str` | 建议 | 投标文件文本。技能从中提取投标总价、大小写金额、算术行 |
| `max_price` | `float` | 可选 | 最高限价（万元）。缺省时限价与安全区间检查降级为 `warning` |
| `tender_text` | `str` | 可选 | 保留以兼容契约，本技能不解析 |

## 输出结构

```json
{
  "checks": [
    {
      "check_type": "arithmetic",
      "status": "fail",
      "detail": "第2项: 3.2×10.0=32.00≠35.0",
      "evidence_level": "verdict",
      "basis": "最高限价 / 大小写金额对照 / 单位×数量=合价 / 安全区间四类算术规则",
      "checked": true
    }
  ],
  "summary": {"total": 4, "passed": 1, "failed": 2, "warning": 1},
  "risk_level": "high"
}
```

`risk_level` 规则：任一 `fail` → `high`，否则 `low`。

## 边界（诚实说明）

- **只查算术与格式**，不判断报价是否「合理」、不预测中标概率
- **不做定额组价、不读工程量清单 Excel** —— 那是造价产品线的事
- `upper_lower_case` 只检测**是否存在**对照，一致性仍需人工确认（中文大写规则复杂，误判成本高于收益）
- 正则匹配针对**常见排版**（`1. 名称 单价 × 数量 = 合价`）。特殊格式可能漏匹配，此时该项会返回 `warning` 而非静默通过

## 测试

```bash
pip install -e ".[dev]"
pytest
```

## 许可

**AGPL-3.0**。全文见 `LICENSE`。

本技能派生自 AGPL-3.0 上游项目 [BidMaster-Pro](https://github.com/guangshu100/BidMaster-Pro)（经由「老马标书贤内助」主仓），因此必须保持 AGPL-3.0。上游归属见 `NOTICE`。

如果你**分发**本库（含修改版、含打包进你的产品），AGPL-3.0 要求你保留归属声明并向接收者提供完整对应源代码。仅在组织内部使用不触发该义务。

## 相关

本仓库是「老马标书贤内助」技能体系的**最小切片**，刻意只放一个技能，便于独立使用与评估。完整技能集（Word 排版、文档脱敏、规则筛查、风险评分等 8 个）见主仓。
