#!/usr/bin/env python3
"""
Chess Framework - Usage Examples
Practical code examples for common tasks
"""

from chess_framework import (
    ChessFrameworkTrader,
    RiskLevel,
    SOSScorer,
    PieceInventory,
    GamePhase,
)
from chess_cli import InteractiveBoardSimulation
import pandas as pd


# ============================================================================
# EXAMPLE 1: Basic Setup
# ============================================================================

def example_1_basic_setup():
    """Initialize a trader with default settings."""
    print("EXAMPLE 1: Basic Setup\n")

    trader = ChessFrameworkTrader(
        tickers=["AAPL", "MSFT", "GOOGL"],
        total_capital=100000,
        risk_level=RiskLevel.MODERATE,
        ma_period=50,
    )

    print(f"✅ Trader created")
    print(f"   Capital: ${trader.total_capital:,.0f}")
    print(f"   Momentum: ${trader.momentum_capital:,.0f}")
    print(f"   Reserve: ${trader.king_cash:,.0f}")


# ============================================================================
# EXAMPLE 2: Piece Inventory
# ============================================================================

def example_2_piece_inventory():
    """Explore piece inventory and valuations."""
    print("\n\nEXAMPLE 2: Piece Inventory\n")

    inventory = PieceInventory(30000)  # $30k momentum capital
    summary = inventory.summary()

    print("Piece Summary:")
    for ptype, info in summary.items():
        pct_deployed = (info["assigned"] / info["count"]) * 100
        print(
            f"  {ptype:8s}: {info['count']} pieces, "
            f"{info['assigned']} deployed ({pct_deployed:.0f}%), "
            f"${info['total_value']:,.0f} total"
        )

    # Get specific pieces
    queen = inventory.get_best_piece_for_rank(8)
    print(f"\n✅ Best piece for Rank 8: {queen.piece_type.name} (PV={queen.point_value})")

    pawn = inventory.get_tactical_piece()
    print(f"✅ Tactical piece for Black: {pawn.piece_type.name} (PV={pawn.point_value})")


# ============================================================================
# EXAMPLE 3: Load Market Data
# ============================================================================

def example_3_load_data():
    """Load and examine market data."""
    print("\n\nEXAMPLE 3: Load Market Data\n")

    trader = ChessFrameworkTrader(
        tickers=["AAPL", "MSFT", "GOOGL"],
        total_capital=50000,
        risk_level=RiskLevel.MODERATE,
    )

    print("📥 Loading 2023 data...")
    trader.load_market_data("2023-01-01", "2023-12-31")

    print(f"✅ Loaded {len(trader.price_data)} trading days")
    print(f"   Date range: {trader.price_data.index[0].date()} to {trader.price_data.index[-1].date()}")
    print(f"   Tickers: {trader.tickers}")

    # Show sample data
    print("\nFirst 5 days (sample):")
    print(trader.price_data.head())


# ============================================================================
# EXAMPLE 4: Get Board State
# ============================================================================

def example_4_board_state():
    """Get and analyze board state at a specific date."""
    print("\n\nEXAMPLE 4: Get Board State\n")

    trader = ChessFrameworkTrader(
        tickers=["AAPL", "MSFT", "GOOGL"],
        total_capital=100000,
        risk_level=RiskLevel.MODERATE,
    )

    trader.load_market_data("2023-06-01", "2023-08-31")

    # Get state at middle of data
    mid_idx = len(trader.price_data) // 2
    state = trader.get_current_board_state(mid_idx)

    print(f"📅 Board State: {state['date']}")
    print("\nStock Positions:")
    print(f"{'Ticker':<10} {'Position':<10} {'Square':<8} {'SOS':<8}")
    print("-" * 40)

    for ticker, tile in state["tiles"].items():
        print(
            f"{ticker:<10} {tile['position']:<10} "
            f"{tile['square']:<8} {tile['sos']:.3f}"
        )


# ============================================================================
# EXAMPLE 5: Get Move Suggestions
# ============================================================================

def example_5_suggestions():
    """Get AI-powered move suggestions."""
    print("\n\nEXAMPLE 5: Move Suggestions\n")

    trader = ChessFrameworkTrader(
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN"],
        total_capital=100000,
        risk_level=RiskLevel.HIGH,
    )

    trader.load_market_data("2023-01-01", "2023-12-31")

    # Get state at day 100 (after MA period)
    state = trader.get_current_board_state(100)
    suggestions = trader.get_suggestions()

    print("💡 Top Move Suggestions:")
    print("-" * 80)

    if suggestions:
        for i, sugg in enumerate(suggestions[:3], 1):
            print(f"\n{i}. {sugg['action']}")
            print(f"   Ticker: {sugg['ticker']}")
            print(f"   Priority: {sugg['priority_score']:.1f}")
            print(f"   Reason: {sugg['reason']}")
    else:
        print("No suggestions at this time")


# ============================================================================
# EXAMPLE 6: Check Piece Rules
# ============================================================================

def example_6_rules():
    """Demonstrate rule checking."""
    print("\n\nEXAMPLE 6: Rule Enforcement\n")

    trader = ChessFrameworkTrader(
        tickers=["AAPL", "MSFT", "GOOGL"],
        total_capital=50000,
        risk_level=RiskLevel.MODERATE,
    )

    trader.load_market_data("2023-01-01", "2023-12-31")
    state = trader.get_current_board_state(100)

    rules = trader.rules_engine

    # Get a tile and piece
    if state["tiles"]:
        ticker = list(state["tiles"].keys())[0]
        tile = trader.board.get_tile(ticker)
        piece = trader.inventory.get_best_piece_for_rank(tile.rank)

        print(f"Testing rules for {ticker} at {tile.position} ({tile.square_color.value})")
        print()

        # Test White square deployment
        can_deploy, reason = rules.can_deploy_on_white(tile, piece)
        print(f"✅ White deployment: {reason}")

        # Test retreat condition
        retreat_needed, reason = rules.check_retreat_required(piece, tile)
        print(f"✅ Retreat required: {retreat_needed} ({reason or 'Safe'})")

        # Test scaling opportunity
        scale = rules.check_scaling_opportunity(piece, tile)
        print(f"✅ Scaling opportunity: {scale or 'None'}")


