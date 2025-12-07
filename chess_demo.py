#!/usr/bin/env python3
"""
Chess Framework Trading System - Comprehensive Example & Demo
Demonstrates all features: setup, SOS scoring, board state, suggestions, and backtesting.
"""

from chess_framework import (
    ChessFrameworkTrader,
    RiskLevel,
    SOSScorer,
    GamePhase,
)
from chess_cli import InteractiveBoardSimulation
import pandas as pd


def demo_basic_setup():
    """Demonstrate basic system setup."""
    print("\n" + "="*80)
    print("DEMO 1: BASIC SETUP")
    print("="*80)

    # Create trader
    trader = ChessFrameworkTrader(
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
        total_capital=100000,
        risk_level=RiskLevel.MODERATE,  # 30% momentum capital = $30,000
        ma_period=50,
        max_positions=5,
    )

    # Print summary
    trader.print_summary()

    print("📝 Configuration Summary:")
    print(f"   Stock Universe: {trader.tickers}")
    print(f"   Total Capital: ${trader.total_capital:,.2f}")
    print(f"   Momentum Capital (Pieces): ${trader.momentum_capital:,.2f}")
    print(f"   King's Cash (Reserve): ${trader.king_cash:,.2f}")
    print(f"   Risk Level: {trader.risk_level.label} ({trader.risk_level.allocation*100:.0f}%)")
    print(f"   MA Period: {trader.ma_period} days")
    print(f"   Max Positions: {trader.max_positions}")

    return trader


def demo_piece_inventory(trader):
    """Demonstrate piece inventory and valuations."""
    print("\n" + "="*80)
    print("DEMO 2: PIECE INVENTORY & VALUATIONS")
    print("="*80)

    inventory = trader.inventory
    summary = inventory.summary()

    print("\n📊 Piece Breakdown (Total PV: 39)")
    print("-" * 80)
    print(f"{'Type':<12} {'Count':<8} {'PV Each':<10} {'Total Value':<15} {'Assigned':<10}")
    print("-" * 80)

    piece_info = {
        "QUEEN": (1, 9),
        "ROOK": (2, 5),
        "BISHOP": (2, 3),
        "KNIGHT": (2, 3),
        "PAWN": (8, 1),
    }

    for ptype, (qty, pv) in piece_info.items():
        info = summary.get(ptype, {"count": 0, "total_value": 0.0, "assigned": 0})
        print(
            f"{ptype:<12} {qty:<8} {pv:<10} ${info['total_value']:<14,.2f} "
            f"{info['assigned']:<10}"
        )

    print("-" * 80)
    print(f"{'TOTAL':<12} 15 PV{'':<8} 39 PV{'':<6} ${trader.momentum_capital:<14,.2f}")
    print()
    print("🎯 Strategic Roles:")
    print("   - QUEEN (9 PV): Decisive strike - largest position on high-confidence plays")
    print("   - ROOKS (5 PV): Core control - main momentum positions")
    print("   - BISHOPS (3 PV): Thematic view - quality plays")
    print("   - KNIGHTS (3 PV): Tactical raids - mean reversion on Black squares")
    print("   - PAWNS (1 PV): Development/test - small position testing")


def demo_sos_scoring(trader):
    """Demonstrate SOS scoring and board positioning."""
    print("\n" + "="*80)
    print("DEMO 3: SOS SCORING & BOARD POSITIONING")
    print("="*80)

    # Load data
    print("\n📥 Loading market data...")
    trader.load_market_data("2023-01-01", "2023-12-31")

    if trader.price_data is None:
        print("Error: Could not load data")
        return

    print(f"✅ Loaded {len(trader.price_data)} trading days\n")

    # Show SOS scores at a specific date
    date_idx = 100
    date = trader.price_data.index[date_idx]
    state = trader.get_current_board_state(date_idx)

    print(f"📅 Board State at {state['date']}")
    print("-" * 100)
    print(f"{'Ticker':<10} {'Position':<10} {'Square':<8} {'SOS':<8} "
          f"{'Price':<12} {'MA':<12} {'Change':<8}")
    print("-" * 100)

    for ticker, tile in state["tiles"].items():
        price = tile["price"]
        ma = tile["ma"]
        change_pct = ((price - ma) / ma) * 100 if ma > 0 else 0
        print(
            f"{ticker:<10} {tile['position']:<10} {tile['square']:<8} "
            f"{tile['sos']:<8.3f} ${price:<11.2f} ${ma:<11.2f} {change_pct:>+7.1f}%"
        )

    print("-" * 100)
    print("\n🧮 SOS Formula: 60% Momentum + 25% Volatility + 15% Liquidity")
    print("   Rank (1-8): Risk level (1=lowest, 8=highest)")
    print("   File (A-H): Quality (C-F=center/high, A-B/G-H=flanks/lower)")


