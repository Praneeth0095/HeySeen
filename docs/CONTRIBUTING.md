# Contributing to HeySeen

Thank you for your interest in contributing to HeySeen! We welcome contributions from the community to help make this the best open-source PDF-to-LaTeX converter for Apple Silicon.

## Getting Started

### Prerequisites
- macOS with Apple Silicon (M1/M2/M3).
- Python 3.10+.
- `pip` and `venv`.

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/heyseen.git
   cd heyseen
   ```
2. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies in editable mode:
   ```bash
   pip install -e .
   pip install -r requirements.txt
   pip install pytest black isort mypy
   ```

## Development Workflow

1. **Create a Branch**: Always work on a new branch for your feature or fix.
   ```bash
   git checkout -b feature/amazing-new-feature
   ```

2. **Code Style**: We follow standard Python conventions.
   - Use `black` for formatting.
   - Use `isort` for import sorting.
   - Type hints are encouraged.

3. **Running Tests**:
   Before submitting a PR, ensure all tests pass:
   ```bash
   pytest
   ```
   If you add a new feature, please add a corresponding test case in `tests/`.

## Reporting Issues

If you find a bug or have a feature request, please open an issue on GitHub. Include:
- Description of the issue.
- Steps to reproduce.
- PDF file (if possible/public) causing the error.
- Logs (check `server_data/server.log`).

## Project Structure

- `heyseen/core`: Core logic (PDF loading, Layout, OCR).
- `heyseen/server`: FastAPI backend and static frontend.
- `heyseen/cli`: Command-line interface.
- `tests/`: Unit and integration tests.

## License

This project is licensed under the MIT License.
