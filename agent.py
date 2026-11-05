"""ReAct 智能体循环：大模型 + 工具调用（function calling）+ 流式输出。"""
import json

from providers import chat_completion, stream_completion
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

MAX_HISTORY_MESSAGES = 20  # 上下文裁剪：只保留最近 N 条，防止对话过长变慢变贵


def _build_messages(user_message, history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    recent = history[-MAX_HISTORY_MESSAGES:]
    messages += [{"role": m["role"], "content": m["content"]} for m in recent]
    messages.append({"role": "user", "content": user_message})
    return messages


def _tool_calls_message(msg):
    return {
        "role": "assistant",
        "content": msg.content,
        "tool_calls": [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ],
    }


def _safe_args(tc):
    try:
        return json.loads(tc.function.arguments or "{}")
    except json.JSONDecodeError:
        return {}


def _usage_of(resp):
    try:
        u = resp.usage
        return {"prompt": u.prompt_tokens, "completion": u.completion_tokens, "total": u.total_tokens}
    except Exception:  # noqa: BLE001
        return None


def stream_agent(user_message, history, max_steps=8):
    """流式智能体。产出事件：
    {"type":"tool", step, provider, tool, args, result}   # 工具执行（实时状态）
    {"type":"text", text}                                  # 最终回答增量（流式）
    {"type":"done", answer, trace, provider, usage}        # 结束
    """
    messages = _build_messages(user_message, history)
    trace = []
    provider = "?"
    for _ in range(max_steps):
        resp = chat_completion(messages, tools=TOOLS)
        msg = resp.choices[0].message
        provider = getattr(resp, "_provider_name", "?")
        usage = _usage_of(resp)

        if msg.tool_calls:
            messages.append(_tool_calls_message(msg))
            for tc in msg.tool_calls:
                args = _safe_args(tc)
                result = dispatch_tool(tc.function.name, args)
                step = {"step": len(trace) + 1, "provider": provider,
                        "tool": tc.function.name, "args": args, "result": result}
                trace.append(step)
                yield {"type": "tool", **step}
                messages.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": json.dumps(result, ensure_ascii=False)})
        else:
            # 最终回答：重新以流式请求产出（不带 tools，确保只返回文本）
            full = []
            sp = provider
            try:
                stream, sp = stream_completion(messages, tools=None)
                for chunk in stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta and delta.content:
                        full.append(delta.content)
                        yield {"type": "text", "text": delta.content}
            except Exception:  # noqa: BLE001
                fallback = msg.content or "（生成失败，请重试）"
                full = [fallback]
                yield {"type": "text", "text": fallback}
            yield {"type": "done", "answer": "".join(full), "trace": trace,
                   "provider": sp, "usage": usage}
            return

    yield {"type": "text", "text": "（已达到最大推理步数，为安全起见停止。请稍后重试或换种问法。）"}
    yield {"type": "done", "answer": "（已达到最大推理步数）", "trace": trace,
           "provider": provider, "usage": None}


def run_agent(user_message, history, max_steps=8):
    """非流式包装（用于测试/兜底），返回 (answer, trace)。"""
    parts = []
    trace = []
    for ev in stream_agent(user_message, history, max_steps):
        if ev["type"] == "text":
            parts.append(ev["text"])
        elif ev["type"] == "tool":
            trace.append({k: ev[k] for k in ("step", "provider", "tool", "args", "result")})
    return "".join(parts), trace
