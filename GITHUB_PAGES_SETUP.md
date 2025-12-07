# GitHub Pages Deployment Guide

## 🚀 Live GUI on GitHub Pages

Your Chess Framework Trading System is automatically deployed to GitHub Pages!

### Access the GUI

1. **Enable GitHub Pages**:
   - Go to repository Settings → Pages
   - Select "Deploy from a branch"
   - Choose `gh-pages` branch, `/root` folder
   - Save

2. **View the GUI**:
   - Your GUI will be available at: `https://<username>.github.io/<repo>`
   - Example: `https://raviT-yelamanchili.github.io/Test`

### How It Works

**GitHub Actions Workflow** (`.github/workflows/deploy-gui.yml`):
- Automatically runs on every push to `main` branch
- Builds the static site
- Deploys to `gh-pages` branch
- Updates GitHub Pages

**Two Modes**:

1. **Demo Mode** (GitHub Pages - No Backend Needed)
   - Static HTML/CSS/JavaScript
   - Shows sample trading board with demo data
   - Perfect for showcasing the UI design
   - No Python dependencies required

2. **Live Mode** (Local Backend)
   - Run `python chess_web_gui.py` locally
   - Opens `http://localhost:5000`
   - Full trading engine with real market data
   - Interactive trading with real-time updates

### What's Deployed

```
docs/
├── index.html          # Main GUI (standalone mode)
├── style.css          # Beautiful dark theme
└── app.js             # Interactive functionality
```

### Features in GitHub Pages Demo

✅ Beautiful Chess.com-inspired design
✅ 8×8 Trading board with real chess squares
✅ Portfolio summary with cash/pieces deployed
✅ Piece inventory with valuations
✅ Top move suggestions with SOS scores
✅ Dark theme with gradient accents
✅ Responsive layout
✅ Smooth animations

### Running Live Backend Locally

For full interactive trading with real market data:

```bash
# Install dependencies
pip install -r requirements_gui.txt

# Run Flask server
python chess_web_gui.py

# Open browser to http://localhost:5000
```

### Customization

**To add your domain**:
1. Update `cname` in `.github/workflows/deploy-gui.yml`
2. Add DNS records pointing to GitHub Pages
3. Push to trigger deployment

**To modify the demo data**:
1. Edit `docs/index.html` - update the `appState` object
2. Commit and push
3. Changes appear within seconds

### Architecture

```
┌─────────────────────────────────────────┐
│     Your GitHub Repository              │
├─────────────────────────────────────────┤
│  ┌──────────────────────────────────┐   │
│  │  .github/workflows/deploy-gui.yml│   │ ← Auto-deploys on push
│  └──────────────────────────────────┘   │
│                   ↓                      │
│  ┌──────────────────────────────────┐   │
│  │  Python Backend (chess_web_gui.py)   │ ← Run locally
│  └──────────────────────────────────┘   │
│                   ↓                      │
│  ┌──────────────────────────────────┐   │
│  │  Frontend (HTML/CSS/JavaScript)  │   │ ← Deployed to Pages
│  └──────────────────────────────────┘   │
│                   ↓                      │
│  ┌──────────────────────────────────┐   │
│  │  GitHub Pages (docs folder)      │   │ ← Public URL
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Troubleshooting

**Pages not updating?**
- Check GitHub Actions: Settings → Actions → Workflows
- Verify `gh-pages` branch exists
- Make sure Pages is enabled in Settings

**Want to modify the design?**
- Edit `templates/index.html` or `static/style.css`
- Changes auto-deploy within seconds

**Need live trading data?**
- Set up environment variables for broker APIs
- Modify `chess_web_gui.py` to connect to your broker
- Deploy backend service separately (Heroku, AWS, etc.)

### Next Steps

1. ✅ Enable GitHub Pages in repository settings
2. 🚀 Push to `main` branch
3. 🎯 Open your GUI URL
4. 📊 Share the link with others!

---

**For full trading capabilities**, run the Python backend locally while the GUI displays results in your browser.
