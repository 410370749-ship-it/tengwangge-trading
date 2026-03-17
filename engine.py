#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
滕王阁序量化交易系统 - 核心引擎
支持: 持仓管理、止损计算、预警通知
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import requests
import pandas as pd

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


class SignalType(Enum):
    HOLD = "hold"
    STOP_LOSS = "stop_loss"      # 止损
    TAKE_PROFIT = "take_profit"  # 止盈
    TIME_STOP = "time_stop"      # 时间止损
    BUY = "buy"
    SELL = "sell"


@dataclass
class Position:
    """持仓数据类"""
    stock: str
    name: str
    shares: int
    avg_cost: float
    buy_date: str
    current_price: float = 0.0
    
    @property
    def market_value(self) -> float:
        return self.shares * self.current_price
    
    @property
    def floating_pnl(self) -> float:
        return (self.current_price - self.avg_cost) * self.shares
    
    @property
    def floating_pnl_pct(self) -> float:
        return (self.current_price - self.avg_cost) / self.avg_cost
    
    def hold_days(self, today: Optional[str] = None) -> int:
        """计算持有天数"""
        if today is None:
            today = datetime.now().strftime("%Y-%m-%d")
        buy = datetime.strptime(self.buy_date, "%Y-%m-%d")
        end = datetime.strptime(today, "%Y-%m-%d")
        return (end - buy).days


@dataclass
class Signal:
    """交易信号"""
    portfolio_id: str
    portfolio_name: str
    stock: str
    stock_name: str
    signal_type: SignalType
    reason: str
    current_price: float
    avg_cost: float
    pnl_pct: float
    hold_days: int
    suggestion: str


@dataclass
class Trade:
    """交易记录"""
    trade_id: str
    portfolio_id: str
    portfolio_name: str
    stock: str
    stock_name: str
    trade_type: str  # BUY / SELL
    shares: int
    price: float
    amount: float
    date: str
    time: str
    pnl: float = 0.0  # 卖出时记录盈亏
    pnl_pct: float = 0.0
    reason: str = ""  # 交易原因（止损/止盈/时间止损等）
    notes: str = ""


class DataSource:
    """数据源接口 - 已接入AkShare"""
    
    def __init__(self, provider: str = "mock"):
        self.provider = provider
        self._cache = {}
        self._cache_time = None
        self._df_spot = None
        
        if provider == "akshare":
            try:
                import akshare as ak
                self.ak = ak
                print("✅ AkShare 数据源已加载")
            except ImportError:
                print("⚠️ 未安装 AkShare，使用模拟数据")
                print("   运行: pip install akshare")
                self.provider = "mock"
    
    def _fetch_spot_data(self) -> Dict[str, float]:
        """获取A股实时行情"""
        if self.provider != "akshare":
            return {}
        
        # 缓存5秒，避免频繁请求
        now = datetime.now()
        if self._cache_time and (now - self._cache_time).seconds < 5:
            return self._cache
        
        try:
            # 获取东方财富实时行情
            df = self.ak.stock_zh_a_spot_em()
            # 构建代码到价格的映射
            price_map = {}
            for _, row in df.iterrows():
                code = row['代码']
                price = float(row['最新价']) if pd.notna(row['最新价']) else 0.0
                price_map[code] = price
            
            self._cache = price_map
            self._cache_time = now
            return price_map
        except Exception as e:
            print(f"❌ AkShare 获取数据失败: {e}")
            return {}
    
    def get_price(self, stock_code: str) -> float:
        """获取最新价格"""
        if self.provider == "akshare":
            # 转换代码格式: 000001.SZ -> 000001
            code = stock_code.replace('.SZ', '').replace('.SH', '').replace('.BJ', '')
            prices = self._fetch_spot_data()
            if code in prices and prices[code] > 0:
                return prices[code]
            print(f"⚠️ 未找到 {stock_code} 实时价格，使用模拟数据")
        
        # 模拟价格（基于股票代码生成固定但合理的价格）
        import hashlib
        seed = int(hashlib.md5(stock_code.encode()).hexdigest(), 16)
        base_price = 20 + (seed % 200)
        import random
        random.seed(datetime.now().strftime("%Y%m%d"))
        fluctuation = random.uniform(-0.02, 0.02)
        return round(base_price * (1 + fluctuation), 2)
    
    def batch_get_prices(self, stock_codes: List[str]) -> Dict[str, float]:
        """批量获取价格"""
        return {code: self.get_price(code) for code in stock_codes}


