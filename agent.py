"""ReAct 智能体循环：大模型 + 工具调用（function calling）。"""
import json

from providers import chat_completion
from tools import TOOLS, dispatch_tool

SYSTEM_PROMPT = """你是「跨境出海合规与成本测算助手」，帮中小卖家评估把产品出口到海外目标国的合规要求与到岸成本。

当前唯一在册案例：美国 · 儿童声光电动早教玩具。

可用工具：
- check_compliance：查认证/准入要求，含「跳过某认证的后果(risk)」与一次性成本。
- estimate_landed_cost：测算到岸成本（关税从 HS 税率库实时查询，mode 区分「直邮小包」/「FBA大批量」）。
- query_tariff：直接查某产品的当前有效关税（分层：MFN/存量301/IEEPA/新301），带来源与更新时间。

工作方式：
1. 先理解用户的产品、目的国、单价、数量、是否含锂电池、走货方式；信息不全时礼貌追问。
2. 查合规（check_compliance）与关税（query_tariff 或随 estimate_landed_cost 返回）。
3. 若用户要对比两种走货方式，estimate_landed_cost 分别调用两次（mode 不同）再对比。
4. 输出结构化中文小结：认证清单与一次性投入 → 关税构成与到岸成本对比 → 风险量化（跳过CPC等后果）→ 建议。

硬性要求：
- 所有数字（税率、金额、认证、限值）必须来自工具返回结果，不得凭空编造。
- 关税要如实说明「分层构成 + 来源 + 更新时间」，并提示「以海关实时税率为准」；金额为估算值的要注明。
- 问到数据范围之外的国家/产品，如实说明「当前仅覆盖美国·儿童声光电动早教玩具」。"""


def run_agent(user_message: str, history: list, max_steps: int = 8):
    """执行一次对话。history 为之前的 user/assistant 消息列表（不含本次）。"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_message})

    trace = []
    for _ in range(max_steps):
        resp = chat_completion(messages, tools=TOOLS)
        msg = resp.choices[0].message
        provider = getattr(resp, "_provider_name", "?")

        if msg.tool_calls:
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            })
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = dispatch_tool(name, args)
                trace.append({
                    "step": len(trace) + 1,
                    "provider": provider,
                    "tool": name,
                    "args": args,
                    "result": result,
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })
        else:
            return (msg.content or ""), trace

    return "（已达到最大推理步数，为安全起见停止。请稍后重试或换种问法。）", trace
