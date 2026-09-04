# ALPHA - Autonomous Options Agent Dashboard (HTML+Tailwind Version)

A lightweight, beautiful dashboard for monitoring the autonomous options trading agent built with HTML, Tailwind CSS, and vanilla JavaScript.

## Features

- **Real-time Data**: Connects to the same API backend as the Streamlit dashboard
- **Lightweight**: No heavy frameworks - just HTML, Tailwind CSS (via CDN), and vanilla JavaScript
- **Responsive**: Works on desktop and mobile devices
- **Dark Theme**: Optimized for terminal-like aesthetic
- **Auto-refresh**: Periodically updates data every 30 seconds
- **Agent Control**: Start/stop the trading agent directly from the dashboard
- **Complete Monitoring**: Overview, positions, trades, agent activity, risk management, and configuration

## Prerequisites

1. The trading agent API server must be running on `http://localhost:8000`
2. To start the API server:
   ```bash
   # From the project root
   uvicorn backend.app.main:app --reload
   ```

## Usage

1. Start the API server (if not already running):
   ```bash
   uvicorn backend.app.main:app --reload
   ```

2. Open the dashboard:
   - Option 1: Directly open `dashboard-html/index.html` in your web browser
   - Option 2: Serve it with a simple static server (recommended for CORS reasons):
     ```bash
     # Using Python
     cd dashboard-html
     python -m http.server 8080
     # Then open http://localhost:8080 in your browser
     ```

## API Endpoints Used

The dashboard consumes the following API endpoints from `http://localhost:8000/api/dashboard`:

- `/overview` - Portfolio metrics and account info
- `/agent-status` - Agent running status and system health
- `/equity-curve` - Historical portfolio value for charting
- `/live-activity` - Real-time agent activity feed
- `/positions` - Current open positions
- `/trades` - Trade execution history
- `/risk-summary` - Current risk metrics and exposure
- `/agent/config` - Current agent configuration
- `/agent/start` - Start the agent loop (POST)
- `/agent/stop` - Stop the agent loop (POST)

## Customization

### Changing Refresh Interval
To change how often the dashboard updates data, modify the `setInterval` duration in the JavaScript section (currently set to 30000ms = 30 seconds).

### Changing Theme Colors
The dashboard uses Tailwind CSS utility classes. To change colors, modify the relevant classes in the HTML:
- Primary color: `indigo-600` (can be changed to blue, green, red, etc.)
- Status colors: `green-400` (positive), `red-400` (negative), `yellow-400` (warning)

## Architecture

This dashboard is completely frontend-only and communicates with the existing FastAPI backend. It does not require any build process or dependencies beyond what's loaded via CDN:

- Tailwind CSS v3.x (via CDN)
- Alpine.js v3.x (via CDN) - for reactive UI components
- Chart.js (via CDN) - for equity curve visualization
- Google Fonts - Inter font family

## Comparison with Streamlit Version

| Feature | HTML+Tailwind Version | Streamlit Version |
|---------|----------------------|-------------------|
| Load Time | Nearly instant | Slower (Python backend) |
| Resource Usage | Very low | Higher (Python process) |
| Customization | Direct HTML/CSS modification | Streamlit theming |
| Deployment | Static file hosting | Requires Python server |
| API Dependency | Same backend API | Same backend API |
| Real-time Updates | Polling (30s interval) | Polling + auto-refresh |

## Troubleshooting

### "Cannot fetch API data" Errors
1. Ensure the API server is running: `uvicorn backend.app.main:app --reload`
2. Check that the server is accessible at `http://localhost:8000`
3. Verify network connectivity and firewall settings
4. Try accessing the API directly: `http://localhost:8000/api/dashboard/overview`

### CORS Issues
If you open the HTML file directly in a browser (file:// protocol), you may encounter CORS issues. To avoid this:
- Serve the dashboard via a simple static server (as shown in Usage above)
- Or use a browser extension that disables CORS for development

### Stale Data
The dashboard automatically refreshes data every 30 seconds. To manually refresh, simply reload the page.

## License

This dashboard is part of the Alpaca AI Trading Agent project. See the main project README for licensing information.