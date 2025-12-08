// Minimal chess UI that uses server API (python-chess) for rules
let selected = null;
let fen = null;

// --- Game Configuration ---
let gameConfig = {
    tickers: ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'AMD'],
    totalCapital: 100000,
    riskAllocation: 0.30, // Corresponds to 'moderate'
    maPeriod: 50,
    investedAmounts: []
};

// Flag to control looseness of data before the first committed move
let hasCommittedMove = false;

// --- DOM Elements ---
const modal = document.getElementById('setup-modal');
const setupForm = document.getElementById('setup-form');
const mainContainer = document.getElementById('main-container');
const inventoryContainer = document.getElementById('inventory-counts');
const tooltip = document.getElementById('tooltip');
const suggestionsBtn = document.getElementById('get-suggestions-btn');
const suggestionsList = document.getElementById('suggestions-list');
const allocationNote = document.getElementById('allocation-note');

const tickersInput = document.getElementById('tickers');
const investedGroup = document.getElementById('invested-group');
const investedLabel = document.getElementById('invested-label');
const investedHelper = document.getElementById('invested-helper');
const investedInput = document.getElementById('invested-amounts');

let allocationChartInstance = null;

// Portfolio and Piece Value Configuration
let TOTAL_PORTFOLIO_VALUE = gameConfig.totalCapital;
let CORE_PORTFOLIO_RATIO = 1 - gameConfig.riskAllocation;
let MOMENTUM_PORTFOLIO_VALUE = TOTAL_PORTFOLIO_VALUE * gameConfig.riskAllocation;

const piecePoints = { 'P': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 0 };

// Total points for a standard set of momentum pieces (1Q, 2R, 2B, 2N, 8P)
const TOTAL_MOMENTUM_POINTS = (1 * 9) + (2 * 5) + (2 * 3) + (2 * 3) + (8 * 1); // 39

const blackPieceThreats = {
    'k': { title: 'Systemic Risk' },
    'q': { title: 'Major Shock' },
    'r': { title: 'Linear Pressure' },
    'b': { title: 'Long-Range Pressure' },
    'n': { title: 'Tactical Threat' },
    'p': { title: 'Minor Risk' }
};

// Cache of latest SOS values for heat map rendering
let lastSosGrid = null;

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

const chartColors = [
    '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#EC4899', '#6366F1', '#84CC16', '#14B8A6'
];

function renderAllocationChart(tickers, amounts, totalCapital) {
    const ctx = document.getElementById('allocationChart');
    if (!ctx || !Array.isArray(tickers) || !Array.isArray(amounts)) return;

    const totalInvested = amounts.reduce((sum, v) => sum + (isNaN(v) ? 0 : v), 0);

    if (allocationChartInstance) {
        allocationChartInstance.destroy();
        allocationChartInstance = null;
    }

    if (totalInvested <= 0) {
        allocationNote.textContent = 'No capital deployed yet.';
        return;
    }

    const data = amounts.map(v => v);
    const bg = tickers.map((_, idx) => chartColors[idx % chartColors.length]);

    allocationChartInstance = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: tickers,
            datasets: [{
                data: data,
                backgroundColor: bg,
            }]
        },
        options: {
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });

    const pctOfCapital = totalCapital > 0 ? ((totalInvested / totalCapital) * 100).toFixed(1) : '0.0';
    allocationNote.textContent = `Deployed: $${totalInvested.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})} (${pctOfCapital}% of total capital)`;
}

