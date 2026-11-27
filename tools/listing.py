"""本地化 Listing 生成（LLM）+ 违禁/夸大词自检。

让智能体不只是「查资料」，还能「产出可直接用的内容」——
这是从「问答式 chatbot」到「能交付结果的 agent」的关键一步。
"""
from providers import chat_completion

_BAN_WORDS = [
    "best", "#1", "no.1", "no 1", "top rated", "guaranteed", "guarantee",
    "100%", "cure", "heal", "medical", "fda approved", "anti-virus",
    "antibacterial", "cheapest", "perfect", "miracle", "free shipping",
    "best seller", "premium quality",
    "最好", "第一", "顶级", "100%", "绝对", "治疗", "医疗", "抗菌", "抗病毒",
    "杀菌", "包治", "最好卖", "无敌",
]

_LANGUAGE = {"美国": "英语", "印度": "英语", "俄罗斯": "俄语"}


def _filter_ban_words(text):
    lowered = (text or "").lower()
    return sorted({w for w in _BAN_WORDS if w.lower() in lowered})


def generate_listing(product, destination="美国", platform="Amazon"):
    """按产品 + 目的国 + 平台生成当地语言 Listing，并做违禁词自检。"""
    language = _LANGUAGE.get(destination, "英语")
    system = (
        "你是资深跨境电商 Listing 文案专家，精通亚马逊/TikTok Shop 的 SEO 本地化写法。"
        "只输出 Listing 内容，不要解释。用目标市场本地语言写作，符合平台字段规范。"
    )
    user = (
        f"产品：{product}\n"
        f"目标市场：{destination}（语言：{language}）\n"
        f"平台：{platform}\n\n"
        f"请生成：\n"
        f"1. 标题（含核心关键词，符合 {platform} 标题字数规范）\n"
        f"2. 五点描述（5 条，突出卖点与解决痛点）\n"
        f"3. 后台 ST 搜索词（10-15 个，逗号分隔，不堆砌重复词）\n\n"
        f"要求：避免夸大/绝对化用语，不写虚假医疗/疗效宣称。"
    )
    try:
        resp = chat_completion(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            tools=None, temperature=0.7, retries_per_provider=0,
        )
        text = resp.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        return {
            "error": f"Listing 生成失败（{type(exc).__name__}），请稍后重试或人工撰写",
            "platform": platform, "language": language,
        }

    flagged = _filter_ban_words(text)
    return {
        "platform": platform,
        "language": language,
        "product": product,
        "listing": text,
        "flagged_words": flagged,
        "note": ("违禁/夸大词自检：发现 " + "、".join(flagged) + "，建议人工复核替换"
                 if flagged else "违禁/夸大词自检：未发现明显违禁词"),
        "source_note": "由 LLM 生成，需人工复核后方可上架",
    }
