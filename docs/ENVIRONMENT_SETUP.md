# Environment Setup Guide

This document outlines the steps to set up the development environment for the Quantum-Safe Banking Transaction PoC.

## Prerequisites

- **OS:** macOS 11+ (Intel or Apple Silicon) or Linux
- **Hardware:** 8GB RAM recommended
- **Python:** 3.9+ (3.11+ recommended)
- **C Compiler:** `clang` or `gcc` (for building liboqs)
- **Build Tools:** `cmake`, `ninja` (for building liboqs)

## 1. Install System Dependencies (macOS)

We recommend using [Homebrew](https://brew.sh/):
```bash
brew install cmake ninja openssl wget
```

## 2. Install liboqs (C Library for Post-Quantum Cryptography)

The `liboqs` library is required for ML-KEM-768 (post-quantum) support. If not installed, the application will fall back to classical cryptography only.

### Option A: macOS (Recommended)

```bash
brew install liboqs
```

### Option B: Linux / From Source

```bash
# Clone the liboqs repository
git clone -b main https://github.com/open-quantum-safe/liboqs.git
cd liboqs

# Build and install
mkdir build && cd build
cmake -GNinja -DOQS_USE_OPENSSL=ON -DCMAKE_INSTALL_PREFIX=/usr/local ..
ninja
sudo ninja install
```
*(Note: You may need to configure dynamic linker paths depending on your OS, e.g., `export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH` on Linux).*

### Option C: macOS / Linux (Alternative using `pip`)

If system package managers (like `brew`) fail or are unavailable, install build tools via `pip`:

```bash
# Install cmake and ninja
pip install cmake ninja

# Clone and build liboqs locally
git clone -b main https://github.com/open-quantum-safe/liboqs.git
cd liboqs
mkdir build && cd build
cmake -GNinja -DOQS_USE_OPENSSL=OFF -DBUILD_SHARED_LIBS=ON -DCMAKE_INSTALL_PREFIX=$HOME/.local ..
ninja
ninja install
```
*(Note: Export the local library path: `export DYLD_LIBRARY_PATH=$HOME/.local/lib:$DYLD_LIBRARY_PATH` on macOS, or `LD_LIBRARY_PATH=$HOME/.local/lib:$LD_LIBRARY_PATH` on Linux).*

## 3. Clone the Project Repository

```bash
cd /path/to/your/workspace
git clone <repo-url> be_project
cd be_project
```

## 4. Set Up Python Virtual Environment

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

## 5. Install Python Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt
```

*Note: The `requirements.txt` includes `liboqs-python`, which depends on the `liboqs` C library installed in step 2.*

## 6. Environment Variables

Create a `.env` file or export the following variables (optional, as defaults are provided):

```bash
export FLASK_ENV=development
export SECRET_KEY=your-dev-secret-key
export DATABASE_URL=sqlite:///transactions.db
```

## 7. Run the Application

```bash
# Start the Flask development server
python run.py
```

The application frontend and API will be accessible at `http://localhost:5000/`.

## 8. Verify the Setup (Testing)

To verify that the environment is fully operational and the cryptographic libraries are correctly linked, run the test suite:

```bash
# Run all tests with verbosity
pytest tests/ -v
```

If `liboqs` is successfully installed, all integration and PQC tests should pass. If not, PQC tests will be automatically skipped.
