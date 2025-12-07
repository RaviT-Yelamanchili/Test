# Chess Framework - Quick Reference Card

## 🎯 One-Minute Overview

A **disciplined trading system** using chess principles to exploit short-term price inefficiencies in fundamentally strong stocks while maintaining strict risk management.

**Key Insight**: Let fundamentals (value investing) provide the safety floor, then use chess rules to discipline momentum trading.

---

## ♟️ The Pieces (Point Values = Capital)

| Piece | PV | Qty | Role | Typical Use |
|---|---|---|---|---|
| **King** | 0 | 1 | Survival | Reserve capital (not deployed) |
| **Queen** ♕ | 9 | 1 | Strike | High-confidence trades |
| **Rook** ♖ | 5 | 2 | Control | Core momentum positions |
| **Bishop** ♗ | 3 | 2 | Theme | Quality plays |
| **Knight** ♘ | 3 | 2 | Tactical | Mean reversion (Black squares) |
| **Pawn** ♙ | 1 | 8 | Test | Small position experiments |

**Total**: 39 points = Momentum capital (30% of total by default)

---

## 📊 The Board (Risk × Quality)

```
Rank (Risk Level):          File (Quality):
1-2: Safe                   C-F: Center (High)
3-4: Moderate               A-B,G-H: Flanks (Low)
5-6: Aggressive
7-8: Endgame
```

### Examples
- **C3**: Center-filed, moderate risk
- **A8**: Flank-filed, maximum risk
- **E2**: Center-filed, safe (opening)

---

## ⚪🔴 The Squares (Price vs MA)

| Square | Condition | Allowed | Action |
|---|---|---|---|
| **WHITE** ⚪ | Price > MA | ✅ ANY piece | BUY / SCALE / HOLD |
| **BLACK** 🔴 | Price < MA | ⚠️ Pawn/Knight | TACTICAL only / RETREAT |

### Rules
1. **White Deployment**: Any piece, any rank
2. **Black Entry**: Only Pawn/Knight, max 3 days, must reclaim White
3. **White→Black Flip**: MANDATORY RETREAT (stop-loss)

---

## 📈 SOS Score (Strength of Square)

**Formula**: 60% Momentum + 25% Volatility + 15% Liquidity

**Range**: 0.0 (worst) to 1.0 (best)

### What It Means
- **0.8-1.0**: Excellent - Buy/Scale
- **0.6-0.8**: Good - Deploy larger pieces
- **0.4-0.6**: Neutral - Small positions
- **0.2-0.4**: Caution - Tactical only
- **0.0-0.2**: Avoid - Or tactical Pawn

---

## 🎮 Game Phases

### OPENING (Early)
- Deploy Pawns/Knights
- Ranks 1-2 only
- Build foundation safely
- Ends when: 4+ pieces deployed

### MIDDLEGAME (Active)
- Deploy Rooks/Queen
- Ranks 3-6
- Scale winners
- Main trading period

### ENDGAME (Late)
- All pieces active
- Ranks 7-8
- Take profits
- Close winning positions

---

## ⚡ Quick Decisions

### When to DEPLOY
- Stock on **White square**
- SOS ≥ 0.6
- Rank matches piece value
- King's cash available
→ **Action**: Allocate position

### When to SCALE (Advancement)
- Position on **high rank** (5+)
- Stock still **White**
- Pawn earning +5%+
- **Action**: Promote to Rook

### When to RETREAT (Mandatory)
- Position initiated White
- Stock **flips to Black**
- Any loss level
→ **Action**: IMMEDIATE SELL (stop-loss)

### When to CAPTURE (Profit-Take)
- Position on **Rank 7-8**
- Gain ≥ 10%+
- **Action**: SELL for profit

---

## 🛑 Rules You Must Follow

| Rule | Consequence | Why |
|---|---|---|
| **R.7**: White→Black = Sell | Forced exit (loss) | Stop catastrophic losses |
| **R.12**: Black only Pawn/Knight | Can't use Rook | Risk management |
| **R.12**: 3-day reclaim window | Forced exit | Prevent bleeding positions |
| **R.8**: Never 100% deployed | Can't deploy all | King's safety |
| **R.14**: Rank matches piece | Warning if violated | Capital allocation |

---

## 💡 Suggestion Types

### DEPLOYMENT
*"Deploy Rook to AAPL at C5 (White) - SOS: 0.72"*
- Score 80+ = High priority
- Allocate momentum capital
- Set stop-loss at MA

### ADVANCEMENT
*"Pawn gained +8% - Promote to Rook at Rank 5"*
- Score 60+ = Medium priority
- Increase committed capital
- Raise stop-loss

