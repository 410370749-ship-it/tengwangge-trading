from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json
import sys
from pathlib import Path
from datetime import datetime
import threading
import webbrowser

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine import TradingEngine, SignalType, Trade

app = Flask(__name__, template_folder='.')
CORS(app)

# 全局引擎实例
engine = TradingEngine()
engine_lock = threading.Lock()

@app.route('/')
def index():
    """主页面"""
    return render_template('web_trading.html')

@app.route('/api/portfolios')
def get_portfolios():
    """获取所有组合信息"""
    with engine_lock:
        report = engine.generate_report()
        
        # 添加信号信息
        for portfolio in report['portfolios']:
            portfolio_config = next(
                (p for p in engine.config['portfolios'] if p['id'] == portfolio['id']), 
                None
            )
            if portfolio_config:
                signals = engine.check_portfolio(portfolio_config)
                portfolio['signals'] = [
                    {
                        'stock': s.stock,
                        'stock_name': s.stock_name,
                        'signal_type': s.signal_type.value,
                        'reason': s.reason,
                        'current_price': s.current_price,
                        'avg_cost': s.avg_cost,
                        'pnl_pct': s.pnl_pct,
                        'hold_days': s.hold_days,
                        'suggestion': s.suggestion
                    }
                    for s in signals
                ]
        
        return jsonify(report)

@app.route('/api/sell', methods=['POST'])
def sell_stock():
    """卖出股票"""
    data = request.json
    portfolio_id = data.get('portfolio_id')
    stock_code = data.get('stock_code')
    reason = data.get('reason', '')
    
    if not portfolio_id or not stock_code:
        return jsonify({'success': False, 'error': '参数缺失'}), 400
    
    with engine_lock:
        # 查找持仓
        portfolio = None
        position_data = None
        
        for p in engine.config['portfolios']:
            if p['id'] == portfolio_id:
                portfolio = p
                for pos in p.get('positions', []):
                    if pos['stock'] == stock_code:
                        position_data = pos
                        break
                break
        
        if not position_data:
            return jsonify({'success': False, 'error': '未找到持仓'}), 404
        
        # 获取当前价格
        current_price = engine.data_source.get_price(stock_code)
        shares = position_data['shares']
        avg_cost = position_data['avg_cost']
        amount = shares * current_price
        pnl = (current_price - avg_cost) * shares
        pnl_pct = (current_price - avg_cost) / avg_cost
        
        # 创建交易记录
        now = datetime.now()
        trade = Trade(
            trade_id=f"{now.strftime('%Y%m%d%H%M%S')}_{stock_code}",
            portfolio_id=portfolio_id,
            portfolio_name=portfolio['name'],
            stock=stock_code,
            stock_name=position_data['name'],
            trade_type="SELL",
            shares=shares,
            price=current_price,
            amount=amount,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            pnl=pnl,
            pnl_pct=pnl_pct,
            reason=reason,
            notes=""
        )
        
        # 更新持仓
        portfolio['positions'] = [p for p in portfolio['positions'] if p['stock'] != stock_code]
        portfolio['cash'] = portfolio.get('cash', 0) + amount
        
        # 保存
        engine._save_config()
        engine._save_trade(trade)
        
        return jsonify({
            'success': True,
            'trade': {
                'trade_id': trade.trade_id,
                'stock_name': trade.stock_name,
                'shares': trade.shares,
                'price': trade.price,
                'amount': trade.amount,
                'pnl': trade.pnl,
                'pnl_pct': trade.pnl_pct
            }
        })

@app.route('/api/batch_sell', methods=['POST'])
def batch_sell():
    """批量卖出"""
    data = request.json
    trades = data.get('trades', [])  # [{'portfolio_id': '...', 'stock_code': '...', 'reason': '...'}]
    
    results = []
    with engine_lock:
        for trade_info in trades:
            portfolio_id = trade_info.get('portfolio_id')
            stock_code = trade_info.get('stock_code')
            reason = trade_info.get('reason', '')
            
            # 查找持仓
            portfolio = None
            position_data = None
            
            for p in engine.config['portfolios']:
                if p['id'] == portfolio_id:
                    portfolio = p
                    for pos in p.get('positions', []):
                        if pos['stock'] == stock_code:
                            position_data = pos
                            break
                    break
            
            if not position_data:
                results.append({'stock_code': stock_code, 'success': False, 'error': '未找到持仓'})
                continue
            
            # 执行卖出
            current_price = engine.data_source.get_price(stock_code)
            shares = position_data['shares']
            avg_cost = position_data['avg_cost']
            amount = shares * current_price
            pnl = (current_price - avg_cost) * shares
            pnl_pct = (current_price - avg_cost) / avg_cost
            
            now = datetime.now()
            trade = Trade(
                trade_id=f"{now.strftime('%Y%m%d%H%M%S')}_{stock_code}",
                portfolio_id=portfolio_id,
                portfolio_name=portfolio['name'],
                stock=stock_code,
                stock_name=position_data['name'],
                trade_type="SELL",
                shares=shares,
                price=current_price,
                amount=amount,
                date=now.strftime("%Y-%m-%d"),
                time=now.strftime("%H:%M:%S"),
                pnl=pnl,
                pnl_pct=pnl_pct,
                reason=reason,
                notes=""
            )
            
            # 更新持仓
            portfolio['positions'] = [p for p in portfolio['positions'] if p['stock'] != stock_code]
            portfolio['cash'] = portfolio.get('cash', 0) + amount
            
            engine._save_trade(trade)
            
            results.append({
                'stock_code': stock_code,
                'success': True,
                'trade_id': trade.trade_id,
                'pnl': pnl,
                'pnl_pct': pnl_pct
            })
        
        # 保存配置
        engine._save_config()
    
    return jsonify({'success': True, 'results': results})

@app.route('/api/trades')
def get_trades():
    """获取交易记录"""
    limit = request.args.get('limit', 50, type=int)
    
    with engine_lock:
        trades = engine._load_trades()
        trades = sorted(trades, key=lambda x: x['trade_id'], reverse=True)[:limit]
        
        # 加载统计
        history_file = PROJECT_ROOT / "trades" / "trade_history.json"
        stats = {}
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                stats = history.get('stats', {})
        
        return jsonify({
            'trades': trades,
            'stats': stats
        })

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """刷新数据"""
    with engine_lock:
        # 重新加载配置
        engine.config = engine._load_config()
        return jsonify({'success': True})

if __name__ == '__main__':
    print("🏮 滕王阁序交易系统 - Web版")
    print("=" * 60)
    print("启动中...")
    
    print("\n🌐 请在浏览器中访问: http://服务器IP:5000")
    print("   本地访问: http://localhost:5000")
    print("按 Ctrl+C 停止服务\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
