#!/usr/bin/env python3
"""
滕王阁序交易系统 - 数据迁移脚本
将本地 JSON 数据迁移到 Supabase
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from supabase_db import SupabaseDB


def migrate_portfolios():
    """迁移组合配置"""
    print("=" * 60)
    print("🔄 迁移组合配置到 Supabase")
    print("=" * 60)
    
    # 加载本地配置
    config_path = PROJECT_ROOT / "config.json"
    if not config_path.exists():
        print("❌ 未找到 config.json")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    db = SupabaseDB()
    
    if not db.enabled:
        print("❌ Supabase 未启用，无法迁移")
        return
    
    # 迁移每个组合
    for portfolio in config.get('portfolios', []):
        portfolio_data = {
            'id': portfolio['id'],
            'name': portfolio['name'],
            'initial_capital': portfolio['initial_capital'],
            'cash': portfolio.get('cash', 0),
            'config': portfolio['config'],
        }
        
        if db.save_portfolio_config(portfolio_data):
            print(f"✅ 组合配置已保存: {portfolio['name']}")
        else:
            print(f"❌ 组合配置保存失败: {portfolio['name']}")
    
    print()


def migrate_positions():
    """迁移持仓数据"""
    print("=" * 60)
    print("🔄 迁移持仓数据到 Supabase")
    print("=" * 60)
    
    config_path = PROJECT_ROOT / "config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    db = SupabaseDB()
    
    if not db.enabled:
        print("❌ Supabase 未启用，无法迁移")
        return
    
    total = 0
    for portfolio in config.get('portfolios', []):
        portfolio_id = portfolio['id']
        positions = portfolio.get('positions', [])
        
        for pos in positions:
            if db.add_position(portfolio_id, pos):
                total += 1
                print(f"  ✅ {portfolio['name']} - {pos['name']} ({pos['stock']})")
            else:
                print(f"  ❌ {portfolio['name']} - {pos['name']}")
    
    print(f"\n共迁移 {total} 条持仓记录")
    print()


def migrate_trades():
    """迁移交易记录"""
    print("=" * 60)
    print("🔄 迁移交易记录到 Supabase")
    print("=" * 60)
    
    # 加载本地交易记录
    trade_files = list((PROJECT_ROOT / "trades").glob("trades_*.json"))
    
    if not trade_files:
        print("未找到本地交易记录")
        return
    
    db = SupabaseDB()
    
    if not db.enabled:
        print("❌ Supabase 未启用，无法迁移")
        return
    
    total = 0
    for trade_file in trade_files:
        with open(trade_file, 'r', encoding='utf-8') as f:
            trades = json.load(f)
        
        for trade in trades:
            if db.add_trade(trade):
                total += 1
    
    print(f"共迁移 {total} 条交易记录")
    print()


def verify_migration():
    """验证迁移结果"""
    print("=" * 60)
    print("✅ 验证迁移结果")
    print("=" * 60)
    
    db = SupabaseDB()
    
    if not db.enabled:
        print("❌ Supabase 未启用")
        return
    
    # 检查组合
    portfolios = db.get_all_portfolios()
    print(f"组合数量: {len(portfolios)}")
    for p in portfolios:
        positions = db.get_positions(p['id'])
        print(f"  {p['name']}: {len(positions)} 只持仓")
    
    # 检查交易记录
    trades = db.get_trades(limit=1000)
    print(f"\n交易记录: {len(trades)} 条")
    
    # 统计
    stats = db.get_trade_stats()
    if stats:
        print(f"\n统计:")
        print(f"  总交易: {stats.get('total_trades', 0)}")
        print(f"  胜率: {stats.get('win_rate', 0):.1f}%")
        print(f"  总盈亏: ¥{stats.get('total_pnl', 0):+,.2f}")


def main():
    """主函数"""
    print("\n🏮 滕王阁序交易系统 - 数据迁移工具\n")
    
    # 检查 Supabase 配置
    db = SupabaseDB()
    if not db.enabled:
        print("❌ Supabase 未配置或连接失败")
        print("\n请先完成以下步骤:")
        print("1. 创建 Supabase 项目: https://supabase.com")
        print("2. 创建数据表 (见 SUPABASE_SETUP.md)")
        print("3. 配置 .env 文件")
        print("\n然后重新运行此脚本")
        return
    
    print("请选择要迁移的数据:")
    print("1) 全部迁移")
    print("2) 仅组合配置")
    print("3) 仅持仓数据")
    print("4) 仅交易记录")
    print("5) 验证迁移结果")
    
    try:
        choice = input("\n输入选项 (1-5): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消")
        return
    
    if choice == '1':
        migrate_portfolios()
        migrate_positions()
        migrate_trades()
        verify_migration()
    elif choice == '2':
        migrate_portfolios()
    elif choice == '3':
        migrate_positions()
    elif choice == '4':
        migrate_trades()
    elif choice == '5':
        verify_migration()
    else:
        print("无效选项")


if __name__ == '__main__':
    main()
