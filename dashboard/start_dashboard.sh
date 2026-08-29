#!/bin/bash
echo "Setting up virtual environment for Alpaca AI Trading Agent Dashboard..."
echo

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade pip
python -m pip install --upgrade pip

# Install dependencies from requirements.txt
echo "Installing dependencies..."
pip install -r requirements.txt

echo
echo "Dependencies installed successfully!"
echo
echo "To run the dashboard:"
echo "  streamlit run dashboard/app.py"
echo
echo "Or use the shortcut:"
echo "  source venv/bin/activate && streamlit run dashboard/app.py"
echo
echo "Dashboard will be available at: http://localhost:8501"
echo

# Make script executable
chmod +x start_dashboard.sh