"""
Interactive Chess Framework Trading CLI & Backtesting Engine
"""

import json
import uuid
from datetime import datetime
from typing import Optional
from chess_framework import (
    ChessFrameworkTrader,
    RiskLevel,
    PieceInventory,
    SquareColor,
    PieceType,
    Trade,
)
import pandas as pd
import numpy as np


class InteractiveBoardSimulation:
    """Interactive simulation and backtesting engine."""

    def __init__(self, trader: ChessFrameworkTrader):
        self.trader = trader
        self.trade_history = []

    def run_backtest(self, start_date: str, end_date: str):
        """Run full backtest through historical data."""
        print(f"\nStarting backtest from {start_date} to {end_date}...")
        self.trader.load_market_data(start_date, end_date)

        if self.trader.price_data is None or self.trader.sos_data is None:
            print("Error: Could not load market data")
            return

        dates = self.trader.price_data.index
        starting_idx = self.trader.ma_period  # Start after MA computation

        for date_idx in range(starting_idx, len(dates) - 1):
            date = dates[date_idx]
            self.trader.game_state.current_date = date

            # Update board state
            state = self.trader.get_current_board_state(date_idx)
            if not state["tiles"]:
                continue

            # Get suggestions and process
            suggestions = self.trader.get_suggestions()
            self._process_day(date, state, suggestions)

        self._print_backtest_results()

    def _process_day(self, date, board_state: dict, suggestions: list):
        """Process a single trading day."""
        # In a real system, this would execute suggested trades
        # For now, we just track the board state
        pass

    def _print_backtest_results(self):
        """Print backtest results."""
        print("\n" + "="*80)
        print("BACKTEST RESULTS")
        print("="*80)
        print(f"Start Capital: ${self.trader.total_capital:,.2f}")
        print(f"Trades Executed: {len(self.trade_history)}")
        if self.trade_history:
            realized_pl = sum(t.get("gain_loss", 0) for t in self.trade_history)
            print(f"Realized P&L: ${realized_pl:,.2f}")
        print("="*80 + "\n")

    def interactive_mode(self):
        """Run interactive trading simulator."""
        self.trader.load_market_data("2023-01-01", "2023-12-31")

        if self.trader.price_data is None:
            print("Error: Could not load market data")
            return

        dates = self.trader.price_data.index

        print("\n" + "="*80)
        print("CHESS FRAMEWORK - INTERACTIVE MODE")
        print("="*80)
        print("\nCommands: 'status', 'board', 'suggest', 'deploy', 'retreat', 'next', 'quit'")
        print("="*80 + "\n")

        date_idx = self.trader.ma_period
        max_idx = len(dates) - 1

        while date_idx < max_idx:
            current_date = dates[date_idx]
            self.trader.game_state.current_date = current_date

            # Update board
            state = self.trader.get_current_board_state(date_idx)
            if not state["tiles"]:
                date_idx += 1
                continue

            print(f"\n📅 Date: {state['date']}")
            print(f"   Phase: {self.trader.game_state.phase.value.upper()}")
            print(f"   King's Cash: ${self.trader.game_state.king_cash:,.2f}")
            print(f"   Positions Open: {self.trader.game_state.pieces_deployed}\n")

            user_input = input(">>> ").strip().lower()

            if user_input == "status":
                self._show_status(state)
            elif user_input == "board":
                self._show_board(state)
            elif user_input == "suggest":
                self._show_suggestions()
            elif user_input == "deploy":
                ticker = input("  Ticker to deploy: ").upper()
                piece_type = input("  Piece type (PAWN/KNIGHT/BISHOP/ROOK/QUEEN): ").upper()
                self._execute_deployment(ticker, piece_type, state)
            elif user_input == "retreat":
                ticker = input("  Ticker to retreat: ").upper()
                self._execute_retreat(ticker)
            elif user_input == "next":
                date_idx += 1
            elif user_input == "quit":
                break
            else:
                print("Unknown command")

    def _show_status(self, board_state: dict):
        """Show current position status."""
        print("\n📊 BOARD STATUS")
        print("-" * 80)
        print(f"{'Ticker':<10} {'Position':<10} {'Square':<8} {'SOS':<8} {'Price':<12} {'MA':<12}")
        print("-" * 80)
        for ticker, tile in board_state["tiles"].items():
            print(
                f"{ticker:<10} {tile['position']:<10} {tile['square']:<8} "
                f"{tile['sos']:<8.3f} ${tile['price']:<11.2f} ${tile['ma']:<11.2f}"
            )
        print("-" * 80)

    def _show_board(self, board_state: dict):
        """Show ASCII board representation."""
        board = [["." for _ in range(8)] for _ in range(8)]

        for ticker, tile in board_state["tiles"].items():
            parts = tile["position"].split("")
            if len(parts) == 2:
                file_char = parts[0]
                rank = int(parts[1])
                rank_idx = 8 - rank
                file_idx = ord(file_char) - ord('A')
                marker = "W" if tile["square"] == "white" else "B"
                if 0 <= rank_idx < 8 and 0 <= file_idx < 8:
                    board[rank_idx][file_idx] = marker

        print("\n   A B C D E F G H")
        for i, row in enumerate(board):
            rank = 8 - i
            print(f"{rank} {' '.join(row)}")
        print()

    def _show_suggestions(self):
        """Show move suggestions."""
        suggestions = self.trader.get_suggestions()
        if not suggestions:
            print("\nNo suggestions at this time.")
            return

        print("\n💡 TOP MOVE SUGGESTIONS")
        print("-" * 80)
        for i, sugg in enumerate(suggestions, 1):
            action = sugg.get("action", "UNKNOWN")
            ticker = sugg.get("ticker", "???")
            reason = sugg.get("reason", "")
            priority = sugg.get("priority_score", 0)
            print(f"{i}. [{priority:.1f}] {action} - {ticker}: {reason}")
        print("-" * 80)

    def _execute_deployment(self, ticker: str, piece_type: str, board_state: dict):
        """Execute a piece deployment."""
        if ticker not in board_state["tiles"]:
            print(f"Error: {ticker} not in current universe")
            return

        tile = board_state["tiles"][ticker]
        # Find piece
        piece = None
        for p in self.trader.inventory.pieces:
            if p.piece_type.name == piece_type and not p.assigned:
                piece = p
                break

        if not piece:
            print(f"Error: No unassigned {piece_type} available")
            return

        # Check rules
        can_deploy, reason = self.trader.rules_engine.can_deploy_on_white(
            self.trader.board.get_tile(ticker), piece
        )
        if not can_deploy:
            print(f"⚠️  {reason} (deploying anyway for learning)")

        # Execute deployment
        self.trader.inventory.assign_piece(piece.piece_id)
        self.trader.game_state.positions_open[ticker] = piece
        self.trader.game_state.pieces_deployed += 1

        print(f"✅ Deployed {piece_type} to {ticker} at {tile['position']} ({tile['square']})")

    def _execute_retreat(self, ticker: str):
        """Execute a retreat (close position)."""
        if ticker not in self.trader.game_state.positions_open:
            print(f"Error: No position in {ticker}")
            return

        piece = self.trader.game_state.positions_open.pop(ticker)
        self.trader.inventory.unassign_piece(piece.piece_id)
        self.trader.game_state.pieces_deployed -= 1

        print(f"✅ Retreated {piece.piece_type.name} from {ticker}")


