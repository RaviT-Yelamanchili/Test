#!/usr/bin/env python3
"""
Chess-Framework Momentum Backtester (single-file version)

Save this as `chess_backtester_single_file.py`.

Dependencies:
  pip install pandas numpy yfinance tqdm python-dateutil

Usage:
  python chess_backtester_single_file.py
  python chess_backtester_single_file.py --config example_config.json
  python chess_backtester_single_file.py --tickers AAPL MSFT GOOGL --capital 100000 --risk Moderate

Output:
  - trades.csv written to the current directory
  - Console prints a short summary and piece inventory state

Notes:
  - This is the same MVP prototype but consolidated into one file for easier execution.
  - Default MA period = 50 (SMA). Tactical reclaim window = 3 days.
  - Data loaded via yfinance (internet required).
"""

import argparse
import json
import os
import uuid
from datetime import datetime
from collections import OrderedDict

import numpy as np
import pandas as pd
import yfinance as yf
from tqdm import tqdm

# ---------------------------
# Default config (in-file)
# ---------------------------
DEFAULT_CONFIG = {
    "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
    "total_capital": 100000,
    "risk_level": "Moderate",  # High/Moderate/Low
    "ma_type": "SMA",
    "ma_period": 50,
    "start_date": None,
    "end_date": None,
    "reclaim_window_days": 3,
    "max_positions": 8
}

# ---------------------------
# SOS utilities (from sos.py)
# ---------------------------

def compute_sos_frame(price_df, ma_period=50, weights=None):
    """
    Returns a DataFrame with MultiIndex columns (ticker, metric) for metrics:
    PRICE, MA, MOM, VOL, SOS
    """
    if weights is None:
        weights = {"M": 0.6, "Vol": 0.25, "Lq": 0.15}
    tickers = price_df.columns.tolist()
    ma = price_df.rolling(window=ma_period, min_periods=ma_period).mean()
    returns = price_df.pct_change().fillna(0)
    vol = returns.rolling(window=ma_period, min_periods=ma_period).std()

    mom = price_df / ma - 1.0

    out = pd.DataFrame(index=price_df.index)
    for t in tickers:
        out[(t, "PRICE")] = price_df[t]
        out[(t, "MA")] = ma[t]
        out[(t, "MOM")] = mom[t]
        out[(t, "VOL")] = vol[t]
        out[(t, "SOS")] = np.nan

    out.columns = pd.MultiIndex.from_tuples(out.columns)

    # Compute SOS per date across tickers
    for date in price_df.index:
        mom_raw = out.loc[date, pd.IndexSlice[:, "MOM"]].fillna(0)
        vol_raw = out.loc[date, pd.IndexSlice[:, "VOL"]].fillna(0)
        # Normalize mom to 0..1
        if mom_raw.max() == mom_raw.min():
            mom_score = pd.Series(0.5, index=mom_raw.index)
        else:
            mom_score = (mom_raw - mom_raw.min()) / (mom_raw.max() - mom_raw.min())
        # Volatility score: lower vol -> higher score
        if vol_raw.max() == vol_raw.min():
            vol_score = pd.Series(0.5, index=vol_raw.index)
        else:
            vol_score = 1.0 - (vol_raw - vol_raw.min()) / (vol_raw.max() - vol_raw.min())
        # Liquidity placeholder (neutral)
        lq_score = pd.Series(0.5, index=mom_raw.index)

        sos_raw = weights["M"] * mom_score + weights["Vol"] * vol_score + weights["Lq"] * lq_score
        if sos_raw.max() == sos_raw.min():
            sos_norm = pd.Series(0.5, index=sos_raw.index)
        else:
            sos_norm = (sos_raw - sos_raw.min()) / (sos_raw.max() - sos_raw.min())

        for ticker_idx, t in enumerate(tickers):
            out.at[date, (t, "SOS")] = sos_norm.iloc[ticker_idx]

    out = out.reindex(sorted(out.columns), axis=1)
    return out

def map_sos_to_rank(sos_value):
    r = 1 + int(np.floor((1.0 - float(sos_value)) * 8.0))
    if r < 1:
        r = 1
    if r > 8:
        r = 8
    return r

def map_sos_to_file(sos_value_secondary):
    idx = int(np.floor(float(sos_value_secondary) * 8.0))
    if idx < 0: idx = 0
    if idx > 7: idx = 7
    return "ABCDEFGH"[idx]

