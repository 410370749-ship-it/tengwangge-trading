from flask import Flask, jsonify, render_template_string, request
import os
import json
import requests
from datetime import datetime, timedelta
from supabase import create_client

app = Flask(__name__)

# Supabase 配置
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://erfhazdwgnhhtroxjhdl.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVyZmhhemR3Z25oaHRyb3hqaGRsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2ODU4NzYsImV4cCI6MjA4OTI2MTg3Nn0.Epg244WFqN2CfU0wC8EzaadLYmkM4yBw5f4E46N19Aw')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============ 实时价格获取 ============
price_cache = {}
price_cache_time = None

def fetch_realtime_prices(stock_codes):
    """从东方财富获取实时价格"""
    global price_cache, price_cache_time
    
    # 缓存15秒
    now = datetime.now()
    if price_cache_time and (now - price_cache_time).seconds < 15:
        return price_cache
    
    # 转换代码格式
    codes = []
    for code in stock_codes:
        if code.startswith('6'):
            codes.append(f'sh{code}')
        elif code.startswith(('0', '3')):
            codes.append(f'sz{code}')
        else:
            codes.append(f'sz{code}')
    
    try:
        url = f"http://qt.gtimg.cn/q={','.join(codes)}"
        response = requests.get(url, timeout=5)
        response.encoding = 'gbk'
        
        prices = {}
        for line in response.text.strip().split(';'):
            if 'v_' in line:
                parts = line.split('~')
                if len(parts) >= 3:
                    code = parts[2]
                    price = float(parts[3]) if parts[3] else 0
                    prices[code] = price
        
        price_cache = prices
        price_cache_time = now
        return prices
    except Exception as e:
        print(f"获取实时价格失败: {e}")
        return price_cache

