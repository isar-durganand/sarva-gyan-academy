# Contributing to Sarva Gyaan Academy

Thank you for your interest in contributing! 🎉

## How to Contribute

### Reporting Bugs

1. Check if the issue already exists
2. Create a new issue using the bug report template
3. Include:
   - Clear description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots if applicable

### Suggesting Features

1. Open a feature request issue
2. Describe the feature and its use case
3. Explain why it would benefit users

### Pull Requests

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Make your changes** with clear commit messages
5. **Test** your changes locally
6. **Push** to your fork
7. **Open a Pull Request** with:
   - Clear title and description
   - Reference to related issues
   - Screenshots for UI changes

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/sarva-gyan-academy.git
cd sarva-gyan-academy

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Run development server
python run.py
```

## Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to functions
- Keep functions small and focused

## Commit Messages

Use clear, descriptive commit messages:
- `feat: add student export to PDF`
- `fix: resolve attendance calculation bug`
- `docs: update installation guide`
- `style: format code with black`

## Questions?

Feel free to open an issue for any questions!
