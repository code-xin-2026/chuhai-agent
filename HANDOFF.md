# 交接文档 · 帆朵（跨境出海合规 & 成本测算 Agent）

> 本文是「制定比赛参赛方案」会话 → 帆朵项目 的工作交接记录。
> 目标是让下一个接手的人（或 AI）不看历史聊天也能 5 分钟接上状态、知道还剩什么、避开踩过的坑。

---

## 一、一句话定位

**帮中小卖家/创业者评估「把产品出口到海外目标国」的合规要求 + 关税/到岸成本。**
区别于普通 chatbot：帆朵会**真实调用工具**（合规查询、关税测算、成本测算、技能库检索），多轮补全信息，输出**带来源、带风险量化**的结构化结论。覆盖品类（美国/印度/俄罗斯）：**儿童玩具 / 不锈钢食品接触容器 / 锂电池·充电宝 / 蓝牙耳机·音箱**；可信度分级（✅确定 / ⚠️估算 / ❓需核实），关税拆「基础关税（稳定）+ 附加税（政策波动）」。

**订单自动处理（Phase 1 已上线）**：上传订单 CSV/Excel → 自动跑合规+关税/成本+异常识别 → 产出《发货清单/异常清单/发货通知草稿》。代码在 `orders/` 子包 + `pages/1_📦_订单处理.py`，演示样本 `data/demo_orders.csv`（24 笔）。

---

## 二、比赛信息（硬约束）

| 项 | 内容 |
|---|---|
| 比赛 | 第二届全国人工智能应用创新大赛 |
| 赛道 | 通用赛道「让 AI Agent 赋能千行百业」· 出海方向 |
| 主办 | 中国技术经济学会 |
| **截止** | **11 月 20 日 24:00** |
| 提交三件套 | ① PPT ≤20 页（16:9） ② 答辩视频 ≤6 分钟 MP4 ③ 智能体公网链接 + 账号密码 |

**评审关键词**：可验证智能体交互能力 + 真实业务痛点 + 产业效率提升。评委真会点开链接试——所以 demo 必须「当场演示多步工具调用」，不能是套壳 chatbot。

---

## 三、技术架构（已定，勿再改）

```
Streamlit（前端，纯 Python，一个人可维护）
   └─ agent.py  手写 ReAct 循环 + function calling（max 8 步）
        ├─ providers.py  多供应商自动 failover
        │     JoyCode（大赛免费，拿到 key 后成主力）
        │     → DeepSeek（当前主力）→ tokenrhythm（备胎）
        ├─ tools/
        │     compliance.py   认证准入查询（CPC/FCC/UL/UN38.3 + 风险字段）
        │     cost.py         到岸成本测算（关税/MPF/HMF/物流/认证摊薄/风险备用金）
        │     tariff_db.py    HS 税率查询（SQLite，缺库自动重建）
        ├─ skills/           外贸客服技能库（7 个 SKILL.md，注入 system prompt）
        └─ vision.py         GLM-4V-Flash 图片识别（DeepSeek 看不了图）
```

**关键设计决策（及原因）：**
- **Streamlit 而非前后端分离**：团队没人会前端，纯 Python 出公网链接。
- **SQLite 存 HS 分层税率**，不写爬虫：数据手动整理（海关税率表/HTS 公开），「关税计算」是真查表不是 LLM 瞎背。
- **手写 ReAct + function calling**，不引重型框架：可控、透明、评审能看推理过程。
- **数字硬规则**：税率库有真实数据的用真实数据（带来源+更新时间）；没有的让 LLM 归类 HS + 估算，**必须标注「估算值，需核实」**，不得凭空编造数字。

---

## 四、当前完成度

- [x] Agent 骨架（ReAct 循环 + 多供应商 failover）
- [x] Streamlit 前端（工作区/历史会话/流式输出/推理过程可视化/复制/导出报告）
- [x] 真实 HS 分层税率库（SQLite + 来源 + 更新时间）
- [x] 合规 + 成本 + 风险量化工具
- [x] **多品类真实数据 + 任意产品测算**（4 大品类有真实 HS/MFN/合规数据，关键词自动匹配；非覆盖品类给 HS 归类 + 分级置信度 + 核实路径，不再空转）
- [x] **图片识别**（GLM-4V-Flash 当眼睛，识别产品后自动分析）
- [x] 外贸客服技能库（询盘补全/多语言/报价/风险升级/脱敏，7 个 skill）
- [ ] **部署公网链接**（Streamlit Community Cloud）
- [ ] **PPT ≤20 页**
- [ ] **答辩视频 ≤6 分钟**

---

## 五、剩余待办（按优先级）

1. **部署公网链接**（最优先，评委要链接）
   - 先把未提交改动 commit + push 到 GitHub 仓库（见第六节）
   - Streamlit Cloud 部署步骤见 `README.md` 的「部署」节
   - 配 Secrets：`DEEPSEEK_API_KEY`、`DEEPSEEK_MODEL`、`APP_PASSWORD`（给评委的访问密码）
   - 拿到 `https://<app>.streamlit.app` 即满足「智能体链接 + 账号密码」一项

2. **PPT ≤20 页（16:9）**——未开始，建议主线：痛点（出海卖家踩合规/关税坑）→ 为什么 chatbot 不够 → 帆朵的多步工具调用 demo → 真实数据来源 → 效果（省多少调研时间）→ 差异化（合规+成本，少有人做）

3. **答辩视频 ≤6 分钟 MP4**——未开始，围绕「当场演示一次完整多步推理」拍，别念 PPT

---

## 六、⚠️ 交接时必看的坑 / 备忘

1. **代码有未提交改动**：git 历史停在 `v2`，但后面一整套（帆朵改名 + 技能库 + 工作区 + 流式 + 图片识别 + 任意产品测算）都还没 commit。当前 `git status` 有：
   - 已改：`agent.py` `app.py` `providers.py` `tools/__init__.py` `tools/cost.py` `.env.example`
   - 未跟踪：`chat_store.py` `skills/` `skills_loader.py` `vision.py`
   - **交接第一步就是 commit + push**，否则这些工作只在本地磁盘，换机器/重装就没了。

2. **两个 API key 已泄露**：DeepSeek 和 GLM 的 key 都进过聊天记录 + `.env`。**比赛前务必去 DeepSeek 后台、智谱 open.bigmodel.cn 后台重新生成换新**，旧 key 作废。

3. **JoyCode 模型名待确认**：`.env` 里 `JOYCODE_MODEL` 还是空。去 JoyBuilder 控制台申请 Coding Plan Key 时确认模型名填进去，否则 failover 会跳过 JoyCode 直接走 DeepSeek。

4. **Streamlit 的坑（已修，别改回）**：新版 `st.chat_input(accept_file=True)` 返回的是 `ChatInputValue` 对象（有 `.text`/`.files`），不是字符串。判断必须用 `user_input.to_dict()` 读取，用 `isinstance(x, str)` 判断会导致「字发了没反应」。这是踩过两次的坑。

5. **本地内存紧张**：机器 8GB 内存，跑 streamlit 本地调试时别同时开太多东西。

---

## 七、本地运行

```bash
cd E:\SongBIn2.0\AiMaShi-Hermes\duihua\chuhai-agent
uv run streamlit run app.py
# 首次：uv venv .venv && uv pip install -r requirements.txt && cp .env.example .env
```

`.env` 已被 `.gitignore` 忽略，`data/*.db`、`.venv/` 也不入库。
