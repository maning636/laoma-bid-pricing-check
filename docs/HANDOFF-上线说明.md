# 给下游 Agent · 上线说明

> 本文件是给接手「把这个技能推到网上」的 Agent 看的。读完即可开工，不需要主会话上下文。

---

## 1. 现状（已完成）

| 项 | 状态 |
|---|---|
| 代码仓库 | ✅ 已建：`D:/dim开发/bidmaster-skills-pricing` |
| GitHub 公开库 | ✅ 已推：https://github.com/maning636/bidmaster-pricing-check |
| 可见性 | **Public**（当前） |
| 测试 | ✅ 22 条全绿 |
| 从 GitHub 安装 | ✅ 实测通过（`pip install git+https://...`） |
| 许可 | AGPL-3.0 + NOTICE（上游 BidMaster-Pro 归属已写清） |
| 示例 | ✅ `examples/basic_usage.py` 可直接跑 |

**代码侧不用再动。** 剩下的都是「让它更容易被找到 / 更容易被用」的运营工作。

---

## 2. 这个技能是什么

**投标报价算术核查**。一句话：把报价表里那些「人工核必漏」的算术错误查出来。

四类检查：

| 检查项 | 判定 |
|---|---|
| `price_limit` | 投标总价 ≤ 最高限价，超出即 fail |
| `upper_lower_case` | 大写金额与小写金额对照是否存在 |
| `arithmetic` | 逐行 `单价 × 数量 = 合价`，误差 >0.01 报出具体行号 |
| `safe_range` | 报价/限价比例是否落在 95%~98% |

**零第三方运行时依赖**（只用标准库），不调大模型。

---

## 3. 你要做的事（按优先级）

### P0 · 验证当前状态（0.5 小时）

先确认我这边的结论，不要盲目接手：

```bash
cd /tmp && rm -rf _verify && mkdir _verify && cd _verify
"D:/dim开发/_bidmaster/.venv/Scripts/python.exe" -m pip install --no-deps --target ./site \
  "git+https://github.com/maning636/bidmaster-pricing-check.git"
PYTHONPATH=./site "D:/dim开发/_bidmaster/.venv/Scripts/python.exe" -c "
import asyncio
from skill_engine import SkillContext
from skills.pricing_check import PricingCheckSkill
ctx = SkillContext(project_id='x', db=None, llm=None,
    parameters={'bid_text':'投标总价：105万', 'max_price':100.0})
r = asyncio.run(PricingCheckSkill().execute(ctx))
print('risk:', r.data['risk_level'])   # 期望 high（超限价）
"
```

浏览器打开 https://github.com/maning636/bidmaster-pricing-check 确认 README 渲染正常。

### P1 · 补 GitHub 仓库元信息（1 小时）

现在仓库是「裸」的，缺这些：

| 项 | 做法 |
|---|---|
| **Topics（标签）** | 进仓库 Settings → Topics，加：`bidding` `tender` `chinese` `procurement` `bid-check` `python` `skill` `agpl` `招投标` `标书` |
| **About 描述** | 用一句中文 + 一句英文，例：「投标报价算术核查 · 零依赖 · 不调大模型 / Arithmetic checks for Chinese tender bid pricing」 |
| **Website** | 若有官网就填（当前无，可留空） |
| **Release v0.1.0** | 打 tag `v0.1.0`，Release notes 用 `CHANGELOG` 风格写四类检查 + 零依赖 + 安装命令 |
| **CI** | 加 `.github/workflows/ci.yml`：Python 3.10/3.11/3.12 × `pytest` |

**CI 模板**（可直接用）：

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest
```

### P2 · 让它在 PyPI 可装（2 小时）

现在只能 `pip install git+https://...`，不够友好。推到 PyPI 后：

```bash
pip install bidmaster-pricing-check
```

步骤：
1. `pip install build twine`
2. `python -m build`
3. `twine upload dist/*`（需 PyPI 账号 + API token，**要用户提供**）
4. 先发 TestPyPI 验证：`twine upload --repository testpypi dist/*`

**注意**：包名 `bidmaster-pricing-check` 在 PyPI 上可能已被占，先查 https://pypi.org/project/bidmaster-pricing-check/

### P3 · 内容分发（1–2 天，看用户意愿）

| 渠道 | 做什么 |
|---|---|
| **掘金 / 知乎 / CSDN** | 写一篇「投标报价 3 类算术错误，人工核必漏」的技术文，末尾带仓库链接 |
| **V2EX / Reddit r/Python** | 英文版短帖，讲「零依赖的领域技能」这个角度 |
| **微信公众号** | 用户自己的号，讲实战案例（真实废标风险） |

**内容角度建议**：不要写「我做了个工具」，写「这 3 个算术错误会让你直接废标，附检测脚本」。前者没人看，后者有搜索价值。

---

## 4. 未来要「封闭」这个库（用户明确提过）

用户说「未来之后把它封闭掉」。两种做法：

| 方案 | 做法 | 影响 |
|---|---|---|
| **A. 转私有** | Settings → 底部 Danger Zone → Change visibility → Private | 已 clone 的人不受影响；GitHub 搜索不再收录；但**已 fork 的不会消失** |
| **B. 归档 + 转私有** | 先 Archive（只读），再转 Private | 更彻底，明确表示「不再维护」 |

**注意 AGPL 义务**：如果之前**已经分发给别人**（有人 clone / pip install 过），AGPL 要求你向他们提供源码。转私有**不能追溯撤销**已发生的分发义务。

转私有前建议：先确认没有外部依赖者，或提前公告。

---

## 5. 红线（违反会出事）

1. **不许改许可证**：AGPL-3.0 是事实性约束（派生自 BidMaster-Pro），改 MIT 是违法的
2. **不许删 NOTICE 的上游归属**
3. **不许把主仓的提示词、评分模型、私有知识库能力搬进来**
4. **不许用真实标书做示例**（当前示例是构造文本，保持这样）
5. **不许 `git push --force`**（已公开的仓库，force push 会破坏别人的 clone）

---

## 6. 需要用户提供的东西

| 项 | 用途 |
|---|---|
| PyPI 账号 / API token | P2 发版 |
| 官网地址 | P1 的 Website 字段、README 社群区 |
| 微信公众号 / 二维码 | README 社群区（当前未放） |

---

## 7. 验收标准

做完 P0–P1 后应达到：

- [ ] `pip install git+https://github.com/maning636/bidmaster-pricing-check.git` 成功
- [ ] GitHub 页面 Topics ≥ 6 个、About 描述已填
- [ ] Release `v0.1.0` 已发布
- [ ] CI 徽章显示 passing
- [ ] README 在 GitHub 上渲染正常（表格、代码块、徽章都对）
- [ ] 外部人（非本机）能装能跑

---

## 8. 参考

- 主仓：`D:/dim开发/_bidmaster`
- 完整技能集（8 个）：`D:/dim开发/bidmaster-skills`（另一个私有库）
- 本仓库设计说明：`README.md`
- 上游归属：`NOTICE`
