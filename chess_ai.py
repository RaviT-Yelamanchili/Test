import chess
import random

# Piece values
piece_values = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

# Piece-square tables for positional evaluation
# (from white's perspective)
pawn_table = [
    0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0
]

knight_table = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
]

bishop_table = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
]

rook_table = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0
]

queen_table = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
]

king_table = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20
]

piece_square_tables = {
    chess.PAWN: pawn_table,
    chess.KNIGHT: knight_table,
    chess.BISHOP: bishop_table,
    chess.ROOK: rook_table,
    chess.QUEEN: queen_table,
    chess.KING: king_table
}

def evaluate_board(board, sos_scores=None):
    """
    Evaluates the board from the perspective of the current player.
    Includes material, positional, and now SOS score evaluation.
    """
    if board.is_checkmate():
        return -float('inf') if board.turn == chess.WHITE else float('inf')
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    total_score = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            # Material value
            score = piece_values[piece.piece_type]
            
            # Positional value from piece-square tables
            # Tables are from white's perspective, so we flip for black
            if piece.color == chess.WHITE:
                positional_score = piece_square_tables[piece.piece_type][square]
            else:
                positional_score = piece_square_tables[piece.piece_type][chess.square_mirror(square)]
            
            score += positional_score

            # --- SOS Score Integration ---
            # Add a bonus for pieces on high-SOS squares.
            # This bonus is higher for more valuable pieces.
            if sos_scores:
                square_name = chess.square_name(square)
                sos = sos_scores.get(square_name.lower(), 0)
                # SOS bonus: scale by piece value and SOS score
                # A high SOS score (e.g., 0.8) on a queen is worth more than on a pawn
                sos_bonus = (sos * (score / 10)) 
                score += sos_bonus

            if piece.color == chess.WHITE:
                total_score += score
            else:
                total_score -= score
                
    # Return score from the perspective of the current player
    return total_score if board.turn == chess.WHITE else -total_score

def minimax(board, depth, alpha, beta, is_maximizing_player, sos_scores):
    """Minimax algorithm with alpha-beta pruning."""
    if depth == 0 or board.is_game_over():
        return evaluate_board(board, sos_scores)

    if is_maximizing_player:
        max_eval = -float('inf')
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta, False, sos_scores)
            board.pop()
            max_eval = max(max_eval, eval)
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = float('inf')
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta, True, sos_scores)
            board.pop()
            min_eval = min(min_eval, eval)
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval

def get_best_moves(board, sos_scores=None, num_moves=3, depth=3):
    """
    Gets the best moves for the current player using minimax.
    Returns a list of (move, score) tuples.
    """
    best_moves = []
    legal_moves = list(board.legal_moves)
    
    # Add a bit of randomness to explore different but equally good moves
    random.shuffle(legal_moves)

    for move in legal_moves:
        board.push(move)
        score = minimax(board, depth - 1, -float('inf'), float('inf'), board.turn == chess.BLACK, sos_scores)
        board.pop()
        best_moves.append((move, score))

    # Sort moves by score, descending
    best_moves.sort(key=lambda item: item[1], reverse=True)

    return best_moves[:num_moves]
