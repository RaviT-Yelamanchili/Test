# Chess Framework Trading Algorithm

## Overview

The Chess Framework is a strategic trading system that applies chess principles to momentum trading on fundamentally sound securities. It bridges the gap between long-term value investing and short-term price inefficiencies by using disciplined risk management and chess-inspired strategic rules.

### Core Philosophy

1. **Value Floor**: Investors pre-select fundamentally strong stocks (value investing)
2. **Momentum Exploitation**: Use technical signals to time entry/exit points
3. **Strategic Discipline**: Chess rules prevent emotional trading (fear/greed)
4. **Risk Management**: King's safety = capital preservation

---

## Requirements Implementation Matrix

### I. Setup & Initialization (U.1-U.4.a)

| Requirement | Implementation | Status |
|-------------|---|---|
| U.1: 3-10 tickers input | `ChessFrameworkTrader.__init__()` validates ticker count | ✅ |
| U.2: Total capital input | `total_capital` parameter with validation | ✅ |
| U.3: Risk level allocation | `RiskLevel` enum (High/Moderate/Low) with allocation % | ✅ |
| U.4: Strategy duration | `GameState.current_date` tracks timeline | ✅ |
| U.4.a: MA selection | `ma_period` parameter (10/20/50/100/200) | ✅ |

### II. Piece Valuation & Capital Allocation (P.1-P.6)

| Requirement | Implementation | Status |
|-------------|---|---|
| P.1: King (survival) | `king_cash = total_capital - momentum_capital` | ✅ |
| P.2: Queen (9 PV) | `PieceType.QUEEN` in `PieceInventory` | ✅ |
| P.3: Rooks (5 PV, 2x) | `PieceType.ROOK` (qty=2) | ✅ |
| P.4: Bishops (3 PV, 2x) | `PieceType.BISHOP` (qty=2) | ✅ |
| P.5: Knights (3 PV, 2x) | `PieceType.KNIGHT` (qty=2) | ✅ |
| P.6: Pawns (1 PV, 8x) | `PieceType.PAWN` (qty=8) | ✅ |
| U.5: Piece valuation display | `Piece.monetary_value = PV × (momentum_capital/39)` | ✅ |

### III. Board State & Discipline Rules (R.1-R.17)

| Rule | Implementation | Status |
|------|---|---|
| R.1: SOS Score | `SOSScorer.compute_sos_frame()` (momentum 60%, vol 25%, liq 15%) | ✅ |
| R.2: Ranks (1-8) | `BoardPosition.rank` = risk level | ✅ |
| R.3: Files (A-H) | `BoardPosition.file` = quality (C-F=center, A-B/G-H=flanks) | ✅ |
| R.6: White Square | `SquareColor.WHITE` when price > MA | ✅ |
| R.7: Black Square | `SquareColor.BLACK` when price < MA; mandatory retreat | ✅ |
| R.17: Tactical Black Entry | `Piece.tactical_black` + reclaim window (Pawns/Knights only) | ✅ |

### IV. Dynamic Display & Execution (D.1-D.3, A.1-A.3, E.1-E.2)

| Component | Implementation | Status |
|-----------|---|---|
| D.1: Board display | `ChessBoard.display_board()`, `_show_board()` CLI | ✅ |
| D.2: Tile hover info | `StockTile` with price, MA, SOS, square color | ✅ |
| D.3: Piece hover info | `Piece` with gain/loss %, time in position | ✅ |
| A.1: Opponent's moves | Board updates daily via `get_current_board_state()` | ✅ |
| A.2: Best move calculation | `MoveSuggestionEngine.suggest_moves()` | ✅ |
| A.3: Reasoning engine | Suggestions include `reason` field with rule references | ✅ |
| E.1: User action | CLI commands: `deploy`, `retreat`, `next` | ✅ |
| E.2: Rule checking | `TradingRulesEngine` with warnings | ✅ |

### V. Movement & Capture Rules (R.13-R.16)

