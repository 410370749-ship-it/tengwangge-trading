#!/usr/bin/env python3
"""
滕王阁序交易系统 - 快速演示
"""

from engine import TradingEngine, SignalType

print("🏮 滕王阁序交易系统 - 功能演示\n")

# 创建引擎实例
engine = TradingEngine()

# 1. 显示当前持仓状态
print("=" * 60)
print("📊 当前持仓概览")
print("=" * 60)

for p in engine.config["portfolios"]:
    positions = p.get("positions", [])
    print(f"\n{p['name']} ({p['id']}):")
    print(f"  持仓数量: {len(positions)} 只")
    print(f"  现金余额: ¥{p.get('cash', 0):,.2f}")
    print(f"  止损线: {p['config']['stop_loss']:.0%}")
    print(f"  止盈线: {p['config']['take_profit']:.0%}")
    print(f"  最大持仓天数: {p['config']['max_hold_days']} 天")
    
    if positions:
        print(f"  持仓股票:")
        for pos in positions[:3]:  # 只显示前3只
            print(f"    - {pos['name']} ({pos['stock']}): {pos['shares']}股 @ ¥{pos['avg_cost']:.2f}")
        if len(positions) > 3:
            print(f"    ... 等共 {len(positions)} 只")

# 2. 运行扫描
print("\n" + "=" * 60)
print("🔍 运行持仓扫描...")
print("=" * 60)

signals = engine.run_daily_check()

# 3. 显示交易记录统计
print("\n" + "=" * 60)
print("📜 交易记录统计")
print("=" * 60)

import json
from pathlib import Path

history_file = Path(__file__).parent / "trades" / "trade_history.json"
if history_file.exists():
    with open(history_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
        stats = history.get("stats", {})
        print(f"总交易次数: {stats.get('total_trades', 0)}")
        print(f"胜率: {stats.get('win_rate', 0):.1f}%")
        print(f"总盈亏: ¥{stats.get('total_pnl', 0):+,.2f}")
else:
    print("暂无交易记录")

print("\n" + "=" * 60)
print("💡 提示")
print("=" * 60)
print("运行 'python3 engine.py --interactive' 进入交互模式")
print("进行一键卖出操作或查看详细交易记录")
print("=" * 60)