def map_sos_to_tile(sos_value):
    rank = map_sos_to_rank(sos_value)
    file = map_sos_to_file(sos_value)
    return rank, file

# ---------------------------
# Rules & Inventory (from rules.py)
# ---------------------------

TOTAL_POINTS = 39  # per spec

class PieceInventory:
    def __init__(self, momentum_capital):
        self.momentum_capital = float(momentum_capital)
        self.pieces = []  # list of piece dicts: id,type,PV,value,assigned
        self._build_pieces()

    def _build_pieces(self):
        mapping = [
            ("Queen", 9, 1),
            ("Rook", 5, 2),
            ("Bishop", 3, 2),
            ("Knight", 3, 2),
            ("Pawn", 1, 8)
        ]
        multiplier = self.momentum_capital / TOTAL_POINTS
        idx = 0
        for ptype, pv, qty in mapping:
            for _ in range(qty):
                piece = {
                    "id": f"{ptype}_{idx}_{uuid.uuid4().hex[:6]}",
                    "type": ptype,
                    "PV": pv,
                    "value": pv * multiplier,
                    "assigned": False
                }
                self.pieces.append(piece)
                idx += 1

    def summary(self):
        s = {}
        for p in self.pieces:
            s.setdefault(p["type"], []).append(p)
        out = {k: {"count": len(v), "assigned": sum(1 for x in v if x["assigned"])} for k, v in s.items()}
        return out

    def get_best_piece_for_rank(self, rank):
        unassigned = [p for p in self.pieces if not p["assigned"]]
        if not unassigned:
            return None
        best = sorted(unassigned, key=lambda x: -x["PV"])[0]
        return best

    def get_tactical_piece(self):
        unassigned = [p for p in self.pieces if not p["assigned"]]
        if not unassigned:
            return None
        smallest = sorted(unassigned, key=lambda x: x["PV"])[0]
        return smallest

    def assign_piece(self, piece_id):
        for p in self.pieces:
            if p["id"] == piece_id:
                p["assigned"] = True
                return True
        return False

    def recycle_piece(self, piece_id, returned_value):
        for p in self.pieces:
            if p["id"] == piece_id:
                p["assigned"] = False
                return True
        return False

class TradeBook:
    def __init__(self):
        self.trades = []

    def record_trade(self, trade_dict):
        self.trades.append(trade_dict)

    def to_frame(self):
        return pd.DataFrame(self.trades)

    def summary(self):
        df = self.to_frame()
        if df.empty:
            return "No trades recorded"
        buys = df[df["action"]=="BUY"] if "action" in df.columns else df
        sells = df[df["action"]=="SELL"] if "action" in df.columns else df
        realized = sells["value"].sum() - buys["value"].sum()
        ntrades = len(sells)
        return {
            "n_trades": int(ntrades),
            "realized_P&L": float(realized),
            "buys": int(len(buys)),
            "sells": int(len(sells))
        }

# ---------------------------
# Data download helper
# ---------------------------

def download_data(tickers, start=None, end=None):
    """
    Downloads adjusted close prices using yfinance for the given tickers and date range.
    Returns DataFrame indexed by date with columns = tickers.
    """
    df = yf.download(tickers, start=start, end=end, progress=False, auto_adjust=False)
    if df.empty:
        raise RuntimeError("yfinance returned no data. Check internet, tickers, or date range.")
    if ("Adj Close" in df.columns):
        price = df["Adj Close"].copy()
    else:
        price = df["Close"].copy()
    # Ensure columns order matches requested tickers
    price = price.reindex(columns=tickers)
    return price

# ---------------------------
# Backtester (integrated)
# ---------------------------

