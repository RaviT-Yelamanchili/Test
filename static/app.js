// Chess Framework Trading System - Frontend JavaScript

let appState = {
    trader: null,
    boardState: null,
    initialized: false,
};

// Initialize Trader
async function initializeTrader() {
    const tickersStr = document.getElementById('tickersInput').value;
    const tickers = tickersStr.split(',').map(t => t.trim().toUpperCase());
    const capital = parseFloat(document.getElementById('capitalInput').value);
    const riskLevel = document.getElementById('riskLevelSelect').value;
    const maPeriod = parseInt(document.getElementById('maPeriodInput').value);

    if (tickers.length < 3) {
        showAlert('Please enter at least 3 tickers', 'error');
        return;
    }

    try {
        const response = await fetch('/api/initialize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tickers,
                capital,
                risk_level: riskLevel,
                ma_period: maPeriod,
            }),
        });

        const data = await response.json();

        if (data.status === 'error') {
            showAlert(data.message, 'error');
            return;
        }

        appState.initialized = true;
        appState.trader = data.summary;

        // Hide setup, show trading
        document.getElementById('setupPanel').style.display = 'none';
        document.getElementById('tradingDashboard').style.display = 'block';

        // Update UI
        updateBoardState();
        updatePieceInventory();
        updateSuggestions();

        showAlert(`✓ Trading system initialized with ${capital.toLocaleString('en-US', { style: 'currency', currency: 'USD' })} capital`, 'success');
    } catch (error) {
        showAlert(`Error: ${error.message}`, 'error');
    }
}

// Update Board State
async function updateBoardState() {
    if (!appState.initialized) return;

    try {
        const response = await fetch('/api/board-state');
        const data = await response.json();

        if (data.status === 'error') {
            showAlert(data.message, 'error');
            return;
        }

        appState.boardState = data;

        // Update date display
        document.getElementById('dateDisplay').textContent = data.date;

        // Update progress
        const progress = (data.date_idx / data.max_dates) * 100;
        document.getElementById('progressFill').style.width = progress + '%';

        // Update portfolio summary
        document.getElementById('kingCashValue').textContent = 
            '$' + data.king_cash.toLocaleString('en-US', { maximumFractionDigits: 0 });
        document.getElementById('piecesDeployedValue').textContent = 
            data.pieces_deployed + '/15';
        document.getElementById('openPositionsValue').textContent = 
            Object.keys(appState.trader?.positions || {}).length;

        // Render board
        renderBoard(data.tiles, data.pieces);
    } catch (error) {
        console.error('Error updating board:', error);
    }
}

