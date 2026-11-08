"""工具注册：把函数实现注册成可供大模型调用的工具（function calling schema）。"""
from skills_loader import read_reference
from tools.compliance import check_compliance
from tools.cost import estimate_landed_cost
from tools.tariff_db import query_tariff

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_compliance",
            "description": "查询某产品出口到某国的认证/准入要求（强制项/建议项分列，含法规编号、跳过后果、成本区间、周期）。覆盖：儿童玩具/不锈钢食品接触容器/锂电池充电宝/蓝牙耳机音箱。",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "目的国，如：美国"},
                    "product": {"type": "string", "description": "产品名，如：儿童声光电动早教玩具"},
                },
                "required": ["destination", "product"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_landed_cost",
            "description": "测算某产品出口到某国的到岸成本（关税/MPF/HMF/物流/危险品附加/认证摊薄/风险备用金）。mode 区分「直邮小包」与「FBA大批量」。",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "目的国，如：美国"},
                    "product": {"type": "string", "description": "产品名，如：儿童声光电动早教玩具"},
                    "unit_value_usd": {"type": "number", "description": "单品申报价值（美元）"},
                    "quantity": {"type": "integer", "description": "数量（件）"},
                    "mode": {"type": "string", "enum": ["直邮小包", "FBA大批量"], "description": "走货方式"},
                    "has_lithium_battery": {"type": "boolean", "description": "是否含锂电池"},
                    "tariff_rate_pct": {"type": "number", "description": "可选：产品不在税率库时，由模型估算的有效关税税率百分比（MFN+附加）"},
                },
                "required": ["destination", "product", "unit_value_usd", "quantity", "mode", "has_lithium_battery"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_tariff",
            "description": "直接查某产品出口到某国的当前有效关税税率（分层：基础关税[稳定，美国MFN/印度BCD/俄EAEU] + 附加税[政策波动]），带来源与更新时间。",
            "parameters": {
                "type": "object",
                "properties": {
                    "product": {"type": "string", "description": "产品名，如：儿童声光电动早教玩具"},
                    "destination": {"type": "string", "description": "目的国，默认美国"},
                },
                "required": ["product"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_skill_reference",
            "description": "读取技能库中某技能的参考资料（如回复模板 templates.md、服务手册 service-playbook.md、语言风格指南等）。ref 留空则列出该技能下的文件清单。",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill": {"type": "string", "description": "技能名，如 trade-reply-templates"},
                    "ref": {"type": "string", "description": "参考资料相对路径，如 references/templates.md；留空列出文件清单"},
                },
                "required": ["skill"],
            },
        },
    },
]

_TOOL_IMPL = {
    "check_compliance": check_compliance,
    "estimate_landed_cost": estimate_landed_cost,
    "query_tariff": query_tariff,
    "read_skill_reference": read_reference,
}


def dispatch_tool(name: str, args: dict):
    """按名称执行工具，任何异常都转成结构化错误返回，避免打断循环。"""
    fn = _TOOL_IMPL.get(name)
    if fn is None:
        return {"error": f"未知工具：{name}"}
    try:
        return fn(**args)
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}
