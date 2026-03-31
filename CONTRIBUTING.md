# Contributing to mcp-datovka

## Development setup

```bash
git clone https://github.com/Sensio-cz/mcp-datovka.git
cd mcp-datovka
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
pytest --cov=mcp_datovka  # with coverage
```

## Code style

- Python 3.11+ type hints
- Keep it simple - this is a small focused project (~700 LOC)
- Follow existing patterns in the codebase

## Pull requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Write tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Submit a pull request

## Reporting issues

Use [GitHub Issues](https://github.com/Sensio-cz/mcp-datovka/issues). Include:
- Python version
- mcp-datovka version
- Error message / traceback
- Steps to reproduce

## Security vulnerabilities

See [SECURITY.md](SECURITY.md) for reporting security issues.