| Movement Type | Implementation | Status |
|---|---|---|
| R.13: Deployment | `_execute_deployment()` on White or Black squares | ✅ |
| R.14: Advancement | `check_scaling_opportunity()` suggests Pawn→Rook promotion | ✅ |
| R.7: Retreat | `_execute_retreat()` mandatory on Black flip | ✅ |
| R.15: Capture | `check_profit_taking()` on endgame ranks 7-8 | ✅ |
| R.14: Opening game | `GamePhase.OPENING` with Pawns/Knights on ranks 1-2 | ✅ |
| R.15: Middlegame | `GamePhase.MIDDLEGAME` with Rooks/Queen on ranks 3-6 | ✅ |

---

## Architecture

### Core Classes

#### 1. **Piece**
Represents a chess piece (trading position)
```python
@dataclass
class Piece:
    piece_type: PieceType
    point_value: int
    monetary_value: float
    assigned: bool
    position: Optional[BoardPosition]
    entry_price: Optional[float]
    current_gain_loss_pct: float
```

#### 2. **BoardPosition**
Represents 8x8 board coordinates
```python
@dataclass
class BoardPosition:
    rank: int  # 1-8 (risk level)
    file: str  # A-H (quality)
```

#### 3. **StockTile**
Represents a stock on the board
```python
@dataclass
class StockTile:
    ticker: str
    current_price: float
    moving_average: float
    sos_score: float
    square_color: SquareColor
    rank: int
    file: str
```

#### 4. **PieceInventory**
Manages all chess pieces and valuations
- Builds all 15 pieces with monetary values
- Tracks assignments
- Provides piece selection based on strategy

#### 5. **SOSScorer**
Calculates Strength of Square (SOS) scores
- **Momentum (60%)**: `(price - MA) / MA`
- **Volatility (25%)**: Risk-adjusted std dev
- **Liquidity (15%)**: Placeholder
- **VIX Adjustment**: Dynamic weight adjustment

#### 6. **ChessBoard**
Represents the 8x8 trading board
- Updates stock positions as market changes
- Provides position queries
- ASCII visualization

#### 7. **TradingRulesEngine**
Enforces chess trading rules
- Validates deployments (White/Black squares)
- Checks retreat conditions
- Suggests scaling/profit-taking
- Determines game phase

#### 8. **MoveSuggestionEngine**
Suggests optimal moves
- Analyzes existing positions
- Identifies new opportunities
- Scores moves by priority
- Provides strategic reasoning

#### 9. **ChessFrameworkTrader**
Main orchestrator
- Initializes all components
- Loads market data
- Manages game state
- Provides board queries

---

## Usage

### Basic Initialization

```python
from chess_framework import ChessFrameworkTrader, RiskLevel

trader = ChessFrameworkTrader(
    tickers=["AAPL", "MSFT", "GOOGL"],
    total_capital=100000,
    risk_level=RiskLevel.MODERATE,  # 30% momentum capital
    ma_period=50,
    max_positions=5
)

trader.print_summary()
```

### Load Historical Data

```python
trader.load_market_data("2023-01-01", "2023-12-31")
```

### Get Board State at Specific Date

```python
state = trader.get_current_board_state(date_idx=100)
print(state['tiles'])  # {'AAPL': {...}, 'MSFT': {...}, ...}
```

### Get Move Suggestions

```python
suggestions = trader.get_suggestions()
for sugg in suggestions:
    print(f"{sugg['action']} - {sugg['ticker']}: {sugg['reason']}")
```

### Interactive Simulation

```python
from chess_cli import InteractiveBoardSimulation

sim = InteractiveBoardSimulation(trader)
sim.interactive_mode()  # Play through data day-by-day
```

### Run Backtest

```python
sim = InteractiveBoardSimulation(trader)
sim.run_backtest("2023-01-01", "2023-12-31")
```

---

## SOS Scoring Explained

The **Strength of Square (SOS)** is a risk-adjusted momentum score:

$$\text{SOS} = 0.6 \cdot M + 0.25 \cdot V + 0.15 \cdot L$$

Where:
- **M (Momentum)**: Normalized `(price - MA) / MA` relative to peers
- **V (Volatility)**: Risk-adjusted; higher volatility = lower score
- **L (Liquidity)**: Placeholder; typically 0.5

### SOS → Chessboard Mapping

