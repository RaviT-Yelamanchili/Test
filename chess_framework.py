"""
Chess Framework Trading Algorithm

A strategic trading system that uses chess principles to manage momentum trades
on fundamentally sound securities selected by value investors.

Core Philosophy:
- Long-term value investing provides the safety floor
- Short-term momentum trades exploit pricing inefficiencies
- Chess discipline prevents psychological biases (fear/greed)
- Risk management is paramount (King's safety = capital preservation)
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
import yfinance as yf
from abc import ABC, abstractmethod


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class PieceType(Enum):
    """Chess piece types with point values and strategic roles."""
    KING = 0       # Capital preservation (not deployed)
    QUEEN = 9      # Decisive strike
    ROOK = 5       # Core control (2x)
    BISHOP = 3     # Thematic view (2x)
    KNIGHT = 3     # Tactical raid (2x)
    PAWN = 1       # Development/test (8x)


class SquareColor(Enum):
    """Board square colors determined by price vs MA."""
    WHITE = "white"   # Price > MA (BUY/HOLD zone)
    BLACK = "black"   # Price < MA (SELL/AVOID zone)


class GamePhase(Enum):
    """Strategic phases of the trading game."""
    OPENING = "opening"      # Deploy Pawns/Knights on low-risk ranks 1-2
    MIDDLEGAME = "middlegame"  # Execute and scale with Rooks/Queen
    ENDGAME = "endgame"      # Capture (take profits) on high ranks 7-8


class RiskLevel(Enum):
    """Risk allocation levels."""
    HIGH = ("High", 0.50)
    MODERATE = ("Moderate", 0.30)
    LOW = ("Low", 0.10)

    def __init__(self, label, allocation):
        self.label = label
        self.allocation = allocation


TOTAL_POINTS = 39  # Total point value across all pieces

PIECE_CONFIG = [
    (PieceType.QUEEN, 1),
    (PieceType.ROOK, 2),
    (PieceType.BISHOP, 2),
    (PieceType.KNIGHT, 2),
    (PieceType.PAWN, 8),
]


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Piece:
    """Represents a chess piece (trading position)."""
    piece_id: str
    piece_type: PieceType
    point_value: int
    monetary_value: float
    assigned: bool = False
    position: Optional['BoardPosition'] = None
    entry_date: Optional[datetime] = None
    entry_price: Optional[float] = None
    entry_square: Optional[SquareColor] = None
    current_price: Optional[float] = None
    current_gain_loss_pct: float = 0.0
    shares: int = 0
    tactical_black: bool = False  # For Pawns/Knights on Black squares
    tactical_reclaim_window: int = 0  # Days to reclaim White square

    def value_at_price(self, price: float) -> float:
        """Calculate unrealized value at given price."""
        if self.entry_price and self.shares > 0:
            return price * self.shares
        return 0.0

    def gain_loss(self, current_price: float) -> float:
        """Calculate unrealized gain/loss."""
        if self.entry_price and self.shares > 0:
            return (current_price - self.entry_price) * self.shares
        return 0.0

    def gain_loss_pct(self, current_price: float) -> float:
        """Calculate unrealized gain/loss percentage."""
        if self.entry_price and self.entry_price > 0:
            return ((current_price - self.entry_price) / self.entry_price) * 100
        return 0.0


@dataclass
class BoardPosition:
    """Represents an 8x8 chessboard position (Rank 1-8, File A-H)."""
    rank: int  # 1-8 (Risk level: 1=lowest, 8=highest)
    file: str  # A-H (Quality: C-F=center/high, A-B/G-H=flanks)

    def __post_init__(self):
        if not 1 <= self.rank <= 8:
            raise ValueError(f"Rank must be 1-8, got {self.rank}")
        if self.file not in "ABCDEFGH":
            raise ValueError(f"File must be A-H, got {self.file}")

    def is_center_file(self) -> bool:
        """Check if position is in center files (high quality)."""
        return self.file in "CDEF"

    def is_flank_file(self) -> bool:
        """Check if position is in flank files (edge/lower quality)."""
        return self.file in "ABGH"

    def __str__(self) -> str:
        return f"{self.file}{self.rank}"


@dataclass
class StockTile:
    """Represents a stock on the board with technical metrics."""
    ticker: str
    current_price: float
    moving_average: float
    sos_score: float  # 0.0-1.0
    vix_level: float
    square_color: SquareColor
    rank: int
    file: str
    momentum: float
    volatility: float

    @property
    def position(self) -> BoardPosition:
        return BoardPosition(self.rank, self.file)

    def __str__(self) -> str:
        return f"{self.ticker} @ ${self.current_price:.2f} (MA: ${self.moving_average:.2f}) - {self.square_color.value.upper()}"


@dataclass
class Trade:
    """Records a trade execution."""
    trade_id: str
    piece_id: str
    ticker: str
    action: str  # BUY, SELL
    entry_date: datetime
    exit_date: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    shares: int
    reason: str
    initiated_on_square: SquareColor
    is_tactical: bool


@dataclass
class GameState:
    """Represents the overall game state."""
    phase: GamePhase
    total_capital: float
    momentum_capital: float
    king_cash: float  # Capital not deployed
    current_date: datetime
    pieces_deployed: int
    positions_open: Dict[str, Piece] = field(default_factory=dict)  # ticker -> piece
    trades: List[Trade] = field(default_factory=list)
    piece_inventory: Dict[PieceType, List[Piece]] = field(default_factory=dict)


# ============================================================================
# PIECE INVENTORY MANAGEMENT (Requirement P.1-P.6)
# ============================================================================

class PieceInventory:
    """Manages the chess piece inventory and valuations."""

    def __init__(self, momentum_capital: float):
        self.momentum_capital = float(momentum_capital)
        self.pieces: List[Piece] = []
        self._build_pieces()

    def _build_pieces(self):
        """Build all pieces with monetary valuations."""
        multiplier = self.momentum_capital / TOTAL_POINTS
        piece_counter = 0

        for piece_type, quantity in PIECE_CONFIG:
            for _ in range(quantity):
                pv = piece_type.value
                monetary_value = pv * multiplier
                piece = Piece(
                    piece_id=f"{piece_type.name}_{piece_counter}_{id(self)}",
                    piece_type=piece_type,
                    point_value=pv,
                    monetary_value=monetary_value,
                )
                self.pieces.append(piece)
                piece_counter += 1

    def summary(self) -> Dict[str, Dict]:
        """Return summary of inventory by type."""
        summary = {}
        for piece in self.pieces:
            ptype = piece.piece_type.name
            if ptype not in summary:
                summary[ptype] = {"count": 0, "assigned": 0, "total_value": 0.0}
            summary[ptype]["count"] += 1
            summary[ptype]["total_value"] += piece.monetary_value
            if piece.assigned:
                summary[ptype]["assigned"] += 1
        return summary

    def get_best_piece_for_rank(self, rank: int) -> Optional[Piece]:
        """Get highest-value unassigned piece suitable for rank."""
        unassigned = [p for p in self.pieces if not p.assigned]
        if not unassigned:
            return None
        # Prefer larger pieces for higher ranks
        return sorted(unassigned, key=lambda p: -p.point_value)[0]

    def get_tactical_piece(self) -> Optional[Piece]:
        """Get smallest unassigned piece for tactical Black square entry."""
        unassigned = [p for p in self.pieces if not p.assigned and p.piece_type in (PieceType.PAWN, PieceType.KNIGHT)]
        if not unassigned:
            return None
        return sorted(unassigned, key=lambda p: p.point_value)[0]

    def assign_piece(self, piece_id: str) -> bool:
        """Assign a piece to the board."""
        for p in self.pieces:
            if p.piece_id == piece_id:
                p.assigned = True
                return True
        return False

    def unassign_piece(self, piece_id: str) -> bool:
        """Remove piece from board (retreat or capture)."""
        for p in self.pieces:
            if p.piece_id == piece_id:
                p.assigned = False
                p.position = None
                p.entry_date = None
                p.entry_price = None
                p.entry_square = None
                p.shares = 0
                p.tactical_black = False
                return True
        return False

    def get_piece(self, piece_id: str) -> Optional[Piece]:
        """Retrieve a piece by ID."""
        for p in self.pieces:
            if p.piece_id == piece_id:
                return p
        return None


# ============================================================================
# SOS SCORING SYSTEM (Requirement R.1, R.4, R.5)
# ============================================================================

class SOSScorer:
    """Calculates Strength of Square (SOS) scores."""

    @staticmethod
    def compute_sos_frame(
        price_df: pd.DataFrame,
        ma_period: int = 50,
        vix_data: Optional[pd.Series] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> pd.DataFrame:
        """
        Compute SOS scores for all tickers across all dates.
        
        SOS = weighted combination of:
        - Momentum (60%): Price relative to MA
        - Volatility (25%): Risk-adjusted volatility
        - Liquidity (15%): Placeholder (neutral 0.5)
        
        VIX Adjustment: Higher VIX reduces risk tolerance, adjusting weights.
        """
        if weights is None:
            weights = {"M": 0.6, "Vol": 0.25, "Lq": 0.15}

        tickers = price_df.columns.tolist()
        ma = price_df.rolling(window=ma_period, min_periods=ma_period).mean()
        returns = price_df.pct_change().fillna(0)
        vol = returns.rolling(window=ma_period, min_periods=ma_period).std().fillna(0)

        # Momentum: price relative to MA
        mom = (price_df / ma - 1.0).fillna(0)

        # Build output frame
        out = pd.DataFrame(index=price_df.index)
        for t in tickers:
            out[(t, "PRICE")] = price_df[t]
            out[(t, "MA")] = ma[t]
            out[(t, "MOM")] = mom[t]
            out[(t, "VOL")] = vol[t]
            out[(t, "SOS")] = np.nan

        out.columns = pd.MultiIndex.from_tuples(out.columns)

        # Compute SOS per date
        for date in price_df.index:
            mom_raw = out.loc[date, pd.IndexSlice[:, "MOM"]].fillna(0)
            vol_raw = out.loc[date, pd.IndexSlice[:, "VOL"]].fillna(0)

            # Normalize momentum to [0, 1]
            if mom_raw.max() == mom_raw.min():
                mom_score = pd.Series(0.5, index=mom_raw.index)
            else:
                mom_score = (mom_raw - mom_raw.min()) / (mom_raw.max() - mom_raw.min())

            # Volatility score: lower vol -> higher score
            if vol_raw.max() == vol_raw.min():
                vol_score = pd.Series(0.5, index=vol_raw.index)
            else:
                vol_score = 1.0 - (vol_raw - vol_raw.min()) / (vol_raw.max() - vol_raw.min())

            lq_score = pd.Series(0.5, index=mom_raw.index)

            # Adjust weights based on VIX if available
            adj_weights = weights.copy()
            if vix_data is not None and date in vix_data.index:
                vix_val = vix_data.loc[date]
                # Higher VIX reduces risk tolerance
                risk_factor = min(1.0, vix_val / 20.0)  # Normalize ~20 as baseline
                adj_weights["M"] = weights["M"] * (1 - 0.2 * risk_factor)
                adj_weights["Vol"] = weights["Vol"] * (1 + 0.2 * risk_factor)

            # Compute weighted SOS
            sos_raw = (
                adj_weights["M"] * mom_score
                + adj_weights["Vol"] * vol_score
                + adj_weights["Lq"] * lq_score
            )

            # Normalize to [0, 1]
            if sos_raw.max() == sos_raw.min():
                sos_norm = pd.Series(0.5, index=sos_raw.index)
            else:
                sos_norm = (sos_raw - sos_raw.min()) / (sos_raw.max() - sos_raw.min())

            for ticker_idx, t in enumerate(tickers):
                out.at[date, (t, "SOS")] = sos_norm.iloc[ticker_idx]

        return out.reindex(sorted(out.columns), axis=1)

    @staticmethod
    def sos_to_rank(sos_value: float) -> int:
        """Map SOS [0,1] to chess rank [1,8]."""
        rank = 1 + int(np.floor((1.0 - float(sos_value)) * 8.0))
        return max(1, min(8, rank))

    @staticmethod
    def sos_to_file(sos_value_secondary: float) -> str:
        """Map SOS secondary component to file [A-H]."""
        idx = int(np.floor(float(sos_value_secondary) * 8.0))
        return "ABCDEFGH"[max(0, min(7, idx))]

    @staticmethod
    def sos_to_position(sos_value: float) -> BoardPosition:
        """Map SOS to a board position (rank, file)."""
        rank = SOSScorer.sos_to_rank(sos_value)
        file = SOSScorer.sos_to_file(sos_value)
        return BoardPosition(rank, file)


# ============================================================================
# BOARD STATE & RULES (Requirement R.1-R.17)
# ============================================================================

class ChessBoard:
    """Represents the 8x8 trading board with stock positions."""

    def __init__(self):
        self.tiles: Dict[str, StockTile] = {}  # ticker -> StockTile
        self.pieces_on_board: Dict[str, Piece] = {}  # ticker -> Piece

    def update_stock(
        self,
        ticker: str,
        price: float,
        ma: float,
        sos_score: float,
        vix: float,
        momentum: float,
        volatility: float,
    ):
        """Update stock position on board."""
        square_color = SquareColor.WHITE if price > ma else SquareColor.BLACK
        rank = SOSScorer.sos_to_rank(sos_score)
        file = SOSScorer.sos_to_file(sos_score)

        self.tiles[ticker] = StockTile(
            ticker=ticker,
            current_price=price,
            moving_average=ma,
            sos_score=sos_score,
            vix_level=vix,
            square_color=square_color,
            rank=rank,
            file=file,
            momentum=momentum,
            volatility=volatility,
        )

    def get_tile(self, ticker: str) -> Optional[StockTile]:
        """Get a stock tile by ticker."""
        return self.tiles.get(ticker)

    def display_board(self):
        """Display current board state (ASCII art)."""
        board = [["." for _ in range(8)] for _ in range(8)]

        for tile in self.tiles.values():
            rank_idx = 8 - tile.rank  # Invert for display
            file_idx = ord(tile.file) - ord('A')
            marker = "W" if tile.square_color == SquareColor.WHITE else "B"
            board[rank_idx][file_idx] = marker

        print("\n  A B C D E F G H")
        for i, row in enumerate(board):
            rank = 8 - i
            print(f"{rank} {' '.join(row)}")
        print()


# ============================================================================
# TRADING RULES ENGINE (Requirement R.6-R.17)
# ============================================================================

class TradingRulesEngine:
    """Implements core trading rules and constraints."""

    def __init__(self, inventory: PieceInventory, max_positions: int = 8):
        self.inventory = inventory
        self.max_positions = max_positions
        self.rules_warnings: List[str] = []

    def can_deploy_on_white(self, tile: StockTile, piece: Piece) -> Tuple[bool, str]:
        """
        Rule R.6, R.13: Can deploy any piece on White Square.
        Higher ranks require higher-value pieces.
        """
        if tile.square_color != SquareColor.WHITE:
            return False, "Position is not on White Square"

        # Suggest appropriate piece for rank
        if tile.rank <= 2:
            if piece.point_value < 1:
                return False, f"Rank {tile.rank} requires at least Pawn (PV>=1)"
        elif tile.rank <= 4:
            if piece.point_value < 3:
                return False, f"Rank {tile.rank} requires at least Knight/Bishop (PV>=3)"
        elif tile.rank <= 6:
            if piece.point_value < 5:
                return False, f"Rank {tile.rank} requires at least Rook (PV>=5)"
        else:
            if piece.point_value < 9:
                return False, f"Rank {tile.rank} requires Queen (PV>=9)"

        return True, "Valid deployment on White Square"

    def can_deploy_tactical_black(self, tile: StockTile, piece: Piece, reclaim_window: int = 3) -> Tuple[bool, str]:
        """
        Rule R.12, R.17: Only Pawns/Knights can enter Black squares.
        Must reclaim White within reclaim_window days or be sold.
        """
        if tile.square_color != SquareColor.BLACK:
            return False, "Position is not on Black Square"

        if piece.piece_type not in (PieceType.PAWN, PieceType.KNIGHT):
            return False, f"Only Pawns/Knights can trade Black squares, not {piece.piece_type.name}"

        return True, "Valid tactical Black entry"

    def check_retreat_required(self, piece: Piece, tile: StockTile, days_held: int = 0) -> Tuple[bool, str]:
        """
        Rule R.7: Mandatory retreat if:
        1. Position initiated on White, now on Black
        2. Tactical Black entry exceeds reclaim window
        """
        if piece.entry_square == SquareColor.WHITE and tile.square_color == SquareColor.BLACK:
            return True, "White→Black flip: MANDATORY RETREAT"

        if piece.tactical_black and days_held > piece.tactical_reclaim_window:
            return True, f"Tactical Black: Failed to reclaim White within {piece.tactical_reclaim_window} days"

        return False, ""

    def check_scaling_opportunity(self, piece: Piece, tile: StockTile) -> Optional[str]:
        """
        Rule R.14: Suggest scaling up (Pawn → Rook/Queen) when:
        - Position on White square at high rank (5+)
        - Strong momentum
        """
        if tile.square_color != SquareColor.WHITE:
            return None
        if tile.rank < 5:
            return None
        if piece.point_value >= 5:
            return None  # Already at high value
        return f"Consider promoting {piece.piece_type.name} to larger piece at Rank {tile.rank}"

    def check_profit_taking(self, piece: Piece, tile: StockTile, gain_pct: float) -> Optional[str]:
        """
        Rule R.15: Suggest profit taking when:
        - Position on Endgame ranks (7-8)
        - Positive gain
        """
        if tile.rank < 7:
            return None
        if gain_pct <= 0:
            return None
        return f"ENDGAME: {tile.ticker} at Rank {tile.rank}. Consider taking profit (+{gain_pct:.1f}%)"

    def check_game_phase(self, game_state: GameState) -> GamePhase:
        """
        Determine game phase:
        - OPENING: King secured, <4 pieces deployed
        - MIDDLEGAME: 4+ pieces deployed, <80% capital
        - ENDGAME: High ranks, closing trades
        """
        if game_state.pieces_deployed < 4:
            return GamePhase.OPENING
        elif game_state.pieces_deployed < 8 and game_state.king_cash > game_state.total_capital * 0.2:
            return GamePhase.MIDDLEGAME
        else:
            return GamePhase.ENDGAME


# ============================================================================
# MOVE SUGGESTION ENGINE (Requirement A.1-A.3)
# ============================================================================

class MoveSuggestionEngine:
    """Suggests optimal moves based on current board state."""

    def __init__(self, rules_engine: TradingRulesEngine, board: ChessBoard):
        self.rules_engine = rules_engine
        self.board = board

    def suggest_moves(
        self,
        game_state: GameState,
        piece_inventory: PieceInventory,
    ) -> List[Dict]:
        """
        Suggest top 3 optimal moves (Deployment, Advancement, Retreat/Capture).
        """
        suggestions = []

        # Scan all tiles for opportunities
        opportunities = []
        for ticker, tile in self.board.tiles.items():
            if ticker in game_state.positions_open:
                # Existing position: check retreat/advance
                piece = game_state.positions_open[ticker]
                advice = self._analyze_existing_position(piece, tile, game_state)
                if advice:
                    opportunities.extend(advice)
            else:
                # New opportunity: check deployment
                advice = self._analyze_deployment_opportunity(tile, piece_inventory, game_state)
                if advice:
                    opportunities.extend(advice)

        # Sort by score and return top 3
        opportunities.sort(key=lambda x: -x["priority_score"])
        return opportunities[:3]

    def _analyze_existing_position(self, piece: Piece, tile: StockTile, game_state: GameState) -> List[Dict]:
        """Analyze existing position for retreat/advance/profit-taking."""
        advice = []
        gain_pct = piece.gain_loss_pct(tile.current_price) if piece.entry_price else 0.0

        # Check retreat
        retreat_required, reason = self.rules_engine.check_retreat_required(piece, tile)
        if retreat_required:
            advice.append({
                "action": "RETREAT",
                "ticker": tile.ticker,
                "reason": reason,
                "priority_score": 100.0,
                "gain_loss_pct": gain_pct,
            })

        # Check profit-taking
        profit_hint = self.rules_engine.check_profit_taking(piece, tile, gain_pct)
        if profit_hint:
            advice.append({
                "action": "CAPTURE",
                "ticker": tile.ticker,
                "reason": profit_hint,
                "priority_score": 80.0 + gain_pct,
                "gain_loss_pct": gain_pct,
            })

        # Check scaling
        scale_hint = self.rules_engine.check_scaling_opportunity(piece, tile)
        if scale_hint:
            advice.append({
                "action": "ADVANCEMENT",
                "ticker": tile.ticker,
                "reason": scale_hint,
                "priority_score": 60.0 + (tile.sos_score * 20),
                "gain_loss_pct": gain_pct,
            })

        return advice

    def _analyze_deployment_opportunity(self, tile: StockTile, inventory: PieceInventory, game_state: GameState) -> List[Dict]:
        """Analyze new deployment opportunity."""
        advice = []

        # Check if White square deployment
        piece = inventory.get_best_piece_for_rank(tile.rank)
        if piece and tile.square_color == SquareColor.WHITE:
            can_deploy, reason = self.rules_engine.can_deploy_on_white(tile, piece)
            if can_deploy and game_state.pieces_deployed < game_state.king_cash / piece.monetary_value:
                advice.append({
                    "action": "DEPLOYMENT",
                    "ticker": tile.ticker,
                    "piece": piece.piece_type.name,
                    "reason": f"Deploy {piece.piece_type.name} on {tile}. SOS: {tile.sos_score:.2f}",
                    "priority_score": tile.sos_score * 100,
                    "sos_score": tile.sos_score,
                })

        # Check if tactical Black square entry
        tactical_piece = inventory.get_tactical_piece()
        if tactical_piece and tile.square_color == SquareColor.BLACK:
            can_deploy, reason = self.rules_engine.can_deploy_tactical_black(tile, tactical_piece)
            if can_deploy:
                advice.append({
                    "action": "DEPLOYMENT_TACTICAL",
                    "ticker": tile.ticker,
                    "piece": tactical_piece.piece_type.name,
                    "reason": f"Tactical Black entry with {tactical_piece.piece_type.name}. Risky mean reversion.",
                    "priority_score": tile.sos_score * 50,  # Lower priority than normal
                    "sos_score": tile.sos_score,
                })

        return advice


# ============================================================================
# MAIN CHESS FRAMEWORK CLASS
# ============================================================================

class ChessFrameworkTrader:
    """Main orchestrator for the chess trading framework."""

    def __init__(
        self,
        tickers: List[str],
        total_capital: float,
        risk_level: RiskLevel,
        ma_period: int = 50,
        max_positions: int = 8,
    ):
        if not (3 <= len(tickers) <= 10):
            raise ValueError("Must provide 3-10 tickers")

        self.tickers = tickers
        self.total_capital = total_capital
        self.risk_level = risk_level
        self.ma_period = ma_period
        self.max_positions = max_positions

        # Initialize components
        self.momentum_capital = total_capital * risk_level.allocation
        self.king_cash = total_capital - self.momentum_capital

        self.inventory = PieceInventory(self.momentum_capital)
        self.board = ChessBoard()
        self.rules_engine = TradingRulesEngine(self.inventory, max_positions)
        self.suggestion_engine = MoveSuggestionEngine(self.rules_engine, self.board)
        self.sos_scorer = SOSScorer()

        self.game_state = GameState(
            phase=GamePhase.OPENING,
            total_capital=total_capital,
            momentum_capital=self.momentum_capital,
            king_cash=self.king_cash,
            current_date=datetime.now(),
            pieces_deployed=0,
        )

        self.price_data: Optional[pd.DataFrame] = None
        self.sos_data: Optional[pd.DataFrame] = None

    def load_market_data(self, start_date: str, end_date: str):
        """Download market data for backtesting."""
        print(f"Loading market data for {self.tickers} from {start_date} to {end_date}...")

        df = yf.download(self.tickers, start=start_date, end=end_date, progress=False, auto_adjust=False)

        if "Adj Close" in df.columns:
            price = df["Adj Close"].copy()
        else:
            price = df["Close"].copy()

        self.price_data = price.reindex(columns=self.tickers)
        self.price_data = self.price_data.ffill().dropna()

        print(f"Loaded {len(self.price_data)} trading days")

        # Compute SOS data
        self.sos_data = self.sos_scorer.compute_sos_frame(self.price_data, ma_period=self.ma_period)

    def get_current_board_state(self, date_idx: int) -> Dict:
        """Get board state at a specific date."""
        if self.price_data is None or self.sos_data is None:
            return {}

        date = self.price_data.index[date_idx]
        state = {"date": date.strftime("%Y-%m-%d"), "tiles": {}}

        for ticker in self.tickers:
            if date not in self.price_data.index:
                continue

            price = self.price_data.loc[date, ticker]
            ma = self.sos_data.loc[date, (ticker, "MA")]
            sos = self.sos_data.loc[date, (ticker, "SOS")]
            momentum = self.sos_data.loc[date, (ticker, "MOM")]
            volatility = self.sos_data.loc[date, (ticker, "VOL")]
            vix = 20.0  # Placeholder (would need VIX data)

            # Skip if SOS is NaN (insufficient data)
            if pd.isna(sos):
                continue

            self.board.update_stock(ticker, price, ma, sos, vix, momentum, volatility)
            tile = self.board.get_tile(ticker)

            state["tiles"][ticker] = {
                "price": float(price),
                "ma": float(ma),
                "sos": float(sos),
                "position": str(tile.position),
                "square": tile.square_color.value,
            }

        return state

    def get_suggestions(self) -> List[Dict]:
        """Get current move suggestions."""
        return self.suggestion_engine.suggest_moves(self.game_state, self.inventory)

    def print_summary(self):
        """Print game summary."""
        print("\n" + "="*80)
        print("CHESS FRAMEWORK TRADING SYSTEM")
        print("="*80)
        print(f"\nTotal Capital: ${self.total_capital:,.2f}")
        print(f"Momentum Capital (Pieces): ${self.momentum_capital:,.2f}")
        print(f"King's Cash (Reserve): ${self.king_cash:,.2f}")
        print(f"Risk Level: {self.risk_level.label}")
        print(f"MA Period: {self.ma_period} days")
        print(f"\nPiece Inventory Summary:")
        for ptype, info in self.inventory.summary().items():
            print(f"  {ptype:8s}: {info['count']} total, {info['assigned']} assigned, ${info['total_value']:>10,.2f}")
        print("\n" + "="*80 + "\n")


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Initialize trader
    trader = ChessFrameworkTrader(
        tickers=["AAPL", "MSFT", "GOOGL"],
        total_capital=100000,
        risk_level=RiskLevel.MODERATE,
        ma_period=50,
        max_positions=5,
    )

    trader.print_summary()

    # Load market data
    trader.load_market_data("2023-01-01", "2023-12-31")

    # Get board state at a specific date
    if trader.price_data is not None:
        state = trader.get_current_board_state(len(trader.price_data) // 2)
        print(f"\nBoard State at {state['date']}:")
        for ticker, tile_info in state['tiles'].items():
            print(f"  {ticker}: {tile_info['position']} ({tile_info['square']}) - SOS: {tile_info['sos']:.3f}")

        # Get suggestions
        print("\nTop Move Suggestions:")
        suggestions = trader.get_suggestions()
        for i, sugg in enumerate(suggestions, 1):
            print(f"  {i}. {sugg.get('action', 'UNKNOWN')} - {sugg.get('ticker', '???')}: {sugg.get('reason', '')}")