def run_backtest(cfg):
    tickers = cfg["tickers"]
    total_capital = float(cfg["total_capital"])
    risk_level = cfg["risk_level"]
    ma_period = int(cfg["ma_period"])
    reclaim_window = int(cfg["reclaim_window_days"])
    max_positions = int(cfg["max_positions"])

    # Risk allocation
    risk_map = {"High": 0.5, "Moderate": 0.3, "Low": 0.1}
    momentum_capital = total_capital * risk_map.get(risk_level, 0.3)
    king_cash = total_capital - momentum_capital

    piece_inventory = PieceInventory(momentum_capital)
    tradebook = TradeBook()

    # Data window
    if cfg["start_date"] is None:
        start = (pd.Timestamp.today() - pd.DateOffset(years=2)).strftime("%Y-%m-%d")
    else:
        start = cfg["start_date"]
    end = cfg["end_date"]

    price_panel = download_data(tickers, start, end)
    price_panel = price_panel.dropna(how='all')
    price_panel = price_panel.ffill().dropna(axis=1, how="any")
    dates = price_panel.index

    if len(dates) < ma_period + 2:
        raise RuntimeError("Not enough data to compute MA with the selected period. Try shorter MA or a longer history.")

    # Compute SOS frame
    sos_df = compute_sos_frame(price_panel, ma_period=ma_period)

    positions = {}  # ticker -> position dict

    for i in tqdm(range(ma_period, len(dates)-1), desc="Backtest days"):
        today = dates[i]
        tomorrow = dates[i+1]
        day_prices = price_panel.loc[today]
        next_prices = price_panel.loc[tomorrow]

        sos_today = sos_df.loc[today]

        # 1) Check existing positions for stop-loss/retreats
        to_close = []
        for ticker, pos in list(positions.items()):
            price = day_prices.get(ticker, np.nan)
            ma = sos_today.get((ticker, "MA"), np.nan)
            if pd.isna(price) or pd.isna(ma):
                continue
            was_initiated_on = pos["initiated_on_square"]
            current_square = "white" if price > ma else "black"

            if pos.get("tactical_black", False):
                days_since = (pd.Timestamp(today) - pd.Timestamp(pos["opened_date"])).days
                if current_square == "white":
                    pos["tactical_reclaimed"] = True
                elif days_since >= reclaim_window and not pos.get("tactical_reclaimed", False):
                    to_close.append((ticker, "tactical_reclaim_failed"))
            else:
                if was_initiated_on == "white" and current_square == "black":
                    to_close.append((ticker, "black_flip_stoploss"))

        # Execute closes at next_prices
        for ticker, reason in to_close:
            if ticker not in positions:
                continue
            exec_price = next_prices.get(ticker, np.nan)
            if pd.isna(exec_price):
                continue
            pos = positions.pop(ticker)
            tradebook.record_trade({
                "ticker": ticker,
                "action": "SELL",
                "price": float(exec_price),
                "shares": pos["shares"],
                "value": float(exec_price*pos["shares"]),
                "opened_date": pos["opened_date"].strftime("%Y-%m-%d") if hasattr(pos["opened_date"], "strftime") else str(pos["opened_date"]),
                "closed_date": pd.Timestamp(tomorrow).strftime("%Y-%m-%d"),
                "reason": reason,
                "initiated_on_square": pos["initiated_on_square"],
                "tactical": pos.get("tactical_black", False)
            })
            piece_inventory.recycle_piece(pos["piece_id"], float(exec_price*pos["shares"]))

        # 2) Deploy new pieces
        available_slots = max_positions - len(positions)
        if available_slots > 0:
            cand = []
            for ticker in tickers:
                if ticker in positions:
                    continue
                price = day_prices.get(ticker, np.nan)
                ma = sos_today.get((ticker, "MA"), np.nan)
                sos_val = sos_today.get((ticker, "SOS"), np.nan)
                if pd.isna(price) or pd.isna(ma) or pd.isna(sos_val):
                    continue
                square = "white" if price > ma else "black"
                cand.append((float(sos_val), ticker, square))
            if cand:
                cand_sorted = sorted(cand, key=lambda x: (-x[0], x[1]))
                for sos_val, ticker, square in cand_sorted:
                    if available_slots <= 0:
                        break
                    if square == "white":
                        rank, file = map_sos_to_tile(sos_val)
                        piece = piece_inventory.get_best_piece_for_rank(rank)
                        if piece is None:
                            continue
                        entry_price = next_prices.get(ticker, np.nan)
                        if pd.isna(entry_price) or entry_price <= 0:
                            continue
                        shares = int(piece["value"] // entry_price)
                        if shares <= 0:
                            continue
                        positions[ticker] = {
                            "shares": shares,
                            "avg_entry": float(entry_price),
                            "opened_date": today,
                            "piece_id": piece["id"],
                            "piece_type": piece["type"],
                            "initiated_on_square": "white",
                            "tactical_black": False
                        }
                        piece_inventory.assign_piece(piece["id"])
                        tradebook.record_trade({
                            "ticker": ticker,
                            "action": "BUY",
                            "price": float(entry_price),
                            "shares": shares,
                            "value": float(entry_price*shares),
                            "opened_date": pd.Timestamp(tomorrow).strftime("%Y-%m-%d"),
                            "closed_date": "",
                            "reason": "deploy_on_white",
                            "initiated_on_square": "white",
                            "tactical": False
                        })
                        available_slots -= 1

                    elif square == "black":
                        tactical_piece = piece_inventory.get_tactical_piece()
                        if tactical_piece is None:
                            continue
                        entry_price = next_prices.get(ticker, np.nan)
                        if pd.isna(entry_price) or entry_price <= 0:
                            continue
                        shares = int(tactical_piece["value"] // entry_price)
                        if shares <= 0:
                            continue
                        positions[ticker] = {
                            "shares": shares,
                            "avg_entry": float(entry_price),
                            "opened_date": today,
                            "piece_id": tactical_piece["id"],
                            "piece_type": tactical_piece["type"],
                            "initiated_on_square": "black",
                            "tactical_black": True,
                            "tactical_reclaimed": False
                        }
                        piece_inventory.assign_piece(tactical_piece["id"])
                        tradebook.record_trade({
                            "ticker": ticker,
                            "action": "BUY",
                            "price": float(entry_price),
                            "shares": shares,
                            "value": float(entry_price*shares),
                            "opened_date": pd.Timestamp(tomorrow).strftime("%Y-%m-%d"),
                            "closed_date": "",
                            "reason": "tactical_black_entry",
                            "initiated_on_square": "black",
                            "tactical": True
                        })
                        available_slots -= 1

    # Close any remaining positions at last price
    last_date = dates[-1]
    last_prices = price_panel.loc[last_date]
    for ticker, pos in list(positions.items()):
        exec_price = last_prices.get(ticker, np.nan)
        if pd.isna(exec_price):
            continue
        tradebook.record_trade({
            "ticker": ticker,
            "action": "SELL",
            "price": float(exec_price),
            "shares": pos["shares"],
            "value": float(exec_price*pos["shares"]),
            "opened_date": pos["opened_date"].strftime("%Y-%m-%d") if hasattr(pos["opened_date"], "strftime") else str(pos["opened_date"]),
            "closed_date": pd.Timestamp(last_date).strftime("%Y-%m-%d"),
            "reason": "end_of_sim",
            "initiated_on_square": pos["initiated_on_square"],
            "tactical": pos.get("tactical_black", False)
        })
        piece_inventory.recycle_piece(pos["piece_id"], float(exec_price*pos["shares"]))
        positions.pop(ticker, None)

    trades_df = tradebook.to_frame()
    trades_df.to_csv("trades.csv", index=False)
    print("Trades written to trades.csv")
    print("Piece inventory final state:")
    print(json.dumps(piece_inventory.summary(), indent=2))
    print("Trade summary:")
    print(tradebook.summary())

# ---------------------------
# CLI & helpers
# ---------------------------

def load_config(path):
    with open(path, "r") as f:
        cfg = json.load(f)
    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)
    return cfg

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=False, default=None, help="Optional JSON config file")
    p.add_argument("--tickers", nargs="+", help="List of tickers to override config")
    p.add_argument("--capital", type=float, help="Total capital override")
    p.add_argument("--risk", choices=["High", "Moderate", "Low"], help="Risk level override")
    p.add_argument("--start", help="Start date (YYYY-MM-DD)")
    p.add_argument("--end", help="End date (YYYY-MM-DD)")
    return p.parse_args()

def main():
    args = parse_args()
    cfg = DEFAULT_CONFIG.copy()
    if args.config:
        if not os.path.exists(args.config):
            raise FileNotFoundError(f"Config {args.config} not found.")
        cfg = load_config(args.config)
    if args.tickers:
        cfg["tickers"] = args.tickers
    if args.capital:
        cfg["total_capital"] = args.capital
    if args.risk:
        cfg["risk_level"] = args.risk
    if args.start:
        cfg["start_date"] = args.start
    if args.end:
        cfg["end_date"] = args.end

    print("Running backtest with config:")
    print(json.dumps(cfg, indent=2))
    run_backtest(cfg)

if __name__ == "__main__":
    main()
