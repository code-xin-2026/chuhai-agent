"""端到端冒烟测试：用真实 DeepSeek 跑一次完整对话（会消耗少量额度）。"""
from agent import run_agent

Q = ("我想把 500 个儿童声光电动早教玩具（单价 15 美元，含锂电池）卖到美国，"
     "帮我算一下「直邮小包」和「FBA大批量」两种方式的合规要求和到岸成本，"
     "以及如果我跳过 CPC 会有什么后果？")

answer, trace = run_agent(Q, [])
print("=" * 60)
print(answer)
print("=" * 60)
print(f"\n推理 {len(trace)} 步：")
for t in trace:
    print(f"  [{t['provider']}] 工具 {t['tool']} → {t['args']}")
