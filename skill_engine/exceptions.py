"""技能引擎的最小异常集（独立包只保留技能相关错误）。"""


class SkillNotFoundError(Exception):
    """请求的 skill 未注册，或已被下线。"""


class SkillExecutionError(Exception):
    """技能执行失败（基类统一包装后的对外错误）。"""
