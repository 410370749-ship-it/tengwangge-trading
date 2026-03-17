#!/bin/bash
# 滕王阁序交易系统 - 每日扫描脚本

cd /root/.openclaw/workspace/quant
python3 engine.py >> logs/daily_$(date +%Y%m%d).log 2>&1
