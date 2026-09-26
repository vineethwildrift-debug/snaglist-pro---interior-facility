# Contributing to Snaglist Pro

Thank you for your interest in contributing to Snaglist Pro!

## How to Contribute

### Reporting Bugs

Found a bug? Help us fix it!

1. **Check existing issues** to avoid duplicates
2. **Create a new issue** with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Your environment (Windows version, Python version, etc.)
   - Error logs (from `%LOCALAPPDATA%\SnaglistPro\snaglist_error.log`)

### Suggesting Features

Have an idea? We'd love to hear it!

1. **Check existing discussions** for similar ideas
2. **Create a new discussion** with:
   - Feature title and description
   - Use case / problem it solves
   - Proposed solution
   - Alternatives considered

### Contributing Code

Want to submit code? Follow these steps:

#### Setup Development Environment

```powershell
# Clone the repo
git clone https://github.com/vineethwildrift-debug/snaglist-pro---interior-facility.git
cd snaglist-pro---interior-facility

# Create virtual environment
python -m venv venv
venv\Scripts\Activate.ps1

# Install dependencies
cd 01_source
pip install -r requirements.txt
pip install -e .

# Install dev dependencies
pip install pytest pytest-cov flake8 black
```

#### Make Your Changes

1. **Create a feature branch**
   ```powershell
   git checkout -b feature/your-feature-name
   ```

2. **Follow code style**
   ```powershell
   black 01_source/snaglist_pro/
   flake8 01_source/snaglist_pro/
   ```

3. **Add tests** for new functionality
   ```powershell
   # Add tests to 01_source/tests/
   ```

4. **Run tests locally**
   ```powershell
   python -m pytest 01_source/tests/ -v
   ```

5. **Update documentation**
   - Update README if behavior changes
   - Update docstrings in code
   - Update CHANGELOG.md

#### Submit Your PR

1. **Commit with clear messages**
   ```
   git commit -m "Fix: Correct category matching logic"
   git commit -m "Feature: Add Google Sheets export"
   ```

2. **Push to your fork**
   ```powershell
   git push origin feature/your-feature-name
   ```

3. **Open a Pull Request**
   - Link related issues
   - Describe changes clearly
   - Include test results
   - Request review

## Code Standards

### Style Guide

- Follow PEP 8
- Use type hints for functions
- Keep functions small and focused
- Add docstrings to all functions

### Example

```python
def calculate_match_rate(matched: int, total: int) -> float:
    """
    Calculate match rate percentage.
    
    Args:
        matched: Number of matched items
        total: Total items
        
    Returns:
        Match rate as percentage (0-100)
    """
    if total == 0:
        return 0.0
    return (matched / total) * 100
```

## Testing Requirements

- All new code must have tests
- Tests must pass locally before PR
- Aim for >90% code coverage
- Update existing tests if behavior changes

```powershell
# Run tests with coverage
python -m pytest 01_source/tests/ --cov=snaglist_pro --cov-report=html
```

## Commit Message Guidelines

Use clear, descriptive commit messages:

- **Fix:** Corrections to existing functionality
- **Feature:** New functionality
- **Docs:** Documentation updates
- **Refactor:** Code restructuring (no behavior change)
- **Test:** Adding or updating tests

Examples:
- `Fix: Correct vendor assignment in config`
- `Feature: Add Google Sheets export`
- `Docs: Update installation guide`

## Review Process

1. Maintainers will review your PR
2. Feedback will be provided (usually within 48 hours)
3. Make requested changes
4. Once approved, PR will be merged
5. Your contribution appears in next release!

## Development Roadmap

We're actively working on:

- [ ] v2.0.2 (week 2-3) - Bug fixes
- [ ] v2.1.0 (month 2) - Image embedding, Google Sheets
- [ ] v3.0.0 (month 6+) - Cloud sync, mobile apps

Want to help? Check issues labeled:
- `good-first-issue` - Perfect for newcomers
- `help-wanted` - Explicitly requesting help
- `enhancement` - Feature requests

## Questions?

- 📖 Check [documentation](04_docs/)
- 💬 Join [discussions](../../discussions)
- 📧 Email support@snaglist.pro

## License

By contributing, you agree your code will be licensed under the same license as Snaglist Pro.

---

**Thank you for contributing to Snaglist Pro!**
