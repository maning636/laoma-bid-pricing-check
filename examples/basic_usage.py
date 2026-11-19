"""最小可跑示例：三行代码核查一份投标报价文本。

运行：
    python examples/basic_usage.py
"""
from __future__ import annotations

import asyncio

from skill_engine import SkillContext
from skills.pricing_check import PricingCheckSkill

# 一份典型的问题报价：第 2 项算错 3 万，总价又贴着限价
BID_TEXT = """
投标总价：98.5万

总金额：玖拾捌万伍仟元（985000）

1. 服务器 12.50 × 8 = 100.00
2. 交换机 3.20 × 10 = 35.00
"""


async def main() -> None:
    ctx = SkillContext(
        project_id="demo",
        db=None,
        llm=None,                      # 本技能不用大模型
        parameters={
            "bid_text": BID_TEXT,
            "max_price": 100.0,        # 最高限价（万元）
        },
    )
    result = await PricingCheckSkill().execute(ctx)

    if not result.success:
        print("执行失败:", result.error)
        return

    data = result.data
    s = data["summary"]
    print(f"风险等级: {data['risk_level']}")
    print(f"共 {s['total']} 项检查：通过 {s['passed']} / 失败 {s['failed']} / 提示 {s['warning']}")
    print()
    for c in data["checks"]:
        icon = {"pass": "OK  ", "warning": "WARN", "fail": "FAIL"}[c["status"]]
        print(f"[{icon}] {c['check_type']:16s} {c['detail']}")


if __name__ == "__main__":
    asyncio.run(main())