class Notification:
    """通知服务"""
    
    def __init__(self, config: Dict):
        self.config = config
        
    def send(self, title: str, message: str, signals: List[Signal] = None):
        """发送通知"""
        # 控制台输出
        print(f"\n{'='*60}")
        print(f"【{title}】")
        print(f"{'='*60}")
        print(message)
        
        if signals:
            print(f"\n⚠️  发现 {len(signals)} 个交易信号:\n")
            for i, sig in enumerate(signals, 1):
                emoji = {
                    SignalType.STOP_LOSS: "🔴",
                    SignalType.TAKE_PROFIT: "🟢", 
                    SignalType.TIME_STOP: "⏰",
                    SignalType.HOLD: "⚪"
                }.get(sig.signal_type, "⚪")
                
                print(f"{i}. {emoji} {sig.portfolio_name} - {sig.stock_name}({sig.stock})")
                print(f"   信号: {sig.signal_type.value} | 原因: {sig.reason}")
                print(f"   成本: ¥{sig.avg_cost:.2f} → 现价: ¥{sig.current_price:.2f}")
                print(f"   盈亏: {sig.pnl_pct:+.2%} | 持有: {sig.hold_days}天")
                print(f"   建议: {sig.suggestion}")
                print()
        
        # TODO: 接入钉钉/飞书Webhook
        self._send_dingtalk(title, message, signals)
        self._send_feishu(title, message, signals)
    
    def _send_dingtalk(self, title: str, message: str, signals: List[Signal] = None):
        """发送钉钉通知"""
        webhook = self.config.get("dingtalk_webhook", "")
        if not webhook:
            return
        
        # 构建钉钉消息
        content = f"### {title}\n\n{message}"
        if signals:
            content += f"\n\n发现 **{len(signals)}** 个交易信号:\n"
            for sig in signals:
                emoji = {"stop_loss": "🔴", "take_profit": "🟢", "time_stop": "⏰"}.get(sig.signal_type.value, "⚪")
                content += f"\n{emoji} **{sig.portfolio_name}** - {sig.stock_name}\n"
                content += f"> 信号: {sig.signal_type.value} | 盈亏: {sig.pnl_pct:+.2%}\n"
                content += f"> 建议: {sig.suggestion}\n"
        
        payload = {
            "msgtype": "markdown",
            "markdown": {"title": title, "text": content}
        }
        
        try:
            requests.post(webhook, json=payload, timeout=5)
        except Exception as e:
            print(f"钉钉通知发送失败: {e}")
    
    def _send_feishu(self, title: str, message: str, signals: List[Signal] = None):
        """发送飞书通知"""
        webhook = self.config.get("feishu_webhook", "")
        if not webhook:
            return
        
        # 构建飞书消息
        content = f"**{title}**\n\n{message}"
        if signals:
            content += f"\n\n发现 {len(signals)} 个交易信号:\n"
            for sig in signals:
                content += f"\n• {sig.portfolio_name} - {sig.stock_name}: {sig.signal_type.value}"
        
        payload = {
            "msg_type": "text",
            "content": {"text": content}
        }
        
        try:
            requests.post(webhook, json=payload, timeout=5)
        except Exception as e:
            print(f"飞书通知发送失败: {e}")


