# Solana Vanity Address Generator
"The Worst Coded Company" Production

A high-performance tool for generating custom Solana wallet addresses with specific patterns. Available in both command-line and graphical user interface versions.

## Features

- **Custom Address Generation**:
  - Generate addresses with specific prefixes
  - Generate addresses with specific suffixes
  - Combine both prefix and suffix patterns
  - Case-sensitive or case-insensitive matching
  - Advanced pattern complexity analysis and time estimation
  - Search pattern history in saved wallets

- **Performance**:
  - Multi-core processing support
  - Real-time speed monitoring
  - Pause/Resume generation at any time
  - Accurate time remaining calculations based on pattern complexity
  - Detailed system resource usage monitoring
  - Optimized for high-speed generation

- **Wallet Management**:
  - Automatic saving of generated wallets
  - View saved wallet addresses with search patterns
  - Secure private key viewing option with warning system
  - JSON format wallet storage with pattern history
  - Organized wallet history view

- **User Interface**:
  - Modern, compact GUI design
  - Real-time progress updates
  - System resource monitoring
  - Status bar with detailed information
  - Clean, intuitive controls
  - Proper cleanup on exit

## Requirements

### System Requirements
- Python 3.8 or higher
- 2GB RAM minimum (4GB+ recommended)
- Multi-core CPU (performance scales with core count)
- 100MB free disk space

### Python Dependencies
```
solders>=0.18.0
base58>=2.1.1
psutil>=5.9.0
tkinter (usually included with Python)
```

## Setup and Installation

1. Ensure Python 3.8+ is installed:
   ```bash
   python --version
   # Should show Python 3.8 or higher
   ```

2. Clone the repository:
   ```bash
   git clone https://github.com/theworstcoded/sol-vanity.git
   cd sol-vanity
   ```

3. Create and activate a virtual environment (recommended):
   ```bash
   # Create virtual environment
   python -m venv .venv

   # Activate on Windows:
   .venv\Scripts\activate
   
   # Activate on macOS/Linux:
   source .venv/bin/activate
   ```

4. Install required packages:
   ```bash
   # Upgrade pip (recommended)
   python -m pip install --upgrade pip

   # Install dependencies
   pip install -r requirements.txt
   ```

5. Verify installation:
   ```bash
   # Test CLI version
   python solana_vanity.py --version

   # Test GUI version
   python vanity_gui.py --version
   ```

## Running the Application

### GUI Mode (Recommended)
```bash
# Make sure virtual environment is activated
python vanity_gui.py
```

### CLI Mode
```bash
# Make sure virtual environment is activated
python solana_vanity.py
```

### Common Issues

1. **tkinter not found**:
   - Windows: Reinstall Python with tkinter option checked
   - Ubuntu/Debian: `sudo apt-get install python3-tk`
   - macOS: Install Python through Homebrew: `brew install python-tk`

2. **Permission Issues**:
   - Windows: Run as administrator
   - Linux/macOS: `chmod +x solana_vanity.py vanity_gui.py`

3. **Virtual Environment Issues**:
   ```bash
   # If venv creation fails, try:
   python -m pip install --upgrade virtualenv
   virtualenv .venv
   ```

## Technical Details

- **Core Features**:
  - Built with Python 3.x
  - Uses Solders library for Solana interactions
  - Implements Base58 encoding
  - Multi-processing for optimal performance
  - Advanced probability-based time estimations

- **GUI Implementation**:
  - Built with tkinter for native look and feel
  - Threaded design for responsive interface
  - Real-time updates without blocking
  - Proper resource cleanup

- **Performance Optimization**:
  - Smart CPU core allocation
  - Efficient pattern matching
  - Minimal memory footprint
  - Accurate progress tracking

## Security Features

- Private keys stored locally in JSON format
- Private key viewing requires explicit user action
- Warning system for sensitive information
- Secure cleanup on program exit
- No external API dependencies for core functionality

## License

MIT License

## Credits

Created by The Worst Coded Company - Making terrible code work surprisingly well.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.