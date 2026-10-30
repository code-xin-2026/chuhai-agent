# 跨境出海合规 & 成本测算 Agent

第二届全国人工智能应用创新大赛 · 通用赛道「让 AI Agent 赋能千行百业」· 出海方向。

## 作品定位

帮中小卖家/创业者评估把产品出口到海外目标国的**合规要求 + 关税成本**。
区别于普通 chatbot：本 Agent 会真实调用工具（合规查询、关税测算、成本测算），多轮补全信息，
输出带来源、带风险量化的结构化结论。

当前在册案例：**美国 · 儿童声光电动早教玩具**。

## 目录结构

```
app.py               Streamlit 前端（评委交互 + 推理过程可视化）
agent.py             ReAct 智能体循环（function calling + 兜底）
providers.py         LLM 供应商配置 + 自动 failover（JoyCode/DeepSeek/tokenrhythm）
tools/
  compliance.py      认证准入查询（CPC/FCC/UL/UN38.3 + 风险字段）
  cost.py            到岸成本测算（关税/MPF/HMF/物流/认证摊薄/风险备用金）
  tariff_db.py       HS 税率查询层（SQLite，缺库自动重建）
data/
  seed_tariff.py     税率库种子数据（真实分层税率 + 来源 + 更新时间）
  tariff.db          生成的 SQLite 库（不入库，自动重建）
.env.example         本地配置模板 → 复制为 .env 填真实值
```

## 本地运行

```bash
uv venv .venv
uv pip install -r requirements.txt
cp .env.example .env      # 填入 DEEPSEEK_API_KEY
uv run streamlit run app.py
```

## 部署（Streamlit Community Cloud，免费）

1. 把本项目 push 到一个 GitHub 仓库（`requirements.txt`、`app.py` 必须在根目录）。
2. 打开 https://share.streamlit.io → Sign in with GitHub → New app → 选仓库和 `app.py` → Deploy。
3. 在 App 的 **Settings → Secrets** 里配（密钥不要写进代码）：
   ```toml
   DEEPSEEK_API_KEY = "sk-..."
   DEEPSEEK_MODEL = "deepseek-chat"
   APP_PASSWORD = "给评委的访问密码"   # 可选，配了就多一道密码门
   ```
4. 得到公网链接：`https://<app-name>.streamlit.app`，提交到比赛系统即可。

## 状态

- [x] Agent 骨架（ReAct 循环 + failover）
- [x] 前端交互界面 + 推理过程可视化
- [x] 真实 HS 分层税率库（SQLite + 来源 + 更新时间）
- [x] 合规 + 成本 + 风险量化工具
- [ ] 部署公网链接
- [ ] PPT + 答辩视频