function updateAllocationChart(deployedTickersSet) {
    const tickers = gameConfig.tickers;
    const invested = gameConfig.investedAmounts || [];

    // Build amounts: if ticker has at least one white piece deployed, show its invested amount; otherwise 0
    const amounts = tickers.map((t, idx) => {
        const amt = invested[idx] || 0;
        return deployedTickersSet.has(t) ? amt : 0;
    });

    renderAllocationChart(tickers, amounts, gameConfig.totalCapital);
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
        // Prepare SOS grid for heat map rendering
        lastSosGrid = Array.from({ length: 8 }, () => Array(8).fill(0));
    // Track which tickers have at least one white piece deployed
    const deployedTickers = new Set();
  for (let rank = 8; rank >= 1; rank--) {
    for (let f = 0; f < 8; f++) {
      const file = files[f];
      const pos = file + rank;
      const sq = document.createElement('div');
      const dark = (f + rank) % 2 === 0;
      sq.className = 'square ' + (dark ? 'dark' : 'light');
      sq.id = 'sq-' + pos;

      // --- FR-4.1: Display SOS score on each tile ---
    const stockData = getStockDataForTile(pos, hasCommittedMove);
            const rankIdx = 8 - rank; // 0 at top (rank 8), 7 at bottom (rank 1)
            lastSosGrid[rankIdx][f] = stockData.sos;
      const sosDiv = document.createElement('div');
      sosDiv.className = 'sos-score';
    sosDiv.textContent = stockData.sosDisplay;
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

            // Mark ticker as deployed for allocation chart
            deployedTickers.add(stockData.ticker);
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

    // Update allocation chart based on deployed tickers
    updateAllocationChart(deployedTickers);

        // Render side heat map based on latest SOS grid
        renderHeatmap();
}

function getStockDataForTile(pos, strictMode = true) {
    // Generates opportunity (higher = better, lower risk) and price data; loose ranges (pre-first move) only appear on ranks 1-2.
    const file = pos.charCodeAt(0) - 'a'.charCodeAt(0); // 0-7
    const rank = parseInt(pos[1], 10) - 1; // 0-7
    const useLooseRange = !strictMode && rank <= 1; // only rows 1-2 before first move

    // Center bias for SOS
    const dist_from_center_file = Math.min(Math.abs(file - 3), Math.abs(file - 4));
    const dist_from_center_rank = Math.min(Math.abs(rank - 3), Math.abs(rank - 4));
    const distance = dist_from_center_file + dist_from_center_rank;

    // Opportunity higher at center (lower risk); decreases toward edges
    let baseOpportunity = 0.75 - (distance * 0.08);
    let opportunity = baseOpportunity + (Math.random() * 0.1 - 0.05);
    opportunity = Math.max(0.05, Math.min(0.95, opportunity));
    const sos = opportunity; // keep field name but treat as opportunity (higher = better)

    // Price/MA mock data
    const priceCenter = 150 + Math.random() * 100;
    const maCenter = priceCenter * (0.9 + Math.random() * 0.15);

    let sosDisplay = `SOS: ${sos.toFixed(3)}`;
    let priceDisplay = `$${priceCenter.toFixed(2)}`;
    let maDisplay = `$${maCenter.toFixed(2)}`;

    if (useLooseRange) {
        const sosLow = Math.max(0.05, sos - 0.05);
        const sosHigh = Math.min(0.95, sos + 0.05);
        sosDisplay = `SOS: ${sosLow.toFixed(3)} – ${sosHigh.toFixed(3)}`;

        const priceLow = Math.max(1, priceCenter * 0.95);
        const priceHigh = priceCenter * 1.05;
        priceDisplay = `$${priceLow.toFixed(2)} – $${priceHigh.toFixed(2)}`;

        const maLow = Math.max(1, maCenter * 0.95);
        const maHigh = maCenter * 1.05;
        maDisplay = `$${maLow.toFixed(2)} – $${maHigh.toFixed(2)}`;
    }

    const idx = (file + rank) % gameConfig.tickers.length;
    return {
        ticker: gameConfig.tickers[idx],
        sos,
        sosDisplay,
        price: priceCenter,
        ma: maCenter,
        priceDisplay,
        maDisplay,
        vix: 15 + Math.random() * 5
    };
}

function sosToColor(value) {
    // value is opportunity (higher = better); convert to risk for color mapping
    const opp = Math.max(0, Math.min(1, value || 0));
    const risk = 1 - opp;
    const hue = (1 - risk) * 120; // high opportunity -> green, low opportunity -> red
    return `hsl(${hue}, 75%, 50%)`;
}

function renderHeatmap() {
    const canvas = document.getElementById('heatmapCanvas');
    if (!canvas || !lastSosGrid) return;
    const ctx = canvas.getContext('2d');
    const size = Math.min(canvas.width, canvas.height);
    const cell = size / 8;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) {
            const val = lastSosGrid[r][c] || 0;
            ctx.fillStyle = sosToColor(val);
            ctx.fillRect(c * cell, r * cell, cell, cell);
        }
    }

    // Optional subtle grid lines for readability
    ctx.strokeStyle = 'rgba(15,23,42,0.35)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 8; i++) {
        ctx.beginPath();
        ctx.moveTo(i * cell, 0);
        ctx.lineTo(i * cell, size);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(0, i * cell);
        ctx.lineTo(size, i * cell);
        ctx.stroke();
    }
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
            <span class="label">SOS Score:</span><span class="value">${stockData.sosDisplay || stockData.sos.toFixed(3)}</span>
            <span class="label">Price:</span><span class="value">${stockData.priceDisplay || `$${stockData.price.toFixed(2)}`}</span>
            <span class="label">MA (${gameConfig.maPeriod}-Day):</span><span class="value">${stockData.maDisplay || `$${stockData.ma.toFixed(2)}`}</span>
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
        hasCommittedMove = true;
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
    const tickerInputRaw = tickersInput.value;
    const tickers = tickerInputRaw.split(',').map(t => t.trim()).filter(t => t);

    // Process invested amounts (aligned with tickers)
    const invested = investedInput.value.split(',').map(v => v.trim()).filter(v => v !== '').map(v => parseFloat(v));

    // Process risk allocation
    const riskValue = parseFloat(document.getElementById('risk-level').value);

    // Update game configuration
    gameConfig = {
        tickers: tickers,
        totalCapital: parseFloat(document.getElementById('capital').value),
        riskAllocation: riskValue / 100, // Convert percentage to decimal
        maPeriod: parseInt(document.getElementById('game-duration').value),
        investedAmounts: invested
    };

    // Update portfolio constants
    TOTAL_PORTFOLIO_VALUE = gameConfig.totalCapital;
    CORE_PORTFOLIO_RATIO = 1 - gameConfig.riskAllocation;
    MOMENTUM_PORTFOLIO_VALUE = TOTAL_PORTFOLIO_VALUE * gameConfig.riskAllocation;

    // Hide modal and show board
    modal.style.display = 'none';
    mainContainer.style.display = 'block';

    // Initialize the game
    init().then(() => {
        renderAllocationChart(gameConfig.tickers, gameConfig.investedAmounts, gameConfig.totalCapital);
    });
});