def demo_move_suggestions(trader):
    """Demonstrate move suggestion engine."""
    print("\n" + "="*80)
    print("DEMO 4: MOVE SUGGESTION ENGINE")
    print("="*80)

    if trader.price_data is None:
        print("⚠️  Need to load data first (run demo_sos_scoring)")
        return

    suggestions = trader.get_suggestions()

    print("\n💡 Strategic Recommendations:")
    print("-" * 100)

    if not suggestions:
        print("No suggestions at this time.")
    else:
        for i, sugg in enumerate(suggestions, 1):
            action = sugg.get("action", "UNKNOWN")
            ticker = sugg.get("ticker", "???")
            reason = sugg.get("reason", "")
            priority = sugg.get("priority_score", 0)

            print(f"\n{i}. [{priority:>6.1f}] {action}")
            print(f"   Ticker: {ticker}")
            print(f"   Reason: {reason}")

            # Add strategic context
            if action == "DEPLOYMENT":
                piece = sugg.get("piece", "")
                sos = sugg.get("sos_score", 0)
                print(f"   Deploy: {piece} piece")
                print(f"   SOS Score: {sos:.3f} (quality indicator)")
            elif action == "RETREAT":
                gain_loss = sugg.get("gain_loss_pct", 0)
                print(f"   Gain/Loss: {gain_loss:>+.1f}%")
                print(f"   Reason: Stop-loss protection")
            elif action == "CAPTURE":
                gain_loss = sugg.get("gain_loss_pct", 0)
                print(f"   Gain/Loss: {gain_loss:>+.1f}%")
                print(f"   Reason: Profit taking on endgame position")

    print("-" * 100)


def demo_board_visualization(trader):
    """Demonstrate board visualization."""
    print("\n" + "="*80)
    print("DEMO 5: BOARD VISUALIZATION")
    print("="*80)

    if trader.price_data is None:
        print("⚠️  Need to load data first (run demo_sos_scoring)")
        return

    date_idx = len(trader.price_data) // 2
    state = trader.get_current_board_state(date_idx)

    print(f"\n📋 ASCII Chess Board (Date: {state['date']})")
    print("   Legend: W = White square (BUY zone), B = Black square (SELL zone)")
    print()

    # Build board
    board = [["." for _ in range(8)] for _ in range(8)]

    for ticker, tile in state["tiles"].items():
        parts = tile["position"]
        if len(parts) == 2:
            file_char = parts[0]
            rank = int(parts[1])
            rank_idx = 8 - rank
            file_idx = ord(file_char) - ord('A')
            marker = "W" if tile["square"] == "white" else "B"
            if 0 <= rank_idx < 8 and 0 <= file_idx < 8:
                board[rank_idx][file_idx] = marker

    print("     A B C D E F G H")
    for i, row in enumerate(board):
        rank = 8 - i
        print(f"  {rank} {' '.join(row)}")
    print()

    print("📊 Game Phase: MIDDLEGAME (based on positions deployed)")
    print("   Transition rules:")
    print("   - OPENING → MIDDLEGAME: When ≥4 pieces deployed & King protected")
    print("   - MIDDLEGAME → ENDGAME: When >80% capital deployed")


