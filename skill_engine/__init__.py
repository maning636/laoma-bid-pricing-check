"""技能引擎 —— 只保留 ``pricing_check`` 需要的三个数据契约。

本仓库是「老马标书贤内助」技能体系的最小开源切片：只导出

- ``Skill``        ：技能抽象基类（子类实现 ``execute``）
- ``SkillContext`` ：执行上下文（携带 parameters / llm / db 等）
- ``SkillResult``  ：执行结果（success / data / error / warnings）

刻意**不**包含 ``SkillRegistry`` 与 ``SkillLoader``：本仓库只有一个技能，
不需要磁盘发现与进程内注册表。需要完整引擎的，见主仓或 ``bidmaster-skills``。
"""

from __future__ import annotations

from .base import Skill, SkillContext, SkillResult
from .exceptions import SkillExecutionError, SkillNotFoundError

__all__ = [
    "Skill",
    "SkillContext",
    "SkillResult",
    "SkillExecutionError",
    "SkillNotFoundError",
]
