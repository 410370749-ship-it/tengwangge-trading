from flask import Flask, jsonify, render_template_string
import os
from supabase import create_client

app = Flask(__name__)

# Supabase 配置
SUPABASE_URL = "https://erfhazdwgnhhtroxjhdl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVyZmhhemR3Z25oaHRyb3hqaGRsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2ODU4NzYsImV4cCI6MjA4OTI2MTg3Nn0.Epg244WFqN2CfU0wC8EzaadLYmkM4yBw5f4E46N19Aw"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/')
def home():
    # 获取持仓数据
    positions = supabase.table('positions').select('*').execute()
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>滕王阁序交易系统</title>
        <style>
            body { font-family: Arial; background: #1a1a2e; color: #fff; padding: 20px; }
            h1 { color: #f39c12; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th { background: #f39c12; color: #000; padding: 10px; }
            td { padding: 10px; border-bottom: 1px solid #333; text-align: center; }
            .profit { color: #2ecc71; }
            .loss { color: #e74c3c; }
        </style>
    </head>
    <body>
        <h1>🏮 滕王阁序交易系统</h1>
        <h3>金玉满堂组合 - 持仓监控</h3>
        <table>
            <tr>
                <th>股票</th>
                <th>名称</th>
                <th>数量</th>
                <th>成本价</th>
                <th>买入日期</th>
            </tr>
            {% for pos in positions.data %}
            <tr>
                <td>{{ pos.stock }}</td>
                <td>{{ pos.name }}</td>
                <td>{{ pos.shares }}</td>
                <td>¥{{ pos.avg_cost }}</td>
                <td>{{ pos.buy_date }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    ''', positions=positions)

@app.route('/api/positions')
def api_positions():
    positions = supabase.table('positions').select('*').execute()
    return jsonify(positions.data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)