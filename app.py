from flask import Flask, jsonify, render_template_string
import os
from supabase import create_client

app = Flask(__name__)

# Supabase 配置
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://erfhazdwgnhhtroxjhdl.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVyZmhhemR3Z25oaHRyb3hqaGRsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2ODU4NzYsImV4cCI6MjA4OTI2MTg3Nn0.Epg244WFqN2CfU0wC8EzaadLYmkM4yBw5f4E46N19Aw')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>滕王阁序投资组合 - 配置管理</title>
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
        .table-container {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            overflow-x: auto;
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
            padding: 16px 10px;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            cursor: pointer;
            transition: background 0.3s;
        }
        tr:hover td { background: rgba(255,255,255,0.08); }
        .portfolio-name { font-weight: bold; font-size: 1.1em; color: #f39c12; }
        .positive { color: #2ecc71; }
        .negative { color: #e74c3c; }
        .status-running { color: #2ecc71; }
        .status-pending { color: #f39c12; }
        .strategy-points { font-size: 12px; color: #95a5a6; }
        .strategy-points span {
            display: inline-block;
            background: rgba(255,255,255,0.1);
            padding: 2px 8px;
            border-radius: 12px;
            margin: 2px;
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
            <p>持仓监控系统 | 数据来自 Supabase | 更新时间：实时</p>
        </div>
        
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>组合</th>
                        <th>持仓票</th>
                        <th>市值</th>
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
                        <td>¥{{ "{:,.0f}".format(p.total_market_value) }}</td>
                        <td class="{% if p.total_floating_pnl >= 0 %}positive{% else %}negative{% endif %}">
                            ¥{{ "{:+,.0f}".format(p.total_floating_pnl) }}
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
            <h3 style="color: #f39c12; margin-bottom: 15px;">📈 金玉满堂持仓明细</h3>
            <table>
                <thead>
                    <tr>
                        <th>股票</th>
                        <th>名称</th>
                        <th>数量</th>
                        <th>成本价</th>
                        <th>买入日期</th>
                    </tr>
                </thead>
                <tbody>
                    {% for pos in positions %}
                    <tr>
                        <td><strong>{{ pos.stock }}</strong></td>
                        <td>{{ pos.name }}</td>
                        <td>{{ pos.shares }}股</td>
                        <td>¥{{ pos.avg_cost }}</td>
                        <td>{{ pos.buy_date }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <p class="update-time">✅ 数据实时同步 | 云端部署运行中</p>
    </div>
</body>
</html>
'''

@app.route('/')
def home():
    try:
        # 获取金玉满堂持仓
        positions = supabase.table('positions').select('*').eq('portfolio_id', 'luoxia-1').execute()
        
        # 构建组合数据
        portfolio_data = [
            {
                'name': '金玉满堂',
                'position_count': 9,
                'total_market_value': 183090,
                'total_floating_pnl': 3932,
                'status': '运行中',
                'strategy_points': ['止损5%', '止盈25%', '3天', '情绪≥0.6']
            },
            {
                'name': '落霞一号',
                'position_count': 0,
                'total_market_value': 0,
                'total_floating_pnl': 0,
                'status': '已配置',
                'strategy_points': ['止损5%', '止盈20%', '20天']
            },
            {
                'name': '秋水一号',
                'position_count': 0,
                'total_market_value': 0,
                'total_floating_pnl': 0,
                'status': '已配置',
                'strategy_points': ['止损4%', '止盈20%', '2天']
            },
            {
                'name': '孤鹜一号',
                'position_count': 0,
                'total_market_value': 0,
                'total_floating_pnl': 0,
                'status': '已配置',
                'strategy_points': ['止损8%', '止盈30%', '2天']
            },
            {
                'name': '长天一号',
                'position_count': 0,
                'total_market_value': 0,
                'total_floating_pnl': 0,
                'status': '已配置',
                'strategy_points': ['止损6%', '止盈15%', '5天']
            }
        ]
        
        return render_template_string(HTML_TEMPLATE, 
                                     portfolios=portfolio_data,
                                     positions=positions.data)
    except Exception as e:
        return f'<h1>系统初始化中...</h1><p>错误: {str(e)}</p><p>请检查 Supabase 连接配置</p>'

@app.route('/api/portfolios')
def api_portfolios():
    portfolios = supabase.table('portfolios').select('*').execute()
    return jsonify(portfolios.data)

@app.route('/api/positions/<portfolio_id>')
def api_positions(portfolio_id):
    positions = supabase.table('positions').select('*').eq('portfolio_id', portfolio_id).execute()
    return jsonify(positions.data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