def demo_rules_enforcement(trader):
    """Demonstrate trading rules enforcement."""
    print("\n" + "="*80)
    print("DEMO 6: TRADING RULES ENFORCEMENT")
    print("="*80)

    rules = trader.rules_engine

    print("\n🏛️ Core Trading Rules:\n")

    print("Rule R.1-R.5: SOS Scoring & VIX Adjustment")
    print("   - SOS range: 0.0 (worst) to 1.0 (best)")
    print("   - VIX > 20: Increases volatility weight, reduces risk tolerance")
    print("   - VIX < 20: Increases momentum weight, higher risk tolerance")

    print("\nRule R.6: White Square Deployment")
    print("   - ✅ ALLOWED: Any piece on White square (price > MA)")
    print("   - Recommended: Higher-value pieces on high-rank White squares")

    print("\nRule R.7: Black Square Mandatory Retreat")
    print("   - Position initiated on White → flips to Black → FORCED SELL")
    print("   - Prevents catastrophic losses from trend reversals")

    print("\nRule R.12: Tactical Black Entry (Pawn/Knight only)")
    print("   - Only small pieces (Pawn/Knight) can enter Black squares")
    print("   - Must reclaim White within 3 days or automatic retreat")
    print("   - Mean reversion play with strict risk management")

    print("\nRule R.14: Piece Advancement (Scaling)")
    print("   - Pawn on high rank 5+ → Consider promoting to Rook")
    print("   - Scale winners: Increase position on confirmed trends")
    print("   - Align capital with confidence level")

    print("\nRule R.15: Endgame Profit Taking (Rank 7-8)")
    print("   - High-rank positions: Take profits")
    print("   - Convert paper gains to cash")
    print("   - Secure capital preservation")

    print("\nRule R.8: King's Safety (Capital Preservation)")
    print("   - Never deploy 100% of capital")
    print("   - Maintain emergency reserves")
    print("   - Default: 30-50% in reserve, 50-70% in pieces")


def demo_backtest_summary(trader):
    """Demonstrate backtesting capability."""
    print("\n" + "="*80)
    print("DEMO 7: BACKTESTING FRAMEWORK")
    print("="*80)

    print("\n📊 Backtest Parameters:")
    print(f"   Date Range: 2023-01-01 to 2023-12-31")
    print(f"   Tickers: {trader.tickers}")
    print(f"   Capital: ${trader.total_capital:,.0f}")
    print(f"   Starting Momentum Capital: ${trader.momentum_capital:,.0f}")

    print("\n🎯 Backtest Output Metrics (when run):")
    print("   - Number of trades executed")
    print("   - Win rate (% profitable trades)")
    print("   - Total realized P&L")
    print("   - Max drawdown")
    print("   - Sharpe ratio (risk-adjusted return)")
    print("   - Final portfolio value")
    print("   - Trade journal (entry/exit reasoning)")

    print("\n💡 Running full backtest...")
    sim = InteractiveBoardSimulation(trader)
    sim.run_backtest("2023-01-01", "2023-12-31")


def main():
    """Run all demos."""
    print("\n" + "="*80)
    print("CHESS FRAMEWORK TRADING SYSTEM - COMPREHENSIVE DEMO")
    print("="*80)
    print("\nThis script demonstrates all major features of the chess trading framework.")
    print("Each demo builds on the previous one.\n")

    # Run demos
    trader = demo_basic_setup()
    input("\nPress Enter to continue to Demo 2...")

    demo_piece_inventory(trader)
    input("\nPress Enter to continue to Demo 3...")

    demo_sos_scoring(trader)
    input("\nPress Enter to continue to Demo 4...")

    demo_move_suggestions(trader)
    input("\nPress Enter to continue to Demo 5...")

    demo_board_visualization(trader)
    input("\nPress Enter to continue to Demo 6...")

    demo_rules_enforcement(trader)
    input("\nPress Enter to continue to Demo 7 (full backtest)...")

    print("\nRunning backtest... this may take a moment.")
    demo_backtest_summary(trader)

    print("\n" + "="*80)
    print("✅ DEMO COMPLETE")
    print("="*80)
    print("\n📚 Next Steps:")
    print("   1. Explore chess_cli.py for interactive mode")
    print("   2. Read FRAMEWORK_DOCUMENTATION.md for detailed rules")
    print("   3. Modify parameters and re-run examples")
    print("   4. Integrate real VIX data for enhanced SOS scoring")
    print("   5. Add live trading via broker API")


if __name__ == "__main__":
    main()
