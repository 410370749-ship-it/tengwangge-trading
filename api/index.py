#!/usr/bin/env python3
"""
滕王阁序交易系统 - Vercel Serverless 版本
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine import TradingEngine, SignalType, Trade

# 全局引擎实例（Vercel会复用）
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        config_path = PROJECT_ROOT / "config.json"
        if config_path.exists():
            _engine = TradingEngine(str(config_path))
        else:
            # 使用默认配置
            _engine = TradingEngine()
    return _engine

class handler(BaseHTTPRequestHandler):
    """Vercel Serverless Handler"""
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        if path == '/':
            self._serve_html()
        elif path == '/api/portfolios':
            self._get_portfolios()
        elif path == '/api/trades':
            self._get_trades(query)
        else:
            self._json_response(404, {'error': 'Not found'})
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'
        
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}
        
        if path == '/api/sell':
            self._sell_stock(data)
        elif path == '/api/batch_sell':
            self._batch_sell(data)
        elif path == '/api/refresh':
            self._refresh_data()
        else:
            self._json_response(404, {'error': 'Not found'})
    
    def _serve_html(self):
        """返回HTML页面"""
        html_path = PROJECT_ROOT / "web_trading.html"
        if html_path.exists():
            with open(html_path, 'r', encoding='utf-8') as f:
                html = f.read()
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        else:
            self._json_response(404, {'error': 'HTML not found'})
    
    def _get_portfolios(self):
        """获取组合列表"""
        engine = get_engine()
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
        
        self._json_response(200, report)
    
    def _get_trades(self, query):
        """获取交易记录"""
        engine = get_engine()
        limit = int(query.get('limit', [50])[0])
        
        trades = engine._load_trades()
        trades = sorted(trades, key=lambda x: x['trade_id'], reverse=True)[:limit]
        
        # 加载统计
        history_file = PROJECT_ROOT / "trades" / "trade_history.json"
        stats = {}
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                stats = history.get('stats', {})
        
        self._json_response(200, {'trades': trades, 'stats': stats})
    
    def _sell_stock(self, data):
        """卖出单只股票"""
        engine = get_engine()
        portfolio_id = data.get('portfolio_id')
        stock_code = data.get('stock_code')
        reason = data.get('reason', '')
        
        if not portfolio_id or not stock_code:
            self._json_response(400, {'success': False, 'error': '参数缺失'})
            return
        
        # 查找持仓
        portfolio = None
        position_data = None
        position_idx = -1
        
        for i, p in enumerate(engine.config['portfolios']):
            if p['id'] == portfolio_id:
                portfolio = p
                for j, pos in enumerate(p.get('positions', [])):
                    if pos['stock'] == stock_code:
                        position_data = pos
                        position_idx = j
                        break
                break
        
        if not position_data:
            self._json_response(404, {'success': False, 'error': '未找到持仓'})
            return
        
        # 执行卖出
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
        del portfolio['positions'][position_idx]
        portfolio['cash'] = portfolio.get('cash', 0) + amount
        
        # 保存
        engine._save_config()
        engine._save_trade(trade)
        
        self._json_response(200, {
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
    
    def _batch_sell(self, data):
        """批量卖出"""
        engine = get_engine()
        trades = data.get('trades', [])
        
        results = []
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
        
        self._json_response(200, {'success': True, 'results': results})
    
    def _refresh_data(self):
        """刷新数据"""
        engine = get_engine()
        engine.config = engine._load_config()
        self._json_response(200, {'success': True})
    
    def _json_response(self, status_code, data):
        """返回JSON响应"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def log_message(self, format, *args):
        """禁用默认日志"""
        pass


# Vercel 入口点
def app(environ, start_response):
    """WSGI App for Vercel"""
    from wsgiref.util import setup_testing_defaults
    from io import BytesIO
    
    setup_testing_defaults(environ)
    
    # 创建请求处理器
    class RequestHandler(handler):
        def __init__(self, request, client_address, server):
            self.request = request
            self.client_address = client_address
            self.server = server
            self.setup()
            
        def setup(self):
            self.rfile = environ.get('wsgi.input')
            self.wfile = BytesIO()
            
        def finish(self):
            pass
            
        def handle(self):
            method = environ.get('REQUEST_METHOD', 'GET')
            if method == 'GET':
                self.do_GET()
            elif method == 'POST':
                self.do_POST()
    
    # 处理请求
    request_handler = RequestHandler(None, None, None)
    request_handler.handle()
    
    # 获取响应
    response_body = request_handler.wfile.getvalue()
    
    # 返回WSGI响应
    status = '200 OK'
    headers = [('Content-type', 'application/json; charset=utf-8')]
    start_response(status, headers)
    return [response_body]


# 兼容 Vercel 无服务器环境
if __name__ != '__main__':
    # Vercel 会自动调用 app 函数
    pass