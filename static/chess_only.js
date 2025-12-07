// Minimal chess UI that uses server API (python-chess) for rules
let selected = null;
let fen = null;

// --- Game Configuration ---
let gameConfig = {
    tickers: ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'AMD'],
    totalCapital: 100000,
    riskAllocation: 0.30, // Corresponds to 'moderate'
    maPeriod: 50
};

// --- DOM Elements ---
const modal = document.getElementById('setup-modal');
const setupForm = document.getElementById('setup-form');
const mainContainer = document.getElementById('main-container');
const inventoryContainer = document.getElementById('inventory-counts');
const tooltip = document.getElementById('tooltip');
const suggestionsBtn = document.getElementById('get-suggestions-btn');
const suggestionsList = document.getElementById('suggestions-list');

// Portfolio and Piece Value Configuration
let TOTAL_PORTFOLIO_VALUE = gameConfig.totalCapital;
let CORE_PORTFOLIO_RATIO = 1 - gameConfig.riskAllocation;
let MOMENTUM_PORTFOLIO_VALUE = TOTAL_PORTFOLIO_VALUE * gameConfig.riskAllocation;

const piecePoints = { 'P': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 0 };

// Total points for a standard set of momentum pieces (1Q, 2R, 2B, 2N, 8P)
const TOTAL_MOMENTUM_POINTS = (1 * 9) + (2 * 5) + (2 * 3) + (2 * 3) + (8 * 1); // 39

const blackPieceThreats = {
  'k': { title: 'Systemic Risk' },
  'q': { title: 'Major Market Shock' },
  'r': { title: 'Macro Trend Shift' },
  'b': { title: 'Thematic Decline' },
  'n': { title: 'Volatility Event' },
  'p': { title: 'Market Noise' }
};

function getPieceMonetaryValue(symbol) {
  const upperSym = symbol.toUpperCase();
  if (upperSym === 'K') {
    return TOTAL_PORTFOLIO_VALUE * CORE_PORTFOLIO_RATIO;
  }
  const points = piecePoints[upperSym] || 0;
  const value = (points / TOTAL_MOMENTUM_POINTS) * MOMENTUM_PORTFOLIO_VALUE;
  return value;
}

function pieceValue(sym) {
  // basic chess piece values
  const map = { 'P': '1', 'N': '3', 'B': '3', 'R': '5', 'Q': '9', 'K': '∞' };
  const upper = sym.toUpperCase();
  return map[upper] || '';
}

function piecePortfolio(pos) {
  const idx = (pos.charCodeAt(0) + parseInt(pos[1], 10)) % demoTickers.length;
  const ticker = demoTickers[idx];
  const weight = 4 + ((idx * 3 + pos.charCodeAt(0)) % 22); // 4%..25%
  return { ticker, weight };
}

function mapSymbol(sym) {
  // sym from python-chess is like 'P','p','k'
  const map = { 'P': '♙', 'R':'♖','N':'♘','B':'♗','Q':'♕','K':'♔', 'p':'♟','r':'♜','n':'♞','b':'♝','q':'♛','k':'♚'};
  return map[sym] || sym;
}

async function init() {
  await fetch('/api/chess/init', { method: 'POST' });
  await refresh();
}

async function refresh() {
  const res = await fetch('/api/chess/state');
  const data = await res.json();
  if (data.status !== 'success') { document.getElementById('status').textContent = data.message; return; }
  fen = data.fen;
  renderBoard(data.pieces);
  document.getElementById('status').textContent = 'Turn: ' + data.turn;
}

function renderBoard(pieces) {
  const boardEl = document.getElementById('board');
  boardEl.innerHTML = '';
  const files = ['a','b','c','d','e','f','g','h'];
  for (let rank = 8; rank >= 1; rank--) {
    for (let f = 0; f < 8; f++) {
      const file = files[f];
      const pos = file + rank;
      const sq = document.createElement('div');
      const dark = (f + rank) % 2 === 0;
      sq.className = 'square ' + (dark ? 'dark' : 'light');
      sq.id = 'sq-' + pos;

      // --- FR-4.1: Display SOS score on each tile ---
      const stockData = getStockDataForTile(pos);
      const sosDiv = document.createElement('div');
      sosDiv.className = 'sos-score';
      sosDiv.textContent = `SOS: ${stockData.sos.toFixed(3)}`;
      sq.appendChild(sosDiv);

      const p = pieces.find(x => x.position === pos.toUpperCase());

      if (p) {
        // use simple symbols via map
        const sym = mapSymbol(p.symbol);
        const wrap = document.createElement('div');
        wrap.className = 'piece-wrap';
        const span = document.createElement('span');
        span.className = 'piece ' + (p.color === 'WHITE' ? 'white' : 'black');
        span.textContent = sym;
        wrap.appendChild(span);

        if (p.color === 'WHITE') {
            const monetaryValue = getPieceMonetaryValue(p.symbol);
            const valDiv = document.createElement('div');
            valDiv.className = 'piece-monetary-value';
            valDiv.textContent = `$${monetaryValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            wrap.appendChild(valDiv);
        } else { // Black piece
            const threat = blackPieceThreats[p.symbol.toLowerCase()];
            if (threat) {
                const threatTitleDiv = document.createElement('div');
                threatTitleDiv.className = 'threat-title';
                threatTitleDiv.textContent = threat.title;
                wrap.appendChild(threatTitleDiv);
            }
        }

        sq.appendChild(wrap);
        sq.dataset.pos = pos;
        sq.dataset.color = p.color;
      }

      // --- FR-4.3: Tile Hover ---
      sq.addEventListener('mouseenter', (e) => showTileTooltip(e, pos, stockData, dark));
      sq.addEventListener('mouseleave', hideTooltip);
      sq.addEventListener('mousemove', moveTooltip);

      sq.onclick = () => onSquareClick(pos);
      boardEl.appendChild(sq);
    }
  }
  // --- FR-4.2: Piece Display ---
  updatePieceInventory(pieces);
}

function getStockDataForTile(pos) {
    // This is mock data. In a real application, this would come from an API.
    const idx = (pos.charCodeAt(0) + parseInt(pos[1], 10)) % gameConfig.tickers.length;
    return {
        ticker: gameConfig.tickers[idx],
        sos: Math.random() * 0.5 + 0.25,
        price: 150 + Math.random() * 100,
        ma: 145 + Math.random() * 90,
        vix: 15 + Math.random() * 5
    };
}

function updatePieceInventory(piecesOnBoard) {
    const initialCounts = { 'Q': 1, 'R': 2, 'B': 2, 'N': 2, 'P': 8 };
    const deployedCounts = {};
    piecesOnBoard.forEach(p => {
        const sym = p.symbol.toUpperCase();
        if (p.color === 'WHITE') {
            deployedCounts[sym] = (deployedCounts[sym] || 0) + 1;
        }
    });

    inventoryContainer.innerHTML = '';
    for (const sym in initialCounts) {
        const deployed = deployedCounts[sym] || 0;
        const available = initialCounts[sym] - deployed;
        
        const item = document.createElement('div');
        item.className = 'inventory-item';
        item.innerHTML = `
            <span class="piece white">${mapSymbol(sym)}</span>
            <span class="count">${available}/${initialCounts[sym]}</span>
        `;
        inventoryContainer.appendChild(item);
    }
}

// --- Tooltip Functions ---
function showTileTooltip(event, pos, stockData, isDark) {
    const status = stockData.price > stockData.ma ? 'Bullish' : 'Bearish';
    tooltip.innerHTML = `
        <h4>${stockData.ticker} (${pos.toUpperCase()})</h4>
        <div class="tooltip-grid">
            <span class="label">SOS Score:</span><span class="value">${stockData.sos.toFixed(3)}</span>
            <span class="label">Price:</span><span class="value">$${stockData.price.toFixed(2)}</span>
            <span class="label">MA (${gameConfig.maPeriod}-Day):</span><span class="value">$${stockData.ma.toFixed(2)}</span>
            <span class="label">Status:</span><span class="value">${status}</span>
            <span class="label">VIX Level:</span><span class="value">${stockData.vix.toFixed(2)}</span>
        </div>
    `;
    tooltip.style.display = 'block';
    moveTooltip(event);
}

function hideTooltip() {
    tooltip.style.display = 'none';
}

function moveTooltip(event) {
    tooltip.style.left = `${event.pageX + 15}px`;
    tooltip.style.top = `${event.pageY + 15}px`;
}

async function onSquareClick(pos) {
  const el = document.getElementById('sq-' + pos);
  if (!selected) {
    // pick up piece if present
    if (!el || !el.textContent) return;
    selected = pos;
    el.classList.add('selected');
    return;
  }
  if (selected === pos) {
    // deselect
    document.getElementById('sq-' + selected).classList.remove('selected');
    selected = null; return;
  }

  // --- FR-5.4: Rule Violation Warning ---
  if (isRuleViolation(selected, pos)) {
      const proceed = confirm("Warning: This move violates a core strategic rule (e.g., deploying a Queen in the opening). Are you sure you want to proceed?");
      if (!proceed) {
          document.getElementById('sq-' + selected).classList.remove('selected');
          selected = null;
          return;
      }
  }

  // attempt move selected -> pos
  const body = { from: selected, to: pos };
  const res = await fetch('/api/chess/move', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
  const data = await res.json();
  if (data.status === 'success') {
    // successful move
    document.getElementById('sq-' + selected).classList.remove('selected');
    selected = null;
    await refresh();
  } else {
    // illegal
    alert('Illegal move: ' + (data.message || ''));
    document.getElementById('sq-' + selected).classList.remove('selected');
    selected = null;
  }
}

async function undo() {
  // simple: call move with none; python-chess supports pop but we didn't expose it. Quick hack: add endpoint later. For now refresh.
  alert('Undo not implemented on server yet.');
}

// --- Best Move Engine ---
suggestionsBtn.addEventListener('click', async function() {
    suggestionsBtn.disabled = true;
    suggestionsList.innerHTML = '<li><div class="reason">🤖 Thinking...</div></li>';

    // Collect SOS scores for all squares
    const sosScores = {};
    const files = ['a','b','c','d','e','f','g','h'];
    for (let rank = 8; rank >= 1; rank--) {
        for (let f = 0; f < 8; f++) {
            const pos = files[f] + rank;
            sosScores[pos] = getStockDataForTile(pos).sos;
        }
    }

    try {
        const response = await fetch('/api/chess/suggest_moves', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                fen: fen,
                sos_scores: sosScores
            })
        });
        const data = await response.json();

        if (data.status === 'success' && data.moves && data.moves.length > 0) {
            suggestionsList.innerHTML = '';
            data.moves.forEach((item, index) => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <div class="move">${index + 1}. ${item.move}</div>
                    <div class="reason">Reason: ${item.reason}</div>
                `;
                suggestionsList.appendChild(li);
            });
        } else {
            suggestionsList.innerHTML = `<li><div class="reason">No suggestions found or an error occurred: ${data.message || ''}</div></li>`;
        }
    } catch (error) {
        console.error('Error fetching move suggestions:', error);
        suggestionsList.innerHTML = '<li><div class="reason">Error fetching suggestions.</div></li>';
    } finally {
        suggestionsBtn.disabled = false;
    }
});