def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("CHESS FRAMEWORK TRADING SYSTEM - SETUP")
    print("="*80)

    # Get user inputs
    print("\nStock Universe (3-10 tickers):")
    tickers_input = input("Enter tickers separated by space (default: AAPL MSFT GOOGL): ").strip()
    tickers = tickers_input.split() if tickers_input else ["AAPL", "MSFT", "GOOGL"]

    if not (3 <= len(tickers) <= 10):
        print("Error: Must provide 3-10 tickers")
        return

    print("\nTotal Capital:")
    capital_input = input("Enter amount in dollars (default: 100000): ").strip()
    total_capital = float(capital_input) if capital_input else 100000.0

    print("\nRisk Level:")
    print("  1. High (50% momentum capital)")
    print("  2. Moderate (30% momentum capital)")
    print("  3. Low (10% momentum capital)")
    risk_input = input("Select 1-3 (default: 2): ").strip()

    risk_map = {"1": RiskLevel.HIGH, "2": RiskLevel.MODERATE, "3": RiskLevel.LOW}
    risk_level = risk_map.get(risk_input, RiskLevel.MODERATE)

    print("\nMoving Average Period:")
    print("  Options: 10, 20, 50, 100, 200")
    ma_input = input("Enter period (default: 50): ").strip()
    ma_period = int(ma_input) if ma_input in ["10", "20", "50", "100", "200"] else 50

    print("\nSimulation Mode:")
    print("  1. Backtest (historical data)")
    print("  2. Interactive (play through data)")
    mode_input = input("Select 1-2 (default: 1): ").strip()

    # Initialize trader
    trader = ChessFrameworkTrader(
        tickers=tickers,
        total_capital=total_capital,
        risk_level=risk_level,
        ma_period=ma_period,
        max_positions=5,
    )

    trader.print_summary()

    # Run simulation
    sim = InteractiveBoardSimulation(trader)

    if mode_input == "2":
        sim.interactive_mode()
    else:
        sim.run_backtest("2023-01-01", "2023-12-31")


if __name__ == "__main__":
    main()