### RETREAT
*"Black flip on MSFT - MANDATORY RETREAT"*
- Score 100 = HIGHEST priority
- Sell immediately
- Preserve capital

### CAPTURE
*"GOOGL at Rank 7, +15% gain - Consider taking profit"*
- Score 70+ = High priority
- Convert paper gains
- Reset for new opportunities

---

## 📊 Key Metrics Tracked

| Metric | Purpose | Good Range |
|---|---|---|
| SOS Score | Quality ranking | 0.6+ for deployment |
| Current Position | Rank/File on board | Favorable SOS |
| Gain/Loss % | Unrealized P&L | Watch for triggers |
| Days Held | Time in trade | Match reclaim window |
| Tactical Flag | Black square entry? | <3 days |

---

## 🎯 Setup (5 minutes)

1. **Tickers**: Choose 3-10 fundamentally strong stocks
2. **Capital**: Total trading capital (e.g., $100,000)
3. **Risk**: Select High (50%), Moderate (30%), or Low (10%)
4. **MA Period**: Choose 10, 20, 50, 100, or 200 days
5. **Start Trading**: Deploy first Pawn or Knight

---

## 💰 Capital Allocation Example

**$100,000 Total Capital**

**Moderate Risk (30%)**
- Momentum Capital (Pieces): **$30,000** (15 pieces)
- King's Cash (Reserve): **$70,000**

**Piece Values** (at 30% allocation):
- Queen: $6,923
- Rook: $3,846 each
- Bishop: $2,308 each
- Knight: $2,308 each
- Pawn: $769 each

---

## 🚀 First Trade (Step-by-Step)

1. **Check Board**: `status` → See current SOS scores
2. **Get Suggestions**: `suggest` → Review top moves
3. **Pick Stock**: E.g., "AAPL at C5, White, SOS 0.72"
4. **Pick Piece**: Match rank → Deploy Rook (value: $3,846)
5. **Deploy**: `deploy AAPL ROOK`
6. **Monitor**: Watch price vs MA
7. **Action**: 
   - White stays? Hold or scale
   - Flips Black? Retreat immediately
   - Rank 7-8? Take profits

---

## 🧠 Strategy Tips

### Do ✅
- Start with Pawns/Knights in Opening
- Deploy larger pieces only when confident
- Scale winners on White squares
- Retreat immediately on Black flip
- Take profits on Rank 7-8

### Don't ❌
- Ignore Black square signals
- Hold through reclaim window
- Deploy all capital at once
- Use large pieces on low ranks
- Average down into Black squares

---

## 📚 Key Terms

| Term | Meaning |
|---|---|
| **SOS** | Strength of Square - quality score |
| **White Square** | Price above MA - buy zone |
| **Black Square** | Price below MA - danger zone |
| **Rank** | Risk level (1=safe, 8=risky) |
| **File** | Quality (C-F=center, A-B/G-H=flank) |
| **PV** | Point Value - piece strength |
| **King's Cash** | Reserve capital (not deployed) |
| **Tactical** | Pawn/Knight on Black square |
| **Reclaim Window** | 3 days to return to White |
| **Retreat** | Forced exit/stop-loss |
| **Capture** | Profit-taking sale |
| **Advancement** | Scaling up (Pawn→Rook) |

---

## 🎓 Remember

**Chess Philosophy**: 
- Protect your King (capital)
- Control the center (quality stocks)
- Develop pieces gradually (build positions)
- Calculate variations (risk/reward)

**Value Investing Philosophy**:
- Fundamental analysis first (safety floor)
- Margin of safety (only trade strong stocks)
- Long-term focus (trust valuations)
- Psychological discipline (follow rules)

**Chess Framework Combines Both**:
- ✅ Fundamentals = Safety floor
- ✅ Momentum = Tactical advantage
- ✅ Rules = Psychological discipline
- ✅ Position sizing = Risk management

---

## 📞 Commands

```
status    Show all positions on board
board     Display 8×8 ASCII board
suggest   Get top 3 move recommendations
deploy    Place piece on stock (ticker, piece type)
retreat   Close position (ticker)
next      Advance to next trading day
quit      Exit simulator
```

---

## 📍 Where to Start

1. **Read This Card**: 5 minutes (you're here!)
2. **Run Demo**: `python chess_demo.py` (10 minutes)
3. **Try Interactive**: `python chess_cli.py` (20 minutes)
4. **Read Full Docs**: `FRAMEWORK_DOCUMENTATION.md` (30 minutes)
5. **Explore Code**: `chess_framework.py` (60 minutes)
6. **Build Your Strategy**: Customize and backtest

---

**Version**: 1.0.0  
**Status**: Production-ready MVP  
**Last Updated**: December 2025

**Good luck trading! ♟️🎯📈**