// Render Chess Board
function renderBoard(tiles, pieces) {
    const boardEl = document.getElementById('board');
    boardEl.innerHTML = '';

    // support tiles as object or array
    const tilesArr = Array.isArray(tiles) ? tiles : Object.values(tiles || {});
    const tileMap = {};
    tilesArr.forEach(t => { if (t && t.position) tileMap[t.position] = t; });

    // Use pieces passed as parameter, or fall back to appState
    const piecesArr = pieces || (appState.boardState && appState.boardState.pieces) || [];
    const pieceMap = {};
    piecesArr.forEach(p => { if (p && p.position) pieceMap[p.position] = p; });

    console.log('DEBUG: Pieces array length:', piecesArr.length);
    console.log('DEBUG: Sample - A1 piece:', pieceMap['A1']);

    // Show a small badge on the board with the count of pieces detected (quick visibility)
    let badge = document.getElementById('piecesOnBoardCount');
    if (!badge) {
        badge = document.createElement('div');
        badge.id = 'piecesOnBoardCount';
        badge.className = 'board-badge';
        boardEl.parentElement.insertBefore(badge, boardEl);
    }
    badge.textContent = `Pieces on board: ${piecesArr.length}`;

    const pieceEmoji = {
        'QUEEN': { white: '♕', black: '♛' },
        'ROOK': { white: '♖', black: '♜' },
        'BISHOP': { white: '♗', black: '♝' },
        'KNIGHT': { white: '♘', black: '♞' },
        'PAWN': { white: '♙', black: '♟' },
        'KING': { white: '♔', black: '♚' }
    };

    // Render 8x8 board (rank 8 top)
    for (let rank = 8; rank >= 1; rank--) {
        for (let fileCode = 65; fileCode <= 72; fileCode++) {
            const file = String.fromCharCode(fileCode);
            const pos = file + rank;
            const tile = tileMap[pos];
            const piece = pieceMap[pos];

            const squareEl = document.createElement('div');
            const isWhite = ((fileCode + rank) % 2) === 0;
            squareEl.className = `square ${isWhite ? 'white' : 'black'}`;

            // Build inner content
            const content = document.createElement('div');
            content.className = 'square-content';
            content.style.cursor = tile ? 'pointer' : 'default';

            if (tile) {
                if (tile.sos > 0.65) squareEl.classList.add('highlight');
                // If a piece is on this square, show minimal info; otherwise show full details
                if (piece) {
                    content.innerHTML = `<div class="square-ticker">${tile.ticker}</div>`;
                } else {
                    content.innerHTML = `
                        <div class="square-ticker">${tile.ticker}</div>
                        <div class="square-meta">
                            <span class="square-sos">⚡ ${tile.sos.toFixed(3)}</span>
                            <span class="square-prob">• ${Math.round(tile.probability * 100)}%</span>
                        </div>
                        <div class="square-price">$${Math.round(tile.price)} → $${Math.round(tile.price_target || tile.price)}</div>
                        <div class="square-outcome">${tile.outcome || ''}</div>
                    `;
                }
                content.onclick = (e) => { e.stopPropagation(); showDeployModal(tile); };
            } else {
                content.innerHTML = `<div class="square-empty"></div>`;
            }

            // If a piece occupies this square, render it overlay
            if (piece) {
                console.log('Rendering piece at', pos, ':', piece.piece, piece.color);
                const pieceEl = document.createElement('div');
                pieceEl.className = 'piece-overlay';
                // add explicit color class for styling
                pieceEl.classList.add(piece.color === 'WHITE' ? 'piece-white' : 'piece-black');
                const emoji = pieceEmoji[piece.piece] ? pieceEmoji[piece.piece][piece.color.toLowerCase()] : '♟';
                pieceEl.textContent = emoji;
                pieceEl.setAttribute('aria-hidden', 'true');
                squareEl.appendChild(pieceEl);
            }

            squareEl.appendChild(content);
            boardEl.appendChild(squareEl);
        }
    }
}

// Update Piece Inventory
async function updatePieceInventory() {
    if (!appState.initialized) return;

    try {
        const response = await fetch('/api/piece-info');
        const data = await response.json();

        if (data.status === 'error') {
            showAlert(data.message, 'error');
            return;
        }

        const inventoryEl = document.getElementById('inventoryList');
        inventoryEl.innerHTML = '';

        const pieceEmoji = {
            'QUEEN': '♕',
            'ROOK': '♖',
            'BISHOP': '♗',
            'KNIGHT': '♘',
            'PAWN': '♙',
        };

        data.pieces.forEach(piece => {
            const itemEl = document.createElement('div');
            itemEl.className = 'inventory-item';
            itemEl.innerHTML = `
                <div class="inventory-header">
                    <div class="piece-icon">${pieceEmoji[piece.type] || '♟'}</div>
                    <div class="piece-info">
                        <h4>${piece.type}</h4>
                        <p>${piece.assigned}/${piece.count} deployed</p>
                    </div>
                </div>
                <div class="piece-stats">
                    <span class="piece-count">$${piece.total_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}</span>
                    <span class="piece-percentage">${piece.pct_deployed.toFixed(0)}%</span>
                </div>
            `;
            inventoryEl.appendChild(itemEl);
        });
    } catch (error) {
        console.error('Error updating inventory:', error);
    }
}

