# pricing_check · 报价算术核查

检查投标报价的四类算术风险，用于废标预防。纯规则判定，不调用大模型，不依赖数据库。

## 输入

`execute` 只读 `ctx.parameters`，全部可选：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `tender_text` | str | 否 | 招标文件文本（保留以兼容契约，本技能不解析） |
| `bid_text` | str | 否 | 投标文件文本，用于提取投标总价、大小写金额对照与算术行 |
| `max_price` | float | 否 | 最高限价（万元）；缺省时最高限价/安全区间检查降级为 warning |

## 输出

`SkillResult.success = True`，`data` 结构：

```json
{
  "checks": [
    {"check_type": "price_limit", "status": "pass|warning|fail", "detail": "...",
     "evidence_level": "verdict", "basis": "...", "checked": true},
    {"check_type": "upper_lower_case", "status": "...", "detail": "..."},
    {"check_type": "arithmetic", "status": "...", "detail": "..."},
    {"check_type": "safe_range", "status": "...", "detail": "..."}
  ],
  "summary": {"total": 4, "passed": 3, "failed": 1, "warning": 0},
  "risk_level": "high|low"
}
```

## 检查项

1. **最高限价**（`price_limit`）：投标总价是否 ≤ 最高限价。无限价或未提取到总价 → `warning`；超限 → `fail`。
2. **大小写金额对照**（`upper_lower_case`）：检测 `壹万元（10000）` 一类的对照是否存在；仅检测存在性，一致性需人工确认。无对照 → `warning`。
3. **单位×数量=合价**（`arithmetic`）：逐行验证 `单价 × 数量 = 合价`，仅报告算术不符的行；全部自洽或未检测到算术行 → `pass`。
4. **安全区间**（`safe_range`）：报价/限价比例是否落在 95%~98% 的安全带。低于 95% → `warning`；超过 98% → `fail`。

## 属性

- `name = "pricing_check"`，`category = "check"`，`version = "1.0.0"`
- `triggers = ["报价", "算术", "价格核查"]`