class TradingEngine:
    """交易引擎"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        # 优先使用配置中的数据源设置
        ds_config = self.config.get("data_source", {})
        provider = ds_config.get("provider", "mock")
        # 如果配置了启用akshare，即使provider是mock也尝试使用akshare
        if ds_config.get("akshare_enabled") and provider == "mock":
            provider = "akshare"
        self.data_source = DataSource(provider)
        self.notification = Notification(self.config.get("notifications", {}))
        self.signals: List[Signal] = []
        
    def _load_config(self) -> Dict:
        """加载配置"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_config(self):
        """保存配置 (持仓更新时)"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def check_portfolio(self, portfolio: Dict) -> List[Signal]:
        """检查单个组合的所有持仓"""
        signals = []
        positions = portfolio.get("positions", [])
        
        if not positions:
            return signals
        
        # 批量获取最新价格
        stock_codes = [p["stock"] for p in positions]
        prices = self.data_source.batch_get_prices(stock_codes)
        
        cfg = portfolio["config"]
        today = datetime.now().strftime("%Y-%m-%d")
        
        for pos_data in positions:
            stock = pos_data["stock"]
            name = pos_data["name"]
            current_price = prices.get(stock, pos_data.get("avg_cost", 0))
            
            position = Position(
                stock=stock,
                name=name,
                shares=pos_data["shares"],
                avg_cost=pos_data["avg_cost"],
                buy_date=pos_data["buy_date"],
                current_price=current_price
            )
            
            # 检查各种条件
            hold_days = position.hold_days(today)
            pnl_pct = position.floating_pnl_pct
            
            # 1. 止损检查
            if pnl_pct <= -cfg["stop_loss"]:
                signals.append(Signal(
                    portfolio_id=portfolio["id"],
                    portfolio_name=portfolio["name"],
                    stock=stock,
                    stock_name=name,
                    signal_type=SignalType.STOP_LOSS,
                    reason=f"跌幅达到 {abs(pnl_pct):.2%}，超过止损线 {cfg['stop_loss']:.0%}",
                    current_price=current_price,
                    avg_cost=position.avg_cost,
                    pnl_pct=pnl_pct,
                    hold_days=hold_days,
                    suggestion=f"建议立即卖出 {position.shares} 股"
                ))
            
            # 2. 止盈检查
            elif pnl_pct >= cfg["take_profit"]:
                signals.append(Signal(
                    portfolio_id=portfolio["id"],
                    portfolio_name=portfolio["name"],
                    stock=stock,
                    stock_name=name,
                    signal_type=SignalType.TAKE_PROFIT,
                    reason=f"涨幅达到 {pnl_pct:.2%}，达到止盈线 {cfg['take_profit']:.0%}",
                    current_price=current_price,
                    avg_cost=position.avg_cost,
                    pnl_pct=pnl_pct,
                    hold_days=hold_days,
                    suggestion=f"建议卖出止盈 {position.shares} 股"
                ))
            
            # 3. 时间止损检查
            elif hold_days > cfg["max_hold_days"]:
                signals.append(Signal(
                    portfolio_id=portfolio["id"],
                    portfolio_name=portfolio["name"],
                    stock=stock,
                    stock_name=name,
                    signal_type=SignalType.TIME_STOP,
                    reason=f"已持有 {hold_days} 天，超过最大持仓期 {cfg['max_hold_days']} 天",
                    current_price=current_price,
                    avg_cost=position.avg_cost,
                    pnl_pct=pnl_pct,
                    hold_days=hold_days,
                    suggestion=f"建议评估后卖出（盈亏: {pnl_pct:+.2%}）"
                ))
            
            else:
                # 正常持有
                signals.append(Signal(
                    portfolio_id=portfolio["id"],
                    portfolio_name=portfolio["name"],
                    stock=stock,
                    stock_name=name,
                    signal_type=SignalType.HOLD,
                    reason=f"正常持有中",
                    current_price=current_price,
                    avg_cost=position.avg_cost,
                    pnl_pct=pnl_pct,
                    hold_days=hold_days,
                    suggestion="继续持有"
                ))
        
        return signals
    
    def run_daily_check(self):
        """每日扫描所有组合"""
        all_signals = []
        alert_signals = []
        
        print(f"\n🚀 滕王阁序交易系统 - 每日扫描")
        print(f"⏰ 扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 监控组合: {len(self.config['portfolios'])} 个")
        print("-" * 60)
        
        for portfolio in self.config["portfolios"]:
            signals = self.check_portfolio(portfolio)
            all_signals.extend(signals)
            
            # 筛选需要告警的信号
            for sig in signals:
                if sig.signal_type in [SignalType.STOP_LOSS, SignalType.TAKE_PROFIT, SignalType.TIME_STOP]:
                    alert_signals.append(sig)
        
        # 发送通知
        if alert_signals:
            self.notification.send(
                title=f"⚠️ 交易预警 - 发现 {len(alert_signals)} 个信号",
                message=f"扫描完成，{len(self.config['portfolios'])} 个组合，共 {len(all_signals)} 只持仓，其中 {len(alert_signals)} 只需要关注。",
                signals=alert_signals
            )
        else:
            self.notification.send(
                title="✅ 每日扫描完成 - 无异常",
                message=f"所有 {len(self.config['portfolios'])} 个组合运行正常，{len(all_signals)} 只持仓均无触发止损/止盈/时间止损。"
            )
        
        return alert_signals
    
    def generate_report(self) -> Dict:
        """生成报表数据 (供HTML展示)"""
        report = {
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "portfolios": []
        }
        
        for portfolio in self.config["portfolios"]:
            positions_data = []
            total_market_value = 0
            total_floating_pnl = 0
            
            stock_codes = [p["stock"] for p in portfolio.get("positions", [])]
            prices = self.data_source.batch_get_prices(stock_codes)
            
            for pos_data in portfolio.get("positions", []):
                stock = pos_data["stock"]
                current_price = prices.get(stock, pos_data["avg_cost"])
                market_value = pos_data["shares"] * current_price
                floating_pnl = (current_price - pos_data["avg_cost"]) * pos_data["shares"]
                
                positions_data.append({
                    "stock": stock,
                    "name": pos_data["name"],
                    "buy_date": pos_data["buy_date"],
                    "shares": pos_data["shares"],
                    "avg_cost": pos_data["avg_cost"],
                    "current_price": current_price,
                    "market_value": market_value,
                    "floating_pnl": floating_pnl,
                    "floating_pnl_pct": (current_price - pos_data["avg_cost"]) / pos_data["avg_cost"],
                    "position_ratio": 0  # 稍后计算
                })
                
                total_market_value += market_value
                total_floating_pnl += floating_pnl
            
            # 计算仓位占比
            total_asset = total_market_value + portfolio.get("cash", 0)
            for pos in positions_data:
                pos["position_ratio"] = (pos["market_value"] / total_asset * 100) if total_asset > 0 else 0
            
            report["portfolios"].append({
                "id": portfolio["id"],
                "name": portfolio["name"],
                "status": "运行中" if positions_data else "空仓",
                "initial_capital": portfolio["initial_capital"],
                "cash": portfolio.get("cash", 0),
                "position_count": len(positions_data),
                "position_ratio": (total_market_value / total_asset * 100) if total_asset > 0 else 0,
                "total_market_value": total_market_value,
                "total_floating_pnl": total_floating_pnl,
                "positions": positions_data
            })
        
        return report
    
    # ==================== 交易功能 ====================
    
    def _get_trade_file(self) -> Path:
        """获取交易记录文件路径"""
        trade_dir = PROJECT_ROOT / "trades"
        trade_dir.mkdir(exist_ok=True)
        today = datetime.now().strftime("%Y%m")
        return trade_dir / f"trades_{today}.json"
    
    def _load_trades(self) -> List[Dict]:
        """加载交易记录"""
        trade_file = self._get_trade_file()
        if trade_file.exists():
            with open(trade_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_trade(self, trade: Trade):
        """保存单笔交易"""
        trades = self._load_trades()
        trades.append(asdict(trade))
        
        trade_file = self._get_trade_file()
        with open(trade_file, 'w', encoding='utf-8') as f:
            json.dump(trades, f, ensure_ascii=False, indent=2)
        
        # 同时更新历史总记录
        self._update_trade_history(trade)
    
    def _update_trade_history(self, trade: Trade):
        """更新交易历史统计"""
        history_file = PROJECT_ROOT / "trades" / "trade_history.json"
        
        history = {"trades": [], "stats": {}}
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        
        history["trades"].append(asdict(trade))
        
        # 更新统计
        sells = [t for t in history["trades"] if t["trade_type"] == "SELL"]
        profits = [t for t in sells if t.get("pnl", 0) > 0]
        losses = [t for t in sells if t.get("pnl", 0) <= 0]
        
        history["stats"] = {
            "total_trades": len(sells),
            "profit_count": len(profits),
            "loss_count": len(losses),
            "win_rate": len(profits) / len(sells) * 100 if sells else 0,
            "total_pnl": sum(t.get("pnl", 0) for t in sells),
            "avg_profit": sum(t.get("pnl", 0) for t in profits) / len(profits) if profits else 0,
            "avg_loss": sum(t.get("pnl", 0) for t in losses) / len(losses) if losses else 0,
        }
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def execute_sell(self, portfolio_id: str, stock_code: str, confirm: bool = True) -> Optional[Trade]:
        """
        执行卖出操作
        
        Args:
            portfolio_id: 组合ID
            stock_code: 股票代码
            confirm: 是否需要确认
        
        Returns:
            Trade对象或None
        """
        # 查找组合和持仓
        portfolio = None
        position_idx = -1
        position_data = None
        
        for i, p in enumerate(self.config["portfolios"]):
            if p["id"] == portfolio_id:
                portfolio = p
                for j, pos in enumerate(p.get("positions", [])):
                    if pos["stock"] == stock_code:
                        position_idx = j
                        position_data = pos
                        break
                break
        
        if not portfolio or not position_data:
            print(f"❌ 未找到持仓: {portfolio_id} - {stock_code}")
            return None
        
        # 获取当前价格
        current_price = self.data_source.get_price(stock_code)
        shares = position_data["shares"]
        avg_cost = position_data["avg_cost"]
        amount = shares * current_price
        pnl = (current_price - avg_cost) * shares
        pnl_pct = (current_price - avg_cost) / avg_cost
        
        # 显示交易信息
        print(f"\n{'='*60}")
        print(f"📤 卖出确认 - {portfolio['name']}")
        print(f"{'='*60}")
        print(f"股票: {position_data['name']} ({stock_code})")
        print(f"数量: {shares} 股")
        print(f"成本: ¥{avg_cost:.2f}")
        print(f"现价: ¥{current_price:.2f}")
        print(f"金额: ¥{amount:,.2f}")
        print(f"盈亏: ¥{pnl:+,.2f} ({pnl_pct:+.2%})")
        print(f"{'='*60}")
        
        # 确认卖出
        if confirm:
            try:
                user_input = input("\n确认卖出? [y/N]: ").strip().lower()
                if user_input != 'y':
                    print("❌ 已取消")
                    return None
            except (EOFError, KeyboardInterrupt):
                print("\n❌ 已取消")
                return None
        
        # 创建交易记录
        now = datetime.now()
        trade = Trade(
            trade_id=f"{now.strftime('%Y%m%d%H%M%S')}_{stock_code}",
            portfolio_id=portfolio_id,
            portfolio_name=portfolio["name"],
            stock=stock_code,
            stock_name=position_data["name"],
            trade_type="SELL",
            shares=shares,
            price=current_price,
            amount=amount,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            pnl=pnl,
            pnl_pct=pnl_pct,
            reason=input("卖出原因 (可选): ").strip() if confirm else "",
            notes=""
        )
        
        # 更新持仓（移除该股票）
        del portfolio["positions"][position_idx]
        
        # 更新现金
        portfolio["cash"] = portfolio.get("cash", 0) + amount
        
        # 保存配置
        self._save_config()
        
        # 保存交易记录
        self._save_trade(trade)
        
        print(f"\n✅ 卖出成功!")
        print(f"   交易ID: {trade.trade_id}")
        print(f"   已保存到交易记录")
        
        return trade
    
    def batch_sell(self, signals: List[Signal], interactive: bool = True):
        """
        批量卖出 - 一键确认模式
        
        Args:
            signals: 需要卖出的信号列表
            interactive: 是否交互式确认
        """
        if not signals:
            print("没有需要卖出的信号")
            return []
        
        sell_signals = [s for s in signals if s.signal_type in 
                       [SignalType.STOP_LOSS, SignalType.TAKE_PROFIT, SignalType.TIME_STOP]]
        
        if not sell_signals:
            print("没有触发卖出条件的信号")
            return []
        
        print(f"\n{'='*60}")
        print(f"📋 批量卖出清单 - 共 {len(sell_signals)} 只")
        print(f"{'='*60}")
        
        for i, sig in enumerate(sell_signals, 1):
            emoji = {"stop_loss": "🔴", "take_profit": "🟢", "time_stop": "⏰"}.get(sig.signal_type.value, "⚪")
            print(f"{i}. {emoji} {sig.stock_name} ({sig.stock})")
            print(f"   原因: {sig.reason}")
            print(f"   盈亏: {sig.pnl_pct:+.2%} | 建议: {sig.suggestion}")
            print()
        
        if interactive:
            try:
                # 提供选项
                print("选项:")
                print("  [a] 全部卖出")
                print("  [1,2,3] 选择序号卖出 (逗号分隔)")
                print("  [q] 取消")
                user_input = input("\n请选择: ").strip().lower()
                
                if user_input == 'q':
                    print("❌ 已取消")
                    return []
                
                if user_input == 'a':
                    # 全部卖出
                    to_sell = sell_signals
                else:
                    # 选择部分
                    try:
                        indices = [int(x.strip()) - 1 for x in user_input.split(',')]
                        to_sell = [sell_signals[i] for i in indices if 0 <= i < len(sell_signals)]
                    except (ValueError, IndexError):
                        print("❌ 输入无效")
                        return []
                
                # 执行卖出
                executed = []
                for sig in to_sell:
                    trade = self.execute_sell(sig.portfolio_id, sig.stock, confirm=False)
                    if trade:
                        executed.append(trade)
                
                print(f"\n✅ 共执行 {len(executed)} 笔卖出")
                return executed
                
            except (EOFError, KeyboardInterrupt):
                print("\n❌ 已取消")
                return []
        else:
            # 非交互模式，全部卖出
            executed = []
            for sig in sell_signals:
                trade = self.execute_sell(sig.portfolio_id, sig.stock, confirm=False)
                if trade:
                    executed.append(trade)
            return executed
    
    def show_trade_history(self, portfolio_id: Optional[str] = None, limit: int = 20):
        """显示交易历史"""
        trades = self._load_trades()
        
        if portfolio_id:
            trades = [t for t in trades if t["portfolio_id"] == portfolio_id]
        
        trades = sorted(trades, key=lambda x: x["trade_id"], reverse=True)[:limit]
        
        if not trades:
            print("暂无交易记录")
            return
        
        print(f"\n{'='*80}")
        print(f"📜 最近 {len(trades)} 笔交易记录")
        print(f"{'='*80}")
        print(f"{'日期':<12} {'时间':<10} {'组合':<10} {'股票':<10} {'类型':<6} {'数量':>8} {'价格':>10} {'盈亏':>12}")
        print("-" * 80)
        
        for t in trades:
            pnl_str = f"{t.get('pnl', 0):+,.0f}" if t["trade_type"] == "SELL" else "-"
            print(f"{t['date']:<12} {t['time']:<10} {t['portfolio_name']:<10} {t['stock_name']:<10} "
                  f"{t['trade_type']:<6} {t['shares']:>8} ¥{t['price']:>8.2f} {pnl_str:>12}")
        
        # 显示统计
        history_file = PROJECT_ROOT / "trades" / "trade_history.json"
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                stats = history.get("stats", {})
                if stats:
                    print(f"\n{'='*80}")
                    print(f"📊 交易统计")
                    print(f"{'='*80}")
                    print(f"总交易次数: {stats.get('total_trades', 0)}")
                    print(f"盈利次数: {stats.get('profit_count', 0)}")
                    print(f"亏损次数: {stats.get('loss_count', 0)}")
                    print(f"胜率: {stats.get('win_rate', 0):.1f}%")
                    print(f"总盈亏: ¥{stats.get('total_pnl', 0):+,.2f}")
                    print(f"平均盈利: ¥{stats.get('avg_profit', 0):,.2f}")
                    print(f"平均亏损: ¥{stats.get('avg_loss', 0):,.2f}")


def interactive_mode():
    """交互式交易模式"""
    engine = TradingEngine()
    
    while True:
        print(f"\n{'='*60}")
        print("🏮 滕王阁序交易系统 - 交互模式")
        print(f"{'='*60}")
        print("1. 扫描持仓 (检查止损/止盈/时间止损)")
        print("2. 一键卖出 (批量处理信号)")
        print("3. 手动卖出 (指定股票)")
        print("4. 查看交易记录")
        print("5. 生成报表")
        print("q. 退出")
        
        try:
            choice = input("\n请选择: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n再见!")
            break
        
        if choice == 'q':
            print("再见!")
            break
        
        elif choice == '1':
            signals = engine.run_daily_check()
            engine.signals = signals
        
        elif choice == '2':
            if not engine.signals:
                print("请先运行扫描 (选项1)")
                continue
            engine.batch_sell(engine.signals)
            engine.signals = []  # 清空信号
        
        elif choice == '3':
            print("\n可用组合:")
            for p in engine.config["portfolios"]:
                pos_count = len(p.get("positions", []))
                print(f"  {p['id']}: {p['name']} ({pos_count}只持仓)")
            
            portfolio_id = input("\n输入组合ID: ").strip()
            stock_code = input("输入股票代码 (如 000001): ").strip()
            if stock_code and not stock_code.startswith(('0', '3', '6', '8', '9')):
                print("❌ 股票代码格式错误")
                continue
            engine.execute_sell(portfolio_id, stock_code)
        
        elif choice == '4':
            engine.show_trade_history()
        
        elif choice == '5':
            report = engine.generate_report()
            print(f"\n报表已生成，包含 {len(report['portfolios'])} 个组合")
            for p in report["portfolios"]:
                print(f"  {p['name']}: {p['position_count']}只持仓, 总市值 ¥{p['total_market_value']:,.0f}")
        
        else:
            print("无效选项")


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        engine = TradingEngine()
        signals = engine.run_daily_check()
        
        # 如果有卖出信号，提示可以使用交互模式
        sell_signals = [s for s in signals if s.signal_type in 
                       [SignalType.STOP_LOSS, SignalType.TAKE_PROFIT, SignalType.TIME_STOP]]
        if sell_signals:
            print(f"\n💡 提示: 发现 {len(sell_signals)} 个卖出信号")
            print("   运行 'python engine.py --interactive' 进入交互模式进行一键卖出")


if __name__ == "__main__":
    main()