// Update Suggestions
async function updateSuggestions() {
    if (!appState.initialized) return;

    try {
        const response = await fetch('/api/suggestions');
        const data = await response.json();

        if (data.status === 'error') {
            showAlert(data.message, 'error');
            return;
        }

        const suggestionsEl = document.getElementById('suggestionsList');
        suggestionsEl.innerHTML = '';

        if (data.suggestions.length === 0) {
            suggestionsEl.innerHTML = '<div class="empty-state">No suggestions available</div>';
            return;
        }

        data.suggestions.slice(0, 5).forEach(sugg => {
            const itemEl = document.createElement('div');
            itemEl.className = 'suggestion-item';
            
            const gainLoss = sugg.gain_loss !== null ? 
                `<span style="color: ${sugg.gain_loss >= 0 ? '#22c55e' : '#ef4444'}">${sugg.gain_loss >= 0 ? '+' : ''}${sugg.gain_loss.toFixed(1)}%</span>` : 
                '';

            itemEl.innerHTML = `
                <div class="suggestion-header">
                    <div class="suggestion-ticker">🎯 ${sugg.ticker}</div>
                    <div class="suggestion-reason">${sugg.reason}</div>
                </div>
                <div class="suggestion-stats">
                    <div class="suggestion-sos">SOS: ${sugg.sos.toFixed(3)}</div>
                    <div class="suggestion-priority">Priority: ${sugg.priority}</div>
                </div>
                <div class="suggestion-action">
                    <button class="btn btn-buy" onclick="deployPiece('${sugg.ticker}')">Deploy</button>
                </div>
            `;
            suggestionsEl.appendChild(itemEl);
        });
    } catch (error) {
        console.error('Error updating suggestions:', error);
    }
}

// Show Deploy Modal
function showDeployModal(tile) {
    const modal = document.getElementById('deployModal');
    const formEl = document.getElementById('deployForm');

    formEl.innerHTML = `
        <div class="deploy-form">
            <p><strong>Stock:</strong> ${tile.ticker}</p>
            <p><strong>Position:</strong> ${tile.position}</p>
            <p><strong>Outcome:</strong> ${tile.outcome || 'N/A'}</p>
            <p><strong>Probability:</strong> ${Math.round((tile.probability || 0) * 100)}%</p>
            <p><strong>Current Price:</strong> $${tile.price.toFixed(2)}</p>
            <p><strong>Target Price:</strong> $${(tile.price_target || tile.price).toFixed(2)}</p>
            <p><strong>Change:</strong> ${tile.change_pct >= 0 ? '+' : ''}${tile.change_pct.toFixed(1)}%</p>
            <hr style="border: none; border-top: 1px solid var(--border-color); margin: 1rem 0;">
            <button class="btn btn-primary" onclick="deployPiece('${tile.ticker}'); closeModal('deployModal')">
                Confirm Deploy
            </button>
        </div>
    `;

    modal.style.display = 'flex';
}

// Deploy Piece
async function deployPiece(ticker) {
    if (!appState.initialized) return;

    try {
        const response = await fetch('/api/deploy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ticker,
                piece_type: 'PAWN',
            }),
        });

        const data = await response.json();

        if (data.status === 'error' || data.status === 'warning') {
            showAlert(data.message, data.status === 'error' ? 'error' : 'warning');
            return;
        }

        showAlert(`✓ ${data.message}`, 'success');
        updateBoardState();
        updatePieceInventory();
        updateSuggestions();
        updateTradeHistory();
    } catch (error) {
        showAlert(`Error: ${error.message}`, 'error');
    }
}