function isRuleViolation(from, to) {
    // Mock implementation of FR-5.4
    const piece = document.querySelector(`#sq-${from} .piece`);
    if (piece && piece.textContent === '♕' && fen.split(' ')[5] < 10) {
        return true; // Queen moved in the first 10 moves
    }
    return false;
}

// --- Setup Form Logic ---
setupForm.addEventListener('submit', function(e) {
    e.preventDefault();
    if (!validateSetupForm()) {
        return;
    }

    // Process tickers
    const tickerInput = document.getElementById('tickers').value;
    const tickers = tickerInput.split(',').map(t => t.trim()).filter(t => t);

    // Process risk allocation
    const riskLevel = document.getElementById('risk-level').value;
    const riskMap = { 'high': 0.5, 'moderate': 0.3, 'low': 0.1 };

    // Update game configuration
    gameConfig = {
        tickers: tickers,
        totalCapital: parseFloat(document.getElementById('capital').value),
        riskAllocation: riskMap[riskLevel],
        maPeriod: parseInt(document.getElementById('game-duration').value)
    };

    // Update portfolio constants
    TOTAL_PORTFOLIO_VALUE = gameConfig.totalCapital;
    CORE_PORTFOLIO_RATIO = 1 - gameConfig.riskAllocation;
    MOMENTUM_PORTFOLIO_VALUE = TOTAL_PORTFOLIO_VALUE * gameConfig.riskAllocation;

    // Hide modal and show board
    modal.style.display = 'none';
    mainContainer.style.display = 'block';

    // Initialize the game
    init();
});

function validateSetupForm() {
    let isValid = true;
    // Clear previous errors
    document.querySelectorAll('.error-message').forEach(el => el.style.display = 'none');

    // Validate tickers
    const tickerInput = document.getElementById('tickers').value;
    const tickers = tickerInput.split(',').map(t => t.trim()).filter(t => t);
    const tickerError = document.getElementById('tickers-error');
    if (tickers.length < 3 || tickers.length > 10) {
        tickerError.textContent = 'Please enter between 3 and 10 ticker symbols.';
        tickerError.style.display = 'block';
        isValid = false;
    }

    // Validate capital
    const capitalInput = document.getElementById('capital').value;
    const capitalError = document.getElementById('capital-error');
    if (parseFloat(capitalInput) <= 0 || isNaN(parseFloat(capitalInput))) {
        capitalError.textContent = 'Please enter a valid, positive number for capital.';
        capitalError.style.display = 'block';
        isValid = false;
    }

    return isValid;
}


window.onload = function() {
  document.getElementById('initBtn').onclick = init;
  document.getElementById('undoBtn').onclick = undo;
  // Don't auto-init anymore, wait for form submission
  // init();
}
