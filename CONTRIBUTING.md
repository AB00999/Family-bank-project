# Contributing to Family Bank Project

Thank you for your interest in contributing to the Family Bank Project! This is an educational project built for learning web development, cybersecurity, and software engineering best practices.

## About This Project

This is a **learning/portfolio project**, not a real banking system. It demonstrates:
- Web application development with Flask
- Security best practices (password hashing, CSRF protection)
- Database design with SQLite
- Python scripting and CLI tools
- Test-driven development
- GitHub collaboration

## Getting Started

### Prerequisites
- Python 3.8+
- Git
- Virtual environment (recommended)

### Setup Development Environment

1. **Clone the repository**
   ```bash
   git clone https://github.com/AB00999/Family-bank-project.git
   cd Family-bank-project
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run tests**
   ```bash
   python -m unittest discover -s tests -v
   ```

5. **Run the application**
   ```bash
   python app.py
   ```
   Open http://127.0.0.1:5000 in your browser

## How to Contribute

### Types of Contributions
- **Bug Reports**: Found an issue? Create an issue on GitHub
- **Feature Requests**: Have an idea? Open an issue to discuss
- **Code Improvements**: Submit pull requests for bug fixes or enhancements
- **Documentation**: Improve README, add examples, fix typos
- **Tests**: Add test coverage for edge cases

### Contribution Process

1. **Fork the repository**
   ```bash
   git clone https://github.com/YOUR-USERNAME/Family-bank-project.git
   cd Family-bank-project
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

3. **Make your changes**
   - Write clean, readable code
   - Follow Python PEP 8 style guide
   - Add tests for new features
   - Update documentation as needed

4. **Run tests locally**
   ```bash
   python -m unittest discover -s tests -v
   ```

5. **Commit with clear messages**
   ```bash
   git commit -m "feat: Add new feature description"
   # or
   git commit -m "fix: Fix bug description"
   git commit -m "docs: Update documentation"
   git commit -m "test: Add tests for feature"
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request**
   - Go to the main repository
   - Click "New Pull Request"
   - Describe your changes
   - Link any related issues

## Code Style Guidelines

### Python
- Follow PEP 8
- Use meaningful variable names
- Add docstrings to functions
- Keep lines under 100 characters
- Use type hints where applicable

### Git Commits
- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit subject line to 50 characters
- Reference issues when applicable (#123)

### Testing
- Write tests for all new features
- Maintain or improve test coverage
- Tests should be isolated and repeatable
- Use descriptive test names

## Project Structure

```
Family-bank-project/
├── app.py                 # Main Flask application
├── atm.py                # ATM simulator
├── login_checker.py      # Standalone login tool
├── requirements.txt      # Python dependencies
├── templates/            # HTML templates
├── static/              # CSS, JavaScript, images
├── tests/               # Unit tests
├── docs/                # Documentation
└── README.md
```

## Common Tasks

### Add a new feature
1. Create test file: `tests/test_feature.py`
2. Write failing tests
3. Implement feature in `app.py` or new module
4. Make tests pass
5. Update README if needed
6. Create pull request

### Fix a bug
1. Write test that reproduces bug
2. Implement fix
3. Ensure test passes
4. Check no other tests break
5. Update README if needed
6. Create pull request with "fix:" prefix

### Improve documentation
1. Edit relevant `.md` file
2. Check formatting looks correct
3. Commit with "docs:" prefix
4. Create pull request

## Security Considerations

This is a **learning project**. Please:
- Do NOT use real passwords or personal data
- Do NOT deploy to public internet without security review
- DO report security vulnerabilities privately to the maintainer
- DO NOT commit API keys, passwords, or secrets

## Testing

All contributions must pass tests:

```bash
# Run all tests
python -m unittest discover -s tests -v

# Run specific test file
python -m unittest tests.test_booking

# Run with coverage
pip install coverage
coverage run -m unittest discover -s tests
coverage report
```

## Questions?

- Open an issue to ask questions
- Check existing issues and discussions first
- Reference documentation in README.md

## Code of Conduct

- Be respectful and inclusive
- Welcome different opinions and experiences
- Focus on what is best for the community
- Show empathy to other community members
- Be patient with learning contributors

## Recognition

Contributors will be:
- Thanked in commit messages
- Listed in README contributors section
- Recognized for their efforts

Thank you for contributing! 🙏

---

**Created by**: Abdoul Sawadogo  
**Last Updated**: November 2026