// Update Trade History
async function updateTradeHistory() {
    if (!appState.initialized) return;

    try {
        const response = await fetch('/api/trades');
        const data = await response.json();

        if (data.status === 'error') return;

        const tradesEl = document.getElementById('tradesList');
        tradesEl.innerHTML = '';

        if (data.trades.length === 0) {
            tradesEl.innerHTML = '<div class="empty-state">No trades yet</div>';
            return;
        }

        data.trades.slice(-10).reverse().forEach(trade => {
            const itemEl = document.createElement('div');
            itemEl.className = 'trade-item';
            itemEl.innerHTML = `
                <span class="trade-action ${trade.action.toLowerCase()}">${trade.action}</span>
                <div class="trade-details">
                    <div class="trade-ticker">${trade.ticker}</div>
                    <div class="trade-date">${trade.date}</div>
                </div>
                <div class="trade-price">$${trade.price.toFixed(2)}</div>
            `;
            tradesEl.appendChild(itemEl);
        });
    } catch (error) {
        console.error('Error updating trades:', error);
    }
}

// Navigation
async function goToNextDay() {
    if (!appState.initialized) return;

    try {
        const response = await fetch('/api/next-day', { method: 'POST' });
        const data = await response.json();

        if (data.status === 'error') {
            showAlert(data.message, 'error');
            return;
        }

        updateBoardState();
        updateSuggestions();
    } catch (error) {
        showAlert(`Error: ${error.message}`, 'error');
    }
}

async function goToPrevDay() {
    if (!appState.initialized) return;

    try {
        const response = await fetch('/api/prev-day', { method: 'POST' });
        const data = await response.json();

        if (data.status === 'error') {
            showAlert(data.message, 'error');
            return;
        }

        updateBoardState();
        updateSuggestions();
    } catch (error) {
        showAlert(`Error: ${error.message}`, 'error');
    }
}

// Modal
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

window.onclick = function (event) {
    const modal = document.getElementById('deployModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
};

// Alerts
function showAlert(message, type = 'info') {
    const alertEl = document.createElement('div');
    alertEl.className = `alert alert-${type}`;
    alertEl.textContent = message;
    alertEl.style.position = 'fixed';
    alertEl.style.top = '100px';
    alertEl.style.right = '20px';
    alertEl.style.zIndex = '1001';
    alertEl.style.maxWidth = '400px';
    alertEl.style.animation = 'slideIn 0.3s ease';

    document.body.appendChild(alertEl);

    setTimeout(() => {
        alertEl.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => alertEl.remove(), 300);
    }, 4000);
}

// Add slide animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Render Chess Board with all squares showing stock data or empty
function renderBoard(tiles) {
    const boardEl = document.getElementById('board');
    boardEl.innerHTML = '';
    
    // Create all 64 squares
    for (let rank = 8; rank >= 1; rank--) {
        for (let fileCode = 65; fileCode <= 72; fileCode++) {
            const file = String.fromCharCode(fileCode);
            const position = file + rank;
            const tile = tiles.find(t => t.position === position);
            
            const squareEl = document.createElement('div');
            const isWhiteSquare = (rank + fileCode) % 2 === 1;
            
            squareEl.className = `square ${isWhiteSquare ? 'white' : 'black'}`;
            
            if (tile) {
                // Highlight high SOS squares
                if (tile.sos > 0.65) {
                    squareEl.classList.add('highlight');
                }
                
                squareEl.innerHTML = `
                    <div class="square-content" onclick="showDeployModal({ticker: '${tile.ticker}', position: '${tile.position}', sos: ${tile.sos}, price: ${tile.price}, change_pct: ${tile.change_pct || 0}})">
                        <div class="square-ticker">${tile.ticker}</div>
                        <div class="square-sos">⚡ ${tile.sos.toFixed(3)}</div>
                        <div class="square-price">$${tile.price.toFixed(0)}</div>
                    </div>
                `;
            } else {
                squareEl.innerHTML = '<div class="square-empty"></div>';
            }
            
            boardEl.appendChild(squareEl);
        }
    }
}
