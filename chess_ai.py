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
    Static evaluation (white-positive). Material + positional + opportunity bonus
    (higher opportunity = better for White = lower risk) and simple control of
    opportunity-heavy squares. Positive score favors White; negative favors Black.
    """
    if board.is_checkmate():
        # If it's checkmate, the side to move has lost.
        return float('inf') if board.turn == chess.BLACK else -float('inf')
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    # SoS is opportunity; weight it lightly in the opening and ramp to full midgame.
    ply_count = (board.fullmove_number - 1) * 2 + (0 if board.turn == chess.WHITE else 1)
    opp_weight = 0.1 + 0.9 * min(1.0, max(0.0, ply_count / 24.0))  # 10% early, 100% by ~24 ply

    total_score = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if not piece:
            continue

        material_score = piece_values[piece.piece_type]

        # Positional score: tables are white-oriented; mirror for black pieces
        if piece.color == chess.WHITE:
            positional_score = piece_square_tables[piece.piece_type][square]
        else:
            positional_score = piece_square_tables[piece.piece_type][chess.square_mirror(square)]

        # SOS bonus: scale only by base material to avoid compounding
        sos_bonus = 0
        if sos_scores:
            # sos here is opportunity: higher = better for White (lower risk)
            opp = sos_scores.get(chess.square_name(square).lower(), 0)
            sos_bonus = opp * (material_score * 0.3 * opp_weight)

        piece_score = material_score + positional_score + sos_bonus

        if piece.color == chess.WHITE:
            total_score += piece_score
        else:
            total_score -= piece_score

    # Control of opportunity-heavy squares: reward White control, penalize Black
    if sos_scores:
        control_score = 0
        for square in chess.SQUARES:
            opp = sos_scores.get(chess.square_name(square).lower(), 0)
            if opp <= 0:
                continue
            if board.is_attacked_by(chess.WHITE, square):
                control_score += opp * (10 * opp_weight)  # reward White influence over good squares
            if board.is_attacked_by(chess.BLACK, square):
                control_score -= opp * (10 * opp_weight)  # penalize White if Black controls them
        total_score += control_score

    # Penalize early king walks (encourage castling/safety) and premature queen sorties
    def apply_penalty(is_white: bool, amount: float):
        nonlocal total_score
        total_score -= amount if is_white else -amount

    # King safety: discourage king off its home square early unless castled
    wk_sq = board.king(chess.WHITE)
    bk_sq = board.king(chess.BLACK)
    if wk_sq is not None:
        white_king_moved = wk_sq != chess.E1
        white_castling_rights = board.has_kingside_castling_rights(chess.WHITE) or board.has_queenside_castling_rights(chess.WHITE)
        if white_king_moved and ply_count < 20 and white_castling_rights is False:
            penalty = max(0, 1200 - ply_count * 40)  # strong early deterrent, fades by 20 ply
            apply_penalty(True, penalty)
    if bk_sq is not None:
        black_king_moved = bk_sq != chess.E8
        black_castling_rights = board.has_kingside_castling_rights(chess.BLACK) or board.has_queenside_castling_rights(chess.BLACK)
        if black_king_moved and ply_count < 20 and black_castling_rights is False:
            penalty = max(0, 1200 - ply_count * 40)
            apply_penalty(False, penalty)

    # Early queen development penalty
    def queen_penalty(color, home_square, ply_cutoff=14, base_penalty=400):
        qs = list(board.pieces(chess.QUEEN, color))
        if not qs:
            return 0
        qsq = qs[0]
        if qsq != home_square and ply_count < ply_cutoff:
            return max(0, base_penalty - ply_count * 20)
        return 0

    qpen_w = queen_penalty(chess.WHITE, chess.D1)
    if qpen_w:
        apply_penalty(True, qpen_w)
    qpen_b = queen_penalty(chess.BLACK, chess.D8)
    if qpen_b:
        apply_penalty(False, qpen_b)

    return total_score

def minimax(board, depth, alpha, beta, maximizing_for_white, sos_scores):
    """Minimax with alpha-beta pruning. maximizing_for_white=True means we want a higher score for White."""
    if depth == 0 or board.is_game_over():
        return evaluate_board(board, sos_scores)

    if maximizing_for_white:
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

    def opening_heuristic_adjustment(b, m):
        """Nudge scores toward sound opening principles and away from early risk."""
        adj = 0
        fullmove = b.fullmove_number
        ply = (fullmove - 1) * 2 + (0 if b.turn == chess.WHITE else 1)

        piece = b.piece_at(m.from_square)
        if not piece:
            return adj

        is_capture = b.is_capture(m)
        is_castle = b.is_castling(m)

        # Early king walk penalty (non-castling)
        if piece.piece_type == chess.KING and not is_castle and ply < 20:
            adj -= 1500

        # Early queen adventure penalty (unless capture/check/late)
        if piece.piece_type == chess.QUEEN and ply < 14 and not is_capture:
            adj -= 500

        # Encourage center pawn development in opening
        if piece.piece_type == chess.PAWN and ply < 14:
            to_file = chess.square_file(m.to_square)
            to_rank = chess.square_rank(m.to_square)
            if b.turn == chess.WHITE and to_rank in (3, 4) and to_file in (3, 4):  # d/e files to rank 4/5 (0-indexed ranks)
                adj += 120
            if b.turn == chess.BLACK and to_rank in (4, 3) and to_file in (3, 4):  # d/e files toward rank 4/5 mirror
                adj += 120
            # discourage flank pawn pushes early
            if to_file in (0, 7) and to_rank < 6:
                adj -= 120

        # Encourage knight development toward c/f files in opening
        if piece.piece_type == chess.KNIGHT and ply < 14:
            to_file = chess.square_file(m.to_square)
            to_rank = chess.square_rank(m.to_square)
            if b.turn == chess.WHITE and to_file in (2, 5) and to_rank in (2, 3):
                adj += 150
            if b.turn == chess.BLACK and to_file in (2, 5) and to_rank in (5, 4):
                adj += 150

        return adj
    best_moves = []
    legal_moves = list(board.legal_moves)

    maximizing_for_white = board.turn == chess.WHITE

    for move in legal_moves:
        board.push(move)
        # After push, it is opponent's turn, so flip maximizing flag
        score = minimax(board, depth - 1, -float('inf'), float('inf'), not maximizing_for_white, sos_scores)
        board.pop()
        score += opening_heuristic_adjustment(board, move)
        best_moves.append((move, score))

    # Sort moves by score, descending
    best_moves.sort(key=lambda item: item[1], reverse=True)

    return best_moves[:num_moves]
