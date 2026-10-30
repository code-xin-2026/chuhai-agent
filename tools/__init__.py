"""工具注册：把函数实现注册成可供大模型调用的工具（function calling schema）。"""
from tools.compliance import check_compliance
from tools.cost import estimate_landed_cost
from tools.tariff_db import query_tariff

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_compliance",
            "description": "查询某产品出口到某国的认证/准入要求，含「跳过某认证的后果(risk)」与一次性认证成本。",
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
                },
                "required": ["destination", "product", "unit_value_usd", "quantity", "mode", "has_lithium_battery"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_tariff",
            "description": "直接查某产品出口到某国的当前有效关税税率（分层：最惠国MFN/存量301/IEEPA/新301强迫劳动），带来源与更新时间。",
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
]

_TOOL_IMPL = {
    "check_compliance": check_compliance,
    "estimate_landed_cost": estimate_landed_cost,
    "query_tariff": query_tariff,
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