# ============================================================================
# EXAMPLE 7: SOS Scoring Details
# ============================================================================

def example_7_sos_scoring():
    """Detailed SOS scoring explanation."""
    print("\n\nEXAMPLE 7: SOS Scoring Details\n")

    # Create trader and load data
    trader = ChessFrameworkTrader(
        tickers=["AAPL", "MSFT", "GOOGL"],
        total_capital=50000,
        risk_level=RiskLevel.MODERATE,
    )

    trader.load_market_data("2023-01-01", "2023-12-31")

    # Get SOS data
    if trader.sos_data is not None:
        date_idx = 100
        date = trader.price_data.index[date_idx]

        print(f"SOS Components at {date.date()}:")
        print("-" * 60)
        print(f"{'Ticker':<10} {'MOM':<10} {'VOL':<10} {'SOS':<10} {'Rank':<6}")
        print("-" * 60)

        for ticker in trader.tickers:
            mom = trader.sos_data.loc[date, (ticker, "MOM")]
            vol = trader.sos_data.loc[date, (ticker, "VOL")]
            sos = trader.sos_data.loc[date, (ticker, "SOS")]

            if not pd.isna(sos):
                rank = SOSScorer.sos_to_rank(sos)
                print(f"{ticker:<10} {mom:<10.3f} {vol:<10.3f} {sos:<10.3f} {rank:<6}")

        print("-" * 60)
        print("\nFormula: SOS = 0.6 × Momentum + 0.25 × Volatility + 0.15 × Liquidity")
        print("Rank: 1 (safe) to 8 (risky)")


# ============================================================================
# EXAMPLE 8: Interactive Simulation
# ============================================================================

def example_8_interactive():
    """Start interactive simulation."""
    print("\n\nEXAMPLE 8: Interactive Mode\n")

    trader = ChessFrameworkTrader(
        tickers=["AAPL", "MSFT", "GOOGL"],
        total_capital=50000,
        risk_level=RiskLevel.MODERATE,
    )

    print("Starting interactive simulation...")
    print("Commands: status, board, suggest, deploy, retreat, next, quit")
    print()

    sim = InteractiveBoardSimulation(trader)
    # Uncomment to run interactive mode (requires user input):
    # sim.interactive_mode()

    print("✅ Ready for interactive trading")


# ============================================================================
# EXAMPLE 9: Run Backtest
# ============================================================================

def example_9_backtest():
    """Run a simple backtest."""
    print("\n\nEXAMPLE 9: Backtesting\n")

    trader = ChessFrameworkTrader(
        tickers=["AAPL", "MSFT", "GOOGL"],
        total_capital=50000,
        risk_level=RiskLevel.MODERATE,
        ma_period=50,
    )

    print("Starting backtest for 2023...")
    sim = InteractiveBoardSimulation(trader)

    # Uncomment to run full backtest (may take a few seconds):
    # sim.run_backtest("2023-01-01", "2023-12-31")

    print("✅ Backtest ready to run")


# ============================================================================
# EXAMPLE 10: Custom Configuration
# ============================================================================

def example_10_custom_config():
    """Create trader with custom configuration."""
    print("\n\nEXAMPLE 10: Custom Configuration\n")

    # High-risk aggressive trader
    aggressive_trader = ChessFrameworkTrader(
        tickers=["NVDA", "TSLA", "AMD", "MSTR", "COIN"],
        total_capital=500000,
        risk_level=RiskLevel.HIGH,  # 50% momentum
        ma_period=20,  # Fast (sensitive)
        max_positions=8,
    )

    print("⚡ Aggressive Trader:")
    print(f"   Risk: HIGH (50% momentum)")
    print(f"   MA Period: 20 days (responsive)")
    print(f"   Max Positions: 8")
    print(f"   Momentum Capital: ${aggressive_trader.momentum_capital:,.0f}")
    print()

    # Conservative low-risk trader
    conservative_trader = ChessFrameworkTrader(
        tickers=["JNJ", "PG", "KO", "MCD", "WMT"],
        total_capital=100000,
        risk_level=RiskLevel.LOW,  # 10% momentum
        ma_period=200,  # Slow (smoothed)
        max_positions=2,
    )

    print("🛡️ Conservative Trader:")
    print(f"   Risk: LOW (10% momentum)")
    print(f"   MA Period: 200 days (stable)")
    print(f"   Max Positions: 2")
    print(f"   Momentum Capital: ${conservative_trader.momentum_capital:,.0f}")


# ============================================================================
# Main
# ============================================================================

def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("CHESS FRAMEWORK - USAGE EXAMPLES")
    print("="*80)

    example_1_basic_setup()
    example_2_piece_inventory()
    example_3_load_data()
    example_4_board_state()
    example_5_suggestions()
    example_6_rules()
    example_7_sos_scoring()
    example_8_interactive()
    example_9_backtest()
    example_10_custom_config()

    print("\n" + "="*80)
    print("✅ ALL EXAMPLES COMPLETE")
    print("="*80)
    print("\n📚 Next: Check QUICK_REFERENCE.md or FRAMEWORK_DOCUMENTATION.md")


if __name__ == "__main__":
    main()