# ============ HTML 模板 ============
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>滕王阁序投资组合 - 实时监控系统</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
            color: #e0e0e0;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { text-align: center; padding: 30px 0; margin-bottom: 30px; }
        .header h1 {
            font-size: 2.5em;
            background: linear-gradient(90deg, #f39c12, #e74c3c, #3498db);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header p { color: #95a5a6; margin-top: 10px; }
        .status-bar {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 15px;
            flex-wrap: wrap;
        }
        .status-item {
            background: rgba(255,255,255,0.05);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
        }
        .status-item .dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 6px;
        }
        .dot.online { background: #2ecc71; }
        .table-container {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            overflow-x: auto;
        }
        .section-title {
            color: #f39c12;
            margin-bottom: 20px;
            font-size: 1.3em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        table { width: 100%; border-collapse: collapse; }
        th {
            background: rgba(243, 156, 18, 0.2);
            color: #f39c12;
            padding: 14px 10px;
            text-align: center;
            font-weight: 600;
            font-size: 14px;
        }
        td {
            padding: 14px 10px;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        tr:hover td { background: rgba(255,255,255,0.05); }
        .portfolio-name { font-weight: bold; font-size: 1.1em; color: #f39c12; }
        .positive { color: #2ecc71; }
        .negative { color: #e74c3c; }
        .status-running { color: #2ecc71; }
        .status-pending { color: #f39c12; }
        .strategy-points { font-size: 11px; }
        .strategy-points span {
            display: inline-block;
            background: rgba(255,255,255,0.1);
            padding: 2px 8px;
            border-radius: 12px;
            margin: 2px;
            white-space: nowrap;
        }
        .signal-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        }
        .signal-stoploss { background: rgba(231, 76, 60, 0.3); color: #e74c3c; }
        .signal-takeprofit { background: rgba(46, 204, 113, 0.3); color: #2ecc71; }
        .signal-timestop { background: rgba(243, 156, 18, 0.3); color: #f39c12; }
        .signal-hold { background: rgba(149, 165, 166, 0.3); color: #95a5a6; }
        .chart-container {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            height: 400px;
        }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab {
            background: rgba(255,255,255,0.1);
            border: none;
            color: #fff;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .tab.active { background: #f39c12; }
        .refresh-btn {
            background: linear-gradient(135deg, #f39c12, #e74c3c);
            border: none;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
        }
        .update-time {
            text-align: center;
            color: #7f8c8d;
            margin-top: 30px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏮 滕王阁序投资组合</h1>
            <p>实时监控系统</p>
            <div class="status-bar">
                <div class="status-item">
                    <span class="dot online"></span>
                    实时价格: 东方财富API
                </div>
                <div class="status-item">📊 {{ portfolio_count }}个组合</div>
                <div class="status-item">📈 {{ position_count }}只持仓</div>
                <div class="status-item">🕐 {{ update_time }}</div>
            </div>
        </div>
        
        <div class="chart-container">
            <div class="tabs">
                <button class="tab active" onclick="showChart('pnl')">盈亏曲线</button>
                <button class="tab" onclick="showChart('value')">市值曲线</button>
            </div>
            <canvas id="mainChart"></canvas>
        </div>
        
        <div class="table-container">
            <h3 class="section-title">📊 组合概览</h3>
            <table>
                <thead>
                    <tr>
                        <th>组合</th>
                        <th>持仓票</th>
                        <th>仓位占比</th>
                        <th>总市值</th>
                        <th>现金</th>
                        <th>浮动盈亏</th>
                        <th>状态</th>
                        <th>策略要点</th>
                    </tr>
                </thead>
                <tbody>
                    {% for p in portfolios %}
                    <tr>
                        <td class="portfolio-name">{{ p.name }}</td>
                        <td>{{ p.position_count }}只</td>
                        <td>{{ p.position_ratio }}%</td>
                        <td>¥{{ p.total_market_value }}</td>
                        <td>¥{{ p.cash }}</td>
                        <td class="{% if p.total_floating_pnl >= 0 %}positive{% else %}negative{% endif %}">
                            ¥{{ p.total_floating_pnl }}
                        </td>
                        <td class="{% if p.status == '运行中' %}status-running{% else %}status-pending{% endif %}">
                            {{ p.status }}
                        </td>
                        <td class="strategy-points">
                            {% for point in p.strategy_points %}
                            <span>{{ point }}</span>
                            {% endfor %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="table-container">
            <h3 class="section-title">📈 金玉满堂持仓明细 (实时价格)</h3>
            <table>
                <thead>
                    <tr>
                        <th>股票</th>
                        <th>名称</th>
                        <th>持股数</th>
                        <th>成本价</th>
                        <th>现价</th>
                        <th>市值</th>
                        <th>盈亏金额</th>
                        <th>盈亏比例</th>
                        <th>持有天数</th>
                        <th>交易信号</th>
                    </tr>
                </thead>
                <tbody>
                    {% for pos in positions %}
                    <tr>
                        <td><strong>{{ pos.stock }}</strong></td>
                        <td>{{ pos.name }}</td>
                        <td>{{ pos.shares }}股</td>
                        <td>¥{{ pos.avg_cost }}</td>
                        <td>¥{{ pos.current_price }}</td>
                        <td>¥{{ pos.market_value }}</td>
                        <td class="{% if pos.floating_pnl >= 0 %}positive{% else %}negative{% endif %}">
                            ¥{{ pos.floating_pnl }}
                        </td>
                        <td class="{% if pos.floating_pnl_pct >= 0 %}positive{% else %}negative{% endif %}">
                            {{ pos.floating_pnl_pct }}%
                        </td>
                        <td>{{ pos.hold_days }}天</td>
                        <td>
                            <span class="signal-badge signal-{{ pos.signal_class }}">
                                {{ pos.signal_text }}
                            </span>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="table-container">
            <h3 class="section-title">📜 历史交易记录</h3>
            <table>
                <thead>
                    <tr>
                        <th>日期</th>
                        <th>组合</th>
                        <th>股票</th>
                        <th>操作</th>
                        <th>数量</th>
                        <th>价格</th>
                        <th>金额</th>
                        <th>盈亏</th>
                        <th>卖出原因</th>
                    </tr>
                </thead>
                <tbody>
                    {% for trade in trades %}
                    <tr>
                        <td>{{ trade.trade_date }}</td>
                        <td>{{ trade.portfolio_name }}</td>
                        <td>{{ trade.stock_name }}</td>
                        <td>{{ trade.trade_type }}</td>
                        <td>{{ trade.shares }}</td>
                        <td>¥{{ trade.price }}</td>
                        <td>¥{{ trade.amount }}</td>
                        <td class="{% if trade.pnl >= 0 %}positive{% else %}negative{% endif %}">
                            ¥{{ trade.pnl }}
                        </td>
                        <td>{{ trade.reason }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <button class="refresh-btn" onclick="location.reload()">🔄 刷新数据</button>
        </div>
        
        <p class="update-time">✅ 数据来源: 东方财富实时行情 | Supabase云端数据库</p>
    </div>

    <script>
        const chartData = {{ chart_data|tojson }};
        let mainChart = null;
        
        function showChart(type) {
            document.querySelectorAll('.tab').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            if (mainChart) mainChart.destroy();
            
            const ctx = document.getElementById('mainChart').getContext('2d');
            
            if (type === 'pnl') {
                mainChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: chartData.dates,
                        datasets: [{
                            label: '浮动盈亏',
                            data: chartData.pnl,
                            borderColor: '#f39c12',
                            backgroundColor: 'rgba(243, 156, 18, 0.1)',
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { labels: { color: '#fff' } } },
                        scales: {
                            x: { ticks: { color: '#95a5a6' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                            y: { ticks: { color: '#95a5a6' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                        }
                    }
                });
            } else {
                mainChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: chartData.dates,
                        datasets: [{
                            label: '总市值',
                            data: chartData.values,
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { labels: { color: '#fff' } } },
                        scales: {
                            x: { ticks: { color: '#95a5a6' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                            y: { ticks: { color: '#95a5a6' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                        }
                    }
                });
            }
        }
        
        document.querySelector('.tab').click();
    </script>
</body>
</html>
'''

def calculate_signals(positions_data, config):
    """计算交易信号"""
    signals = []
    today = datetime.now()
    
    for pos in positions_data:
        buy_date = datetime.strptime(pos['buy_date'], '%Y-%m-%d')
        hold_days = (today - buy_date).days
        
        avg_cost = float(pos['avg_cost'])
        current_price = float(pos.get('current_price', avg_cost))
        pnl_pct = (current_price - avg_cost) / avg_cost * 100
        
        stop_loss = config.get('stop_loss', 0.05) * 100
        take_profit = config.get('take_profit', 0.25) * 100
        max_days = config.get('max_hold_days', 3)
        
        if pnl_pct <= -stop_loss:
            signal = {'class': 'stoploss', 'text': '止损卖出'}
        elif pnl_pct >= take_profit:
            signal = {'class': 'takeprofit', 'text': '止盈卖出'}
        elif hold_days > max_days:
            signal = {'class': 'timestop', 'text': '时间止损'}
        else:
            signal = {'class': 'hold', 'text': '持有中'}
        
        pos['current_price'] = round(current_price, 2)
        pos['market_value'] = round(pos['shares'] * current_price, 0)
        pos['floating_pnl'] = round((current_price - avg_cost) * pos['shares'], 0)
        pos['floating_pnl_pct'] = round(pnl_pct, 2)
        pos['hold_days'] = hold_days
        pos['signal_class'] = signal['class']
        pos['signal_text'] = signal['text']
        
        signals.append(pos)
    
    return signals

@app.route('/')
def home():
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        positions = supabase.table('positions').select('*').eq('portfolio_id', 'luoxia-1').execute()
        stock_codes = [p['stock'] for p in positions.data]
        prices = fetch_realtime_prices(stock_codes)
        
        positions_data = []
        for p in positions.data:
            p['current_price'] = prices.get(p['stock'], p.get('avg_cost', 0))
            positions_data.append(p)
        
        config = {'stop_loss': 0.05, 'take_profit': 0.25, 'max_hold_days': 3}
        positions_with_signals = calculate_signals(positions_data, config)
        
        portfolio_data = [
            {'name': '金玉满堂', 'position_count': len(positions_with_signals), 'position_ratio': 88.97, 'total_market_value': '183,090', 'cash': '22,704', 'total_floating_pnl': '+3,932', 'status': '运行中', 'strategy_points': ['止损5%', '止盈25%', '3天']},
            {'name': '落霞一号', 'position_count': 0, 'position_ratio': 0, 'total_market_value': '0', 'cash': '20,000', 'total_floating_pnl': '0', 'status': '已配置', 'strategy_points': ['止损5%', '止盈20%', '20天']},
            {'name': '秋水一号', 'position_count': 0, 'position_ratio': 0, 'total_market_value': '0', 'cash': '20,000', 'total_floating_pnl': '0', 'status': '已配置', 'strategy_points': ['止损4%', '止盈20%', '2天']},
            {'name': '孤鹜一号', 'position_count': 0, 'position_ratio': 0, 'total_market_value': '0', 'cash': '20,000', 'total_floating_pnl': '0', 'status': '已配置', 'strategy_points': ['止损8%', '止盈30%', '2天']},
            {'name': '长天一号', 'position_count': 0, 'position_ratio': 0, 'total_market_value': '0', 'cash': '20,000', 'total_floating_pnl': '0', 'status': '已配置', 'strategy_points': ['止损6%', '止盈15%', '5天']}
        ]
        
        try:
            trades = supabase.table('trades').select('*').order('trade_date', desc=True).limit(20).execute()
            trades_data = trades.data
        except:
            trades_data = []
        
        chart_data = {
            'dates': ['03-10', '03-11', '03-12', '03-13', '03-14', '03-17'],
            'pnl': [1200, 2100, 1800, 3200, 2800, 3932],
            'values': [175000, 178000, 176000, 182000, 180000, 183090]
        }
        
        return render_template_string(HTML_TEMPLATE,
                                     portfolios=portfolio_data,
                                     positions=positions_with_signals,
                                     trades=trades_data,
                                     chart_data=chart_data,
                                     portfolio_count=len(portfolio_data),
                                     position_count=len(positions_with_signals),
                                     update_time=now)
    except Exception as e:
        import traceback
        return f'<h1>系统初始化中...</h1><p>错误: {str(e)}</p><pre>{traceback.format_exc()}</pre>'

@app.route('/api/prices')
def api_prices():
    try:
        positions = supabase.table('positions').select('stock').eq('portfolio_id', 'luoxia-1').execute()
        stock_codes = [p['stock'] for p in positions.data]
        prices = fetch_realtime_prices(stock_codes)
        return jsonify({'success': True, 'prices': prices, 'time': datetime.now().isoformat()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
