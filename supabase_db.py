#!/usr/bin/env python3
"""
滕王阁序交易系统 - Supabase 数据库模块
提供持仓和交易记录的持久化存储
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

# 尝试导入 supabase
try:
    from supabase import create_client, Client
    from dotenv import load_dotenv
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# 加载环境变量
PROJECT_ROOT = Path(__file__).parent
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    load_dotenv(env_file)


class SupabaseDB:
    """Supabase 数据库操作类"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.enabled = False
        
        if not SUPABASE_AVAILABLE:
            print("⚠️ Supabase 未安装，使用本地 JSON 存储")
            print("   运行: pip install supabase python-dotenv")
            return
        
        self._connect()
    
    def _connect(self):
        """连接 Supabase"""
        try:
            url = os.getenv('SUPABASE_URL')
            key = os.getenv('SUPABASE_KEY')
            
            if not url or not key:
                print("⚠️ 未配置 SUPABASE_URL 或 SUPABASE_KEY，使用本地存储")
                return
            
            self.client = create_client(url, key)
            
            # 测试连接
            response = self.client.table('positions').select('count', count='exact').execute()
            self.enabled = True
            print("✅ Supabase 连接成功")
            
        except Exception as e:
            print(f"⚠️ Supabase 连接失败: {e}")
            print("   使用本地 JSON 存储")
    
    # ==================== 持仓操作 ====================
    
    def get_positions(self, portfolio_id: str) -> List[Dict]:
        """获取组合持仓"""
        if not self.enabled:
            return []
        
        try:
            response = self.client.table('positions')\
                .select('*')\
                .eq('portfolio_id', portfolio_id)\
                .execute()
            return response.data
        except Exception as e:
            print(f"❌ 获取持仓失败: {e}")
            return []
    
    def add_position(self, portfolio_id: str, position: Dict) -> bool:
        """添加持仓"""
        if not self.enabled:
            return False
        
        try:
            data = {
                'portfolio_id': portfolio_id,
                'stock': position['stock'],
                'name': position['name'],
                'shares': position['shares'],
                'avg_cost': position['avg_cost'],
                'buy_date': position['buy_date'],
            }
            
            self.client.table('positions')\
                .upsert(data, on_conflict='portfolio_id,stock')\
                .execute()
            return True
        except Exception as e:
            print(f"❌ 添加持仓失败: {e}")
            return False
    
    def remove_position(self, portfolio_id: str, stock: str) -> bool:
        """删除持仓"""
        if not self.enabled:
            return False
        
        try:
            self.client.table('positions')\
                .delete()\
                .eq('portfolio_id', portfolio_id)\
                .eq('stock', stock)\
                .execute()
            return True
        except Exception as e:
            print(f"❌ 删除持仓失败: {e}")
            return False
    
    def update_position(self, portfolio_id: str, stock: str, updates: Dict) -> bool:
        """更新持仓"""
        if not self.enabled:
            return False
        
        try:
            updates['updated_at'] = datetime.now().isoformat()
            self.client.table('positions')\
                .update(updates)\
                .eq('portfolio_id', portfolio_id)\
                .eq('stock', stock)\
                .execute()
            return True
        except Exception as e:
            print(f"❌ 更新持仓失败: {e}")
            return False
    
    # ==================== 交易记录操作 ====================
    
    def add_trade(self, trade: Dict) -> bool:
        """添加交易记录"""
        if not self.enabled:
            return False
        
        try:
            data = {
                'trade_id': trade.get('trade_id', f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{trade['stock']}"),
                'portfolio_id': trade['portfolio_id'],
                'portfolio_name': trade['portfolio_name'],
                'stock': trade['stock'],
                'stock_name': trade['stock_name'],
                'trade_type': trade['trade_type'],
                'shares': trade['shares'],
                'price': trade['price'],
                'amount': trade['amount'],
                'pnl': trade.get('pnl', 0),
                'pnl_pct': trade.get('pnl_pct', 0),
                'reason': trade.get('reason', ''),
                'notes': trade.get('notes', ''),
                'date': trade['date'],
                'time': trade['time'],
            }
            
            self.client.table('trades').insert(data).execute()
            return True
        except Exception as e:
            print(f"❌ 添加交易记录失败: {e}")
            return False
    
    def get_trades(self, portfolio_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """获取交易记录"""
        if not self.enabled:
            return []
        
        try:
            query = self.client.table('trades').select('*').order('created_at', desc=True).limit(limit)
            
            if portfolio_id:
                query = query.eq('portfolio_id', portfolio_id)
            
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"❌ 获取交易记录失败: {e}")
            return []
    
    def get_trade_stats(self, portfolio_id: Optional[str] = None) -> Dict[str, Any]:
        """获取交易统计"""
        if not self.enabled:
            return {}
        
        try:
            # 使用 Supabase 的 RPC 函数或直接查询
            trades = self.get_trades(portfolio_id, limit=1000)
            
            sells = [t for t in trades if t['trade_type'] == 'SELL']
            profits = [t for t in sells if t.get('pnl', 0) > 0]
            losses = [t for t in sells if t.get('pnl', 0) <= 0]
            
            return {
                'total_trades': len(sells),
                'profit_count': len(profits),
                'loss_count': len(losses),
                'win_rate': (len(profits) / len(sells) * 100) if sells else 0,
                'total_pnl': sum(t.get('pnl', 0) for t in sells),
                'avg_profit': sum(t.get('pnl', 0) for t in profits) / len(profits) if profits else 0,
                'avg_loss': sum(t.get('pnl', 0) for t in losses) / len(losses) if losses else 0,
            }
        except Exception as e:
            print(f"❌ 获取统计失败: {e}")
            return {}
    
    # ==================== 组合配置操作 ====================
    
    def save_portfolio_config(self, portfolio: Dict) -> bool:
        """保存组合配置"""
        if not self.enabled:
            return False
        
        try:
            data = {
                'id': portfolio['id'],
                'name': portfolio['name'],
                'initial_capital': portfolio['initial_capital'],
                'cash': portfolio.get('cash', 0),
                'config': portfolio['config'],
                'updated_at': datetime.now().isoformat(),
            }
            
            self.client.table('portfolios')\
                .upsert(data, on_conflict='id')\
                .execute()
            return True
        except Exception as e:
            print(f"❌ 保存组合配置失败: {e}")
            return False
    
    def load_portfolio_config(self, portfolio_id: str) -> Optional[Dict]:
        """加载组合配置"""
        if not self.enabled:
            return None
        
        try:
            response = self.client.table('portfolios')\
                .select('*')\
                .eq('id', portfolio_id)\
                .single()\
                .execute()
            return response.data
        except Exception as e:
            print(f"❌ 加载组合配置失败: {e}")
            return None
    
    def get_all_portfolios(self) -> List[Dict]:
        """获取所有组合"""
        if not self.enabled:
            return []
        
        try:
            response = self.client.table('portfolios').select('*').execute()
            return response.data
        except Exception as e:
            print(f"❌ 获取组合列表失败: {e}")
            return []


# 单例模式
db = SupabaseDB()


if __name__ == '__main__':
    # 测试
    print("测试 Supabase 连接...")
    
    db = SupabaseDB()
    
    if db.enabled:
        # 测试添加持仓
        test_position = {
            'stock': '000001',
            'name': '平安银行',
            'shares': 1000,
            'avg_cost': 10.5,
            'buy_date': '2024-03-17',
        }
        db.add_position('test-portfolio', test_position)
        
        # 测试查询
        positions = db.get_positions('test-portfolio')
        print(f"持仓数量: {len(positions)}")
        
        # 清理测试数据
        db.remove_position('test-portfolio', '000001')
        print("测试完成!")
    else:
        print("Supabase 未启用，跳过测试")
