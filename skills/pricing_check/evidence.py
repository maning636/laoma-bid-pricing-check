"""检查结论的「依据分级」helper（步骤④合规自检的可信度基建）。

在 check 结果的汇聚层给每条 verdict/item 补三个字段：

- ``evidence_level: "verdict" | "hint"``
    ``verdict`` = 确定性规则可判定（如缺少投标函、有效期缺失、字段冲突、算术错误）；
    ``hint``    = 需要人工判断的提示（如技术方案质量、文案风险、语义模糊）
- ``basis: str`` —— 该条结论依据的规则名 / 一句话检查逻辑
- ``checked: bool`` —— ``False`` 表示「未核」（文件缺失对应部分 / 解析失败 / 该维度被跳过）；
  未核绝不能显示为通过

与 ``_atomic.py`` 里的 ``evidence`` 字段（section_ref / chunk_id / bid_sections）
正交：本模块回答"这条结论有多确定"，``evidence`` 字段回答"证据在哪"。

本模块只包含纯函数、无副作用；``enrich_evidence`` 就地修改传入 dict 但**只增**，
不删除、不覆盖任何已存在字段。
"""

from __future__ import annotations

from typing import Any

# ── 分级常量 ──────────────────────────────────────────────
EVIDENCE_VERDICT = "verdict"
EVIDENCE_HINT = "hint"

# 沿用 _confidence.THRESHOLD_CHECK 的语义：≥0.80 视为可判定，<0.80 或 None 保守判 hint
_VERDICT_CONFIDENCE_THRESHOLD = 0.80

# 无 status / status == "unknown" 的 item 一律视为未核
_UNCHECKED_STATUSES = frozenset({"", "unknown", "unchecked", "skipped"})

# ── skill name → 默认 basis 文案 ────────────────────────
_DEFAULT_BASIS: dict[str, str] = {
    "compliance_check": "对照招标文件'必须/应当/禁止'类硬性条款逐条判定合规性",
    "mandatory_req_check": "★▲ 实质性要求逐项比对，未满足即不合规",
    "pricing_check": "最高限价 / 大小写金额对照 / 单位×数量=合价 / 安全区间四类算术规则",
    "signature_check": "签章、公章、骑缝章、CA 数字证书等法定要件齐全性",
    "validity_check": "投标 / 保函 / 证书 / CA 有效期均覆盖招标截止时间",
    "qualification_check": "资质等级 / 证书 / 业绩 / 许可满足招标要求",
    "deposit_check": "投标保证金形式 / 金额 / 时效满足招标要求",
    "consistency_check": "投标文件内部各章节数据一致性",
    "disqualification_check": "命中招标废标条款即废标",
    "cross_check": "跨章节（要求 / 响应 / 报价）逻辑一致性",
    "duplicate_check": "重复条目 / 重复文本检测",
    "doc_integrity_check": "标书文件完整性（缺页 / 乱码 / 目录一致）",
    "ai_text_check": "AI 生成痕迹（句式 / 术语 / 重复率）",
    "fit_score": "评分办法对照打分",
    "risk_score": "多因子加权综合风险评分",
    "collusion_score": "围标串标嫌疑（雷同 / 关联关系）",
    "sample_report_check": "对标样板报告结构完整性",
    "joint_bid_check": "联合体资质 / 协议合规性",
    "ebid_submit_check": "电子投标提交格式 / 签名完整性",
    "pricing_logic_check": "报价内部逻辑（分项 - 汇总 - 总价一致性）",
    "anon_bid_clean": "暗标去公司标识残留",
    "selfcheck_list": "自检清单逐项确认",
}

_FALLBACK_BASIS = "检查规则（依据 skill 内置逻辑，未显式声明 basis）"


# ═════════════════════════════════════════════════════════
# helper
# ═════════════════════════════════════════════════════════
def make_evidence(level: str, basis: str) -> dict:
    """构造 evidence 三字段（``checked`` 默认 ``True``）。

    Args:
      level: 只能是 ``EVIDENCE_VERDICT`` 或 ``EVIDENCE_HINT``；其他值一律降级为 hint，
             避免拼写错误悄悄变成 verdict。
      basis: 依据说明，不允许为空（空串会被保留但强烈不建议）。

    Returns:
      ``{"evidence_level": ..., "basis": ..., "checked": True}``
    """
    lvl = EVIDENCE_VERDICT if level == EVIDENCE_VERDICT else EVIDENCE_HINT
    return {
        "evidence_level": lvl,
        "basis": basis,
        "checked": True,
    }


def mark_unchecked(reason: str) -> dict:
    """构造「未核」条目：``checked=False`` + ``evidence_level=hint`` + ``basis=reason``。

    ``reason`` 为空时回退到通用兜底文案。
    """
    return {
        "evidence_level": EVIDENCE_HINT,
        "basis": reason or "检查维度未核",
        "checked": False,
    }


