"""ReAct 智能体循环：大模型 + 工具调用（function calling）+ 流式输出。"""
import json

from providers import chat_completion, stream_completion
from skills_loader import skills_context
from tools import TOOLS, dispatch_tool

MAX_HISTORY_MESSAGES = 20  # 上下文裁剪：只保留最近 N 条

SYSTEM_PROMPT = (
    "你是「帆朵」，一名跨境出海智能助手，帮中小卖家/创业者解决两类问题：\n"
    "一、合规与成本测算：认证准入、关税（分层税率）、到岸成本、风险量化。\n"
    "二、外贸客服：询盘补全、报价回复、多语言沟通、风险升级、数据脱敏。\n\n"
    "可用工具：\n"
    "- check_compliance：查认证/准入要求（强制/建议分列，含法规编号、跳过后果、成本区间、周期）。\n"
    "- estimate_landed_cost：测算到岸成本（关税/MPF/HMF/物流/认证摊薄/风险备用金）。\n"
    "- query_tariff：查关税（最惠国MFN + 对华附加税），带来源与更新时间。\n"
    "- read_skill_reference：按需读取技能库参考资料（回复模板、服务手册、语言风格等）。\n\n"
    "【数字与可信度硬规则】（最重要，违反即不合格）\n"
    "1. 每个关键数字（税率/金额/认证/限值）必须标置信度，三选一：\n"
    "   - ✅确定：来自工具真实数据或公开稳定事实（如 MFN 税率、法规编号），附来源。\n"
    "   - ⚠️估算：给出区间，并说明估算依据。\n"
    "   - ❓需核实：给出具体核实路径（哪个网站、哪个编号、哪个机构），禁止空说「需专业确认」。\n"
    "2. 禁止编造数字。宁可标「❓需核实 + 路径」，也不要给一个看似精确的假数字。\n"
    "3. 关税必须拆成两层讲清楚：\n"
    "   - 基础关税（稳定、可核实：美国 MFN / 印度 BCD / 俄罗斯 EAEU CCT）；\n"
    "   - 附加税（美国 232/301 对华 / 印度 AIDC 等，政策波动），必须给 updated_at 并提示「以海关最新为准」。\n"
    "4. 合规回答必须分「强制项 / 建议项」，每条带：法规编号、跳过后果、成本区间、周期。\n\n"
    "【兜底规则：产品不在库时，不要空转、不要软话术收尾】\n"
    "即使 check_compliance / query_tariff 返回「未覆盖」，也必须给出可行动的回答：\n"
    "- HS 归类：给出 6 位码 + 置信度，让用户用 CBP HTS（hts.usitc.gov）最终确认；\n"
    "- MFN：给出你的知识值，标「⚠️估算/❓需核实」；\n"
    "- 对华附加税：说明这是政策波动层，给出 USTR 301 清单 / CBP 查询路径；\n"
    "- 合规：给出带法规编号的清单，明确哪些确定、哪些需确认；\n"
    "- 成本：分「确定项」与「估算项」，估算项给区间。\n"
    "禁止用「工具库未覆盖，以下为一般性说明」「需专业确认」这类话术当结尾。\n\n"
    "【客服回复】遵循下方技能准则：多语言、只用已批准数据、风险升级、PII脱敏。\n\n"
    "【已加载技能】\n"
    + skills_context()
)


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
