#!/usr/bin/env python3
"""
Chess Framework Trading System - Beautiful Web GUI
Inspired by Chess.com's modern, professional design
Uses Flask + HTML5 + CSS3 + JavaScript for interactive trading
"""

from flask import Flask, render_template, jsonify, request
from flask import redirect
from chess_framework import (
    ChessFrameworkTrader,
    RiskLevel,
    SOSScorer,
    SquareColor,
)
try:
    import chess as pychess
    from chess_ai import get_best_moves
except Exception:
    pychess = None
    get_best_moves = None
import pandas as pd
import json
from datetime import datetime
import os
import random
import math

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Global trader instance
trader = None
current_date_idx = None
historical_trades = []

# Simple python-chess game state (for chess-only mode)
chess_game = {
    'board': None,  # pychess.Board instance
}


@app.route('/')
def index():
    """Serve the main GUI page."""
    # Redirect root to the chess-only page for a pure chess experience
    return redirect('/chess')


@app.route('/chess')
def chess_only():
    """Serve a minimal pure-chess page (no stocks)."""
    return render_template('chess_only.html')


@app.route('/api/chess/init', methods=['POST'])
def chess_init():
    """Initialize a fresh chess board (server-side with python-chess)."""
    global chess_game
    if pychess is None:
        return jsonify({'status': 'error', 'message': 'python-chess is not installed on server'}), 500
    try:
        chess_game['board'] = pychess.Board()
        return jsonify({'status': 'success', 'message': 'Chess board initialized'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/chess/state', methods=['GET'])
def chess_state():
    """Return board state (FEN + pieces)"""
    global chess_game
    if pychess is None:
        return jsonify({'status': 'error', 'message': 'python-chess not available'}), 500
    board = chess_game.get('board')
    if board is None:
        return jsonify({'status': 'error', 'message': 'Board not initialized'}), 400
    # Build pieces list
    pieces = []
    for square in pychess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            square_name = pychess.square_name(square).upper()
            pieces.append({'position': square_name, 'piece': piece.piece_type, 'color': 'WHITE' if piece.color else 'BLACK', 'symbol': piece.symbol()})

    return jsonify({'status': 'success', 'fen': board.fen(), 'turn': 'white' if board.turn else 'black', 'pieces': pieces})


@app.route('/api/chess/move', methods=['POST'])
def chess_move():
    """Attempt a move; body should contain 'from' and 'to' (e.g., 'e2' -> 'e4') or UCI like 'e2e4'."""
    global chess_game
    if pychess is None:
        return jsonify({'status': 'error', 'message': 'python-chess not available'}), 500
    board = chess_game.get('board')
    if board is None:
        return jsonify({'status': 'error', 'message': 'Board not initialized'}), 400

    data = request.json or {}
    move_raw = data.get('move')
    promotion = data.get('promotion')
    if not move_raw:
        # allow from/to
        frm = data.get('from')
        to = data.get('to')
        if not frm or not to:
            return jsonify({'status': 'error', 'message': 'Missing move'}), 400
        move_raw = frm + to

    try:
        # try UCI
        move = pychess.Move.from_uci(move_raw)
        if move not in board.legal_moves:
            # try SAN
            move = board.parse_san(move_raw)
        board.push(move)
        return jsonify({'status': 'success', 'fen': board.fen(), 'move': move.uci()})
    except Exception:
        # try SAN parse
        try:
            move = board.parse_san(move_raw)
            board.push(move)
            return jsonify({'status': 'success', 'fen': board.fen(), 'move': move.uci()})
        except Exception as e:
            return jsonify({'status': 'error', 'message': 'Illegal move or parse failure: ' + str(e)}), 400


@app.route('/api/initialize', methods=['POST'])
def initialize():
    """Initialize trader with user parameters."""
    global trader, current_date_idx, historical_trades
    
    data = request.json
    tickers = data.get('tickers', ['AAPL', 'MSFT', 'GOOGL'])
    capital = float(data.get('capital', 100000))
    risk_level_str = data.get('risk_level', 'MODERATE')
    ma_period = int(data.get('ma_period', 50))
    
    risk_map = {
        'HIGH': RiskLevel.HIGH,
        'MODERATE': RiskLevel.MODERATE,
        'LOW': RiskLevel.LOW
    }
    
    try:
        trader = ChessFrameworkTrader(
            tickers=tickers,
            total_capital=capital,
            risk_level=risk_map.get(risk_level_str, RiskLevel.MODERATE),
            ma_period=ma_period,
            max_positions=5,
        )
        
        # Load data
        trader.load_market_data("2023-01-01", "2023-12-31")
        current_date_idx = trader.ma_period
        historical_trades = []
        
        return jsonify({
            'status': 'success',
            'message': 'Trader initialized successfully',
            'summary': {
                'total_capital': trader.total_capital,
                'momentum_capital': trader.momentum_capital,
                'king_cash': trader.king_cash,
                'risk_level': risk_level_str,
                'ma_period': ma_period,
                'tickers': tickers,
                'dates_available': len(trader.price_data),
                'start_date': trader.price_data.index[0].strftime('%Y-%m-%d'),
                'end_date': trader.price_data.index[-1].strftime('%Y-%m-%d'),
            },
            'inventory': trader.inventory.summary()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/board-state', methods=['GET'])
def get_board_state():
    """Get current board state."""
    global trader, current_date_idx
    
    if trader is None or current_date_idx is None:
        return jsonify({'status': 'error', 'message': 'Trader not initialized'}), 400
    
    try:
        state = trader.get_current_board_state(current_date_idx)

        # current date index (timestamp) for data lookups
        date_idx = trader.price_data.index[current_date_idx]
        
        # Build tiles for all 64 squares. Stocks may repeat across multiple squares with slight price/SOS variations.
        tiles = []
        files = ['A','B','C','D','E','F','G','H']
        positions = [f + str(r) for r in range(8, 0, -1) for f in files]

        tickers = trader.tickers if trader is not None and len(trader.tickers) > 0 else ['AAPL','MSFT','GOOGL','AMZN','TSLA']

        # Build probabilistic outcome candidates for each ticker (e.g., Down/Flat/Up)
        candidates = []
        for ticker in tickers:
            # base values
            try:
                base_price = float(trader.price_data.loc[date_idx, ticker])
            except Exception:
                base_price = 100.0 + random.randint(-5, 5)

            try:
                base_ma = float(trader.sos_data.loc[date_idx, (ticker, 'MA')])
            except Exception:
                base_ma = base_price * 0.98

            try:
                base_sos = float(trader.sos_data.loc[date_idx, (ticker, 'SOS')])
                if pd.isna(base_sos):
                    base_sos = 0.5
            except Exception:
                base_sos = 0.5

            # momentum proxy
            momentum = 0.0
            try:
                if base_ma != 0:
                    momentum = (base_price - base_ma) / base_ma
            except Exception:
                momentum = 0.0

            # base probabilities influenced by momentum
            base_up = max(0.05, min(0.85, 0.35 + momentum * 0.6))
            base_down = max(0.05, min(0.85, 0.35 - momentum * 0.6))
            base_flat = max(0.01, 1.0 - (base_up + base_down))
            # normalize
            ssum = base_up + base_down + base_flat
            base_up /= ssum
            base_down /= ssum
            base_flat /= ssum

            outcomes = [
                ('DOWN', 0.90, base_down),
                ('FLAT', 1.00, base_flat),
                ('UP', 1.10, base_up),
            ]

            for o_name, multiplier, prob in outcomes:
                price_target = round(base_price * multiplier, 2)
                # adjust sos slightly depending on direction
                sos_adj = max(0.01, min(0.99, round(base_sos * (0.9 if o_name == 'DOWN' else 1.0 if o_name == 'FLAT' else 1.1), 3)))
                candidates.append({
                    'ticker': ticker,
                    'price': round(base_price, 2),
                    'price_target': price_target,
                    'probability': round(prob, 3),
                    'sos': sos_adj,
                    'ma': round(base_ma, 2),
                    'outcome': o_name,
                })

        # sort candidates by combined strength (sos * probability)
        candidates.sort(key=lambda c: c['sos'] * c['probability'], reverse=True)

        # Ensure we have at least 64 candidates by cycling if needed
        full_candidates = []
        idx = 0
        while len(full_candidates) < len(positions):
            full_candidates.append(candidates[idx % len(candidates)])
            idx += 1

        # map candidates to board positions
        for i, pos in enumerate(positions):
            c = full_candidates[i]
            file = pos[0]
            rank = int(pos[1])
            tiles.append({
                'ticker': c['ticker'],
                'position': pos,
                'rank': rank,
                'file': file,
                'square': SquareColor.WHITE.value if (ord(file) + rank) % 2 == 0 else SquareColor.BLACK.value,
                'sos': c['sos'],
                'price': c['price'],
                'price_target': c['price_target'],
                'ma': c['ma'],
                'change_pct': round(((c['price_target'] - c['ma']) / c['ma']) * 100, 2) if c['ma'] != 0 else 0.0,
                'probability': c['probability'],
                'outcome': c['outcome'],
            })

        # Provide initial chess piece layout overlay - all 32 pieces in starting positions
        pieces_layout = [
            # White pieces (rank 1)
            {'position': 'A1', 'piece': 'ROOK', 'color': 'WHITE'},
            {'position': 'B1', 'piece': 'KNIGHT', 'color': 'WHITE'},
            {'position': 'C1', 'piece': 'BISHOP', 'color': 'WHITE'},
            {'position': 'D1', 'piece': 'QUEEN', 'color': 'WHITE'},
            {'position': 'E1', 'piece': 'KING', 'color': 'WHITE'},
            {'position': 'F1', 'piece': 'BISHOP', 'color': 'WHITE'},
            {'position': 'G1', 'piece': 'KNIGHT', 'color': 'WHITE'},
            {'position': 'H1', 'piece': 'ROOK', 'color': 'WHITE'},
            # White pawns (rank 2)
            {'position': 'A2', 'piece': 'PAWN', 'color': 'WHITE'},
            {'position': 'B2', 'piece': 'PAWN', 'color': 'WHITE'},
            {'position': 'C2', 'piece': 'PAWN', 'color': 'WHITE'},
            {'position': 'D2', 'piece': 'PAWN', 'color': 'WHITE'},
            {'position': 'E2', 'piece': 'PAWN', 'color': 'WHITE'},
            {'position': 'F2', 'piece': 'PAWN', 'color': 'WHITE'},
            {'position': 'G2', 'piece': 'PAWN', 'color': 'WHITE'},
            {'position': 'H2', 'piece': 'PAWN', 'color': 'WHITE'},
            # Black pawns (rank 7)
            {'position': 'A7', 'piece': 'PAWN', 'color': 'BLACK'},
            {'position': 'B7', 'piece': 'PAWN', 'color': 'BLACK'},
            {'position': 'C7', 'piece': 'PAWN', 'color': 'BLACK'},
            {'position': 'D7', 'piece': 'PAWN', 'color': 'BLACK'},
            {'position': 'E7', 'piece': 'PAWN', 'color': 'BLACK'},
            {'position': 'F7', 'piece': 'PAWN', 'color': 'BLACK'},
            {'position': 'G7', 'piece': 'PAWN', 'color': 'BLACK'},
            {'position': 'H7', 'piece': 'PAWN', 'color': 'BLACK'},
            # Black pieces (rank 8)
            {'position': 'A8', 'piece': 'ROOK', 'color': 'BLACK'},
            {'position': 'B8', 'piece': 'KNIGHT', 'color': 'BLACK'},
            {'position': 'C8', 'piece': 'BISHOP', 'color': 'BLACK'},
            {'position': 'D8', 'piece': 'QUEEN', 'color': 'BLACK'},
            {'position': 'E8', 'piece': 'KING', 'color': 'BLACK'},
            {'position': 'F8', 'piece': 'BISHOP', 'color': 'BLACK'},
            {'position': 'G8', 'piece': 'KNIGHT', 'color': 'BLACK'},
            {'position': 'H8', 'piece': 'ROOK', 'color': 'BLACK'},
        ]

        # Final response
        return jsonify({
            'status': 'success',
            'date': state.get('date', ''),
            'date_idx': current_date_idx,
            'max_dates': len(trader.price_data) if trader is not None else 0,
            'phase': trader.game_state.phase.value if trader is not None else 'UNKNOWN',
            'king_cash': round(trader.game_state.king_cash, 2) if trader is not None else 0.0,
            'pieces_deployed': trader.game_state.pieces_deployed if trader is not None else 0,
            'tiles': tiles,
            'pieces': pieces_layout,
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/suggestions', methods=['GET'])
def get_suggestions():
    """Get move suggestions."""
    global trader
    
    if trader is None:
        return jsonify({'status': 'error', 'message': 'Trader not initialized'}), 400
    
    try:
        suggestions = trader.get_suggestions()
        
        formatted = []
        for sugg in suggestions[:5]:  # Top 5
            formatted.append({
                'action': sugg.get('action', 'UNKNOWN'),
                'ticker': sugg.get('ticker', '?'),
                'reason': sugg.get('reason', ''),
                'priority': round(sugg.get('priority_score', 0), 1),
                'sos': round(sugg.get('sos_score', 0), 3),
                'gain_loss': round(sugg.get('gain_loss_pct', 0), 1) if 'gain_loss_pct' in sugg else None,
            })
        
        return jsonify({
            'status': 'success',
            'suggestions': formatted
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/piece-info', methods=['GET'])
def get_piece_info():
    """Get piece inventory details."""
    global trader
    
    if trader is None:
        return jsonify({'status': 'error', 'message': 'Trader not initialized'}), 400
    
    try:
        summary = trader.inventory.summary()
        
        pieces = []
        for ptype, info in summary.items():
            pieces.append({
                'type': ptype,
                'count': info['count'],
                'assigned': info['assigned'],
                'unassigned': info['count'] - info['assigned'],
                'total_value': round(info['total_value'], 2),
                'pct_deployed': round((info['assigned'] / info['count'] * 100) if info['count'] > 0 else 0, 1),
            })
        
        return jsonify({
            'status': 'success',
            'pieces': pieces,
            'total_deployed': sum(p['assigned'] for p in pieces),
            'total_pieces': sum(p['count'] for p in pieces),
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/next-day', methods=['POST'])
def next_day():
    """Advance to next trading day."""
    global trader, current_date_idx
    
    if trader is None or current_date_idx is None:
        return jsonify({'status': 'error', 'message': 'Trader not initialized'}), 400
    
    try:
        if current_date_idx < len(trader.price_data) - 2:
            current_date_idx += 1
            return jsonify({
                'status': 'success',
                'message': f'Advanced to day {current_date_idx}',
                'date': trader.price_data.index[current_date_idx].strftime('%Y-%m-%d'),
                'date_idx': current_date_idx,
            })
        else:
            return jsonify({'status': 'error', 'message': 'End of data reached'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/prev-day', methods=['POST'])
def prev_day():
    """Go back to previous trading day."""
    global trader, current_date_idx
    
    if trader is None or current_date_idx is None:
        return jsonify({'status': 'error', 'message': 'Trader not initialized'}), 400
    
    try:
        if current_date_idx > trader.ma_period:
            current_date_idx -= 1
            return jsonify({
                'status': 'success',
                'message': f'Went back to day {current_date_idx}',
                'date': trader.price_data.index[current_date_idx].strftime('%Y-%m-%d'),
                'date_idx': current_date_idx,
            })
        else:
            return jsonify({'status': 'error', 'message': 'Beginning of data reached'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/deploy', methods=['POST'])
def deploy():
    """Deploy a piece to a stock."""
    global trader, historical_trades
    
    if trader is None:
        return jsonify({'status': 'error', 'message': 'Trader not initialized'}), 400
    
    data = request.json
    ticker = data.get('ticker', '')
    piece_type = data.get('piece_type', '')
    
    try:
        tile = trader.board.get_tile(ticker)
        if tile is None:
            return jsonify({'status': 'error', 'message': f'Stock {ticker} not found'}), 400
        
        piece = trader.inventory.get_best_piece_for_rank(tile.rank)
        if piece is None:
            return jsonify({'status': 'error', 'message': f'No unassigned {piece_type} available'}), 400
        
        # Check rules
        can_deploy, reason = trader.rules_engine.can_deploy_on_white(tile, piece)
        
        if not can_deploy:
            return jsonify({'status': 'warning', 'message': reason, 'force': True}), 200
        
        # Deploy
        trader.inventory.assign_piece(piece.piece_id)
        trader.game_state.positions_open[ticker] = piece
        trader.game_state.pieces_deployed += 1
        
        historical_trades.append({
            'date': trader.price_data.index[current_date_idx].strftime('%Y-%m-%d'),
            'action': 'BUY',
            'ticker': ticker,
            'piece': piece.piece_type.name,
            'price': tile.current_price,
        })
        
        return jsonify({
            'status': 'success',
            'message': f'Deployed {piece.piece_type.name} to {ticker}',
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/trades', methods=['GET'])
def get_trades():
    """Get trade history."""
    global historical_trades
    return jsonify({
        'status': 'success',
        'trades': historical_trades[-20:],  # Last 20 trades
        'total': len(historical_trades),
    })


@app.route('/api/chess/legal_moves', methods=['GET'])
def legal_moves():
    """Get legal moves for the current board state."""
    global chess_game
    board = chess_game.get('board')
    if board is None:
        return jsonify({"status": "error", "message": "Board not initialized"}), 400
    
    moves = [move.uci() for move in board.legal_moves]
    return jsonify({"status": "success", "legal_moves": moves})


@app.route('/api/chess/suggest_moves', methods=['POST'])
def suggest_moves():
    """Suggest best moves using the AI engine, factoring in SOS scores."""
    global chess_game
    if pychess is None or get_best_moves is None:
        return jsonify({'status': 'error', 'message': 'AI engine not available'}), 500

    board = chess_game.get('board')
    if board is None:
        return jsonify({'status': 'error', 'message': 'Board not initialized'}), 400

    data = request.json
    fen = data.get('fen', board.fen())
    sos_scores = data.get('sos_scores', {})
    
    try:
        # Create a board from FEN to ensure it's current
        current_board = pychess.Board(fen)
        
        # Get best moves from the AI, now with SOS scores
        moves = get_best_moves(current_board, sos_scores=sos_scores, num_moves=3)

        formatted_moves = []
        for move, score in moves:
            san_move = current_board.san(move)
            reason = f"Combines tactical advantage (score: {score:.2f}) with board opportunities."
            # Add specific reason if it moves to a high SOS square
            if sos_scores.get(pychess.square_name(move.to_square), 0) > 0.6:
                reason = f"Excellent move to a high-opportunity square (SOS: {sos_scores.get(pychess.square_name(move.to_square)):.3f}). Score: {score:.2f}."

            formatted_moves.append({
                "move": san_move,
                "reason": reason
            })

        return jsonify({'status': 'success', 'moves': formatted_moves})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error in AI engine: {str(e)}'}), 500


def main():
    """Run the Flask app."""
    print("\n" + "="*80)
    print("CHESS FRAMEWORK TRADING SYSTEM - WEB GUI")
    print("="*80)
    print("\n🌐 Starting web server...")
    print("📍 Open your browser to: http://localhost:5000")
    print("\n" + "="*80 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)


if __name__ == '__main__':
    main()