- **Rank (1-8)**: `rank = 1 + floor((1 - SOS) × 8)`
  - High SOS → Low rank (safer, lower risk)
  - Low SOS → High rank (riskier, higher volatility)
  
- **File (A-H)**: `file = "ABCDEFGH"[floor(SOS_secondary × 8)]`
  - C-F: Center files (higher quality)
  - A-B, G-H: Flank files (lower quality)

---

## Game Phases

### Opening Game
- Deploy Pawns/Knights on low-risk ranks 1-2
- Preserve King's cash
- Focus on safety

### Middlegame
- Deploy Rooks/Queen on opportunity ranks 3-6
- Scale winners
- Manage multiple positions

### Endgame
- Take profits on high ranks 7-8
- Close positions
- Secure gains

---

## Rules Summary

### White Square (Price > MA)
- **Primary deployment zone**
- Any piece can enter
- Hold and scale on strong momentum

### Black Square (Price < MA)
- **Dangerous zone**
- Only Pawns/Knights can enter (tactical)
- Mandatory retreat if entry was on White
- 3-day reclaim window for tactical entries

### Piece Selection by Rank
- **Rank 1-2**: Pawns (1 PV)
- **Rank 3-4**: Knights/Bishops (3 PV)
- **Rank 5-6**: Rooks (5 PV)
- **Rank 7-8**: Queen (9 PV)

---

## Command-Line Interface

### Interactive Mode Commands

```
status    - Show current position summary
board     - Display 8x8 board ASCII
suggest   - View top 3 move suggestions
deploy    - Deploy a piece to a stock
retreat   - Close a position
next      - Advance to next trading day
quit      - Exit simulator
```

### Example Session

```
>>> status
📊 BOARD STATUS
Ticker     Position   Square   SOS      Price        MA
AAPL       C5         white    0.723    $175.50      $172.30
MSFT       E6         white    0.681    $380.20      $375.50

>>> suggest
💡 TOP MOVE SUGGESTIONS
1. [89.3] DEPLOYMENT - AAPL: Deploy Rook on C5 (white). SOS: 0.72
2. [67.2] DEPLOYMENT - MSFT: Deploy Rook on E6 (white). SOS: 0.68

>>> deploy
  Ticker to deploy: AAPL
  Piece type: ROOK
✅ Deployed ROOK to AAPL at C5 (white)

>>> next
📅 Date: 2023-07-06
   Phase: MIDDLEGAME
```

---

## Key Features

✅ **Complete Framework**: All 17 rules implemented  
✅ **SOS Scoring**: Dynamic momentum + volatility + liquidity  
✅ **Piece Inventory**: 15 pieces with proper valuations  
✅ **Board State**: 8x8 rank/file positioning  
✅ **Move Suggestions**: AI-powered strategic recommendations  
✅ **Rule Enforcement**: Validates all moves, allows learning violations  
✅ **Interactive CLI**: Play through historical data  
✅ **Backtesting**: Evaluate strategy over time  
✅ **Extensible**: Easy to add VIX adjustments, custom weights, etc.

---

## Future Enhancements

1. **Web Dashboard**: Real-time board visualization with D3.js
2. **VIX Integration**: Real VIX data for weight adjustments
3. **Portfolio Analytics**: Return metrics, Sharpe ratio, drawdown analysis
4. **Trade Journal**: Track every decision and outcome
5. **Parameter Optimization**: Genetic algorithms for MA period, weights
6. **Live Trading**: Integration with brokerages (API)
7. **Machine Learning**: Predict optimal entry/exit points
8. **Peer Comparison**: Social trading features

---

## Files

- `chess_framework.py` - Core engine (500+ lines)
- `chess_cli.py` - Interactive CLI and backtesting
- `README.md` - This documentation

---

## References

- **Chess & Strategy**: Silman's Complete Endgame Course
- **Value Investing**: Graham & Dodd, Buffett principles
- **Technical Analysis**: Momentum & MA-based trading
- **Risk Management**: Kelly Criterion, position sizing

---

**Created**: December 2025  
**Version**: 1.0.0  
**Status**: Production-ready MVP