def map_confidence_to_level(
    confidence: Any,
    *,
    needs_review: bool = False,
) -> str:
    """把既有 ``confidence`` 分级映射为 ``evidence_level``。

    路由：
    - ``needs_review=True`` 恒为 ``hint``（LLM 判定不稳，需人工复核）
    - ``confidence >= 0.80`` → ``verdict``（沿用 _confidence.THRESHOLD_CHECK 阈值）
    - ``confidence`` 缺失 / None / 非数值 / <0.80 → ``hint``
    """
    if needs_review:
        return EVIDENCE_HINT
    if confidence is None:
        return EVIDENCE_HINT
    try:
        c = float(confidence)
    except (TypeError, ValueError):
        return EVIDENCE_HINT
    return EVIDENCE_VERDICT if c >= _VERDICT_CONFIDENCE_THRESHOLD else EVIDENCE_HINT


def default_basis(skill_name: str) -> str:
    """skill name → 默认 basis 文案；未登记时使用通用兜底。"""
    if not skill_name:
        return _FALLBACK_BASIS
    return _DEFAULT_BASIS.get(skill_name, _FALLBACK_BASIS)


# ═════════════════════════════════════════════════════════
# 汇聚层入口
# ═════════════════════════════════════════════════════════
def _collect_items(payload: dict) -> list[dict]:
    """从 payload 里取出所有 verdict 级 item（``items`` 优先，其次 ``checks``）。"""
    items = payload.get("items")
    if isinstance(items, list):
        return [x for x in items if isinstance(x, dict)]
    checks = payload.get("checks")
    if isinstance(checks, list):
        return [x for x in checks if isinstance(x, dict)]
    return []


def _item_status_is_unchecked(status: Any) -> bool:
    """判定 item 的 status 是否属于「未核」集合。"""
    if status is None:
        return True
    if not isinstance(status, str):
        return True
    return status.lower() in _UNCHECKED_STATUSES


def _enrich_item(item: dict, basis: str) -> None:
    """就地给 item 补 evidence_level / basis / checked（只增，不覆盖）。"""
    # skill 层已显式声明 evidence_level + basis 时，尊重原值
    explicit = item.get("evidence_level") and item.get("basis")
    if explicit:
        item.setdefault("checked", True)
        return

    # 从 confidence 分级映射 evidence_level；无 confidence 默认 hint
    level = map_confidence_to_level(
        item.get("confidence"),
        needs_review=bool(item.get("needs_review")),
    )
    item.setdefault("evidence_level", level)
    if not item.get("basis"):
        item["basis"] = basis or _FALLBACK_BASIS

    # 判断 checked：status 缺失 / unknown / unchecked / skipped → 未核
    if _item_status_is_unchecked(item.get("status")):
        item["checked"] = False
        if not item.get("basis"):
            item["basis"] = "未核：状态未知或该维度未产生判定"
    else:
        item.setdefault("checked", True)


def enrich_evidence(payload: Any, *, skill_name: str = "") -> Any:
    """在 check 结果 payload 上就地注入 evidence_level / basis / checked。

    行为：
    1. 对 ``payload.items`` 或 ``payload.checks`` 中每条 dict item 就地注入
       ``evidence_level`` / ``basis`` / ``checked``：
       - 已有 ``evidence_level`` + ``basis`` → 尊重原值，仅补 ``checked`` 默认值
       - 无则按 confidence 映射，无 confidence 默认 hint；basis 用 skill 默认文案
       - ``status`` 缺失 / ``"unknown"`` / ``"unchecked"`` / ``"skipped"`` → ``checked=False``
    2. 若 payload 完全没有 ``items`` / ``checks``（或都是空列表）→ 顶层注入
       ``checked=False`` + ``unchecked_reason``；防止 UI 把空结果误判为通过
    3. 顶层追加 ``evidence_summary``：
       ``{total, checked, unchecked, verdict, hint}``
    4. **不删、不改任何既有字段**（只增）

    Args:
      payload: skill 返回的 data dict；就地修改并返回
      skill_name: 用于查默认 basis；空串时 basis 用通用兜底文案

    Returns:
      原 payload（就地修改）
    """
    if not isinstance(payload, dict):
        return payload

    basis = default_basis(skill_name)
    items = _collect_items(payload)

    for item in items:
        _enrich_item(item, basis)

    if items:
        checked_n = sum(1 for i in items if i.get("checked"))
        verdict_n = sum(1 for i in items if i.get("evidence_level") == EVIDENCE_VERDICT)
        hint_n = sum(1 for i in items if i.get("evidence_level") == EVIDENCE_HINT)
        payload["evidence_summary"] = {
            "total": len(items),
            "checked": checked_n,
            "unchecked": len(items) - checked_n,
            "verdict": verdict_n,
            "hint": hint_n,
        }
    else:
        # 无 items/checks → 整个维度视为未核
        payload.setdefault("checked", False)
        payload.setdefault("unchecked_reason", "该检查维度未产生条目（无数据 / 跳过 / 解析失败）")
        payload.setdefault("evidence_level", EVIDENCE_HINT)
        payload.setdefault("basis", basis)
        payload["evidence_summary"] = {
            "total": 0,
            "checked": 0,
            "unchecked": 0,
            "verdict": 0,
            "hint": 0,
        }

    return payload