function validateSetupForm() {
    let isValid = true;
    // Clear previous errors
    document.querySelectorAll('.error-message').forEach(el => el.style.display = 'none');

    // Validate tickers
    const tickerInputVal = tickersInput.value;
    const tickers = tickerInputVal.split(',').map(t => t.trim()).filter(t => t);
    const tickerError = document.getElementById('tickers-error');
    if (tickers.length < 1 || tickers.length > 10) {
        tickerError.textContent = 'Please enter between 1 and 10 ticker symbols.';
        tickerError.style.display = 'block';
        isValid = false;
    }

    // Validate risk
    const riskInput = document.getElementById('risk-level').value;
    const riskError = document.getElementById('risk-error');
    const riskValue = parseFloat(riskInput);
    if (isNaN(riskValue) || riskValue < 0 || riskValue > 50) {
        riskError.textContent = 'Please enter a number between 0 and 50.';
        riskError.style.display = 'block';
        isValid = false;
    }

    // Validate invested amounts
    const investedInputVal = investedInput.value;
    const investedError = document.getElementById('invested-error');
    const investedPieces = investedInputVal.split(',').map(v => v.trim());
    if (investedPieces.length !== tickers.length || investedPieces.some(v => v === '')) {
        investedError.textContent = 'Provide one amount per ticker (same order).';
        investedError.style.display = 'block';
        isValid = false;
    } else {
        const investedNums = investedPieces.map(v => parseFloat(v));
        if (investedNums.some(v => isNaN(v) || v < 0)) {
            investedError.textContent = 'Amounts must be numbers ≥ 0.';
            investedError.style.display = 'block';
            isValid = false;
        }
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

// Dynamic invested amounts prompt: update once tickers are entered
tickersInput.addEventListener('input', () => {
    const tickerInputVal = tickersInput.value;
    const tickers = tickerInputVal.split(',').map(t => t.trim()).filter(t => t);

    if (tickers.length > 0) {
        investedGroup.style.display = 'block';
        investedLabel.textContent = `Capital per ticker (${tickers.join(', ')})`;
        investedHelper.textContent = 'Enter amounts in the same order as your tickers.';
    } else {
        investedGroup.style.display = 'none';
        investedLabel.textContent = 'Capital deployed per ticker';
        investedHelper.textContent = '';
        investedInput.value = '';
    }
});
