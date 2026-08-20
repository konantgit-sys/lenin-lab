# Contributing to Lenin-Lab

Thanks for your interest! This project is a serious digital-humanities
platform, and every contribution counts.

## Quick start

1. **Fork** the repo and clone it locally.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-timeout
   ```
3. Run the test suite:
   ```bash
   python3 -m pytest tests/ -v
   ```
   Without the 770 MB corpus DB the suite runs in CI mode (16 tests,
   DB-dependent tests auto-skip). With the full DB (`data/lenin.db`) all
   100 tests run.

## Reporting bugs

Open an issue using the **Bug report** template. Include:

- Expected vs actual behavior
- The exact request/endpoint (if API-related) or page (if site-related)
- Logs or error output
- Python version / OS

## Feature requests

Use the **Feature request** template. Describe the problem you are solving,
not just the feature — that helps us design the right solution.

## Pull requests

- Branch from `main` (`git checkout -b feat/your-feature`).
- Keep changes focused: one PR = one logical change.
- Run tests before pushing. New functionality must come with tests.
- Update `README.md` if user-facing behavior changed.
- PR description: what, why, how it was tested.

## Code style

- Python: PEP 8, no line over 120 chars.
- Keep engines independent — each engine has a single responsibility.
- Never hardcode absolute paths: use `os.environ.get("LENIN_*", <fallback>)`.
- No secrets in code, ever. Use env vars + `.env` locally.

## License

Code is **AGPL-3.0**. Data (corpus annotations, concept graph) is
**CC BY-NC-SA 4.0**. By contributing you agree to release your changes under
these licenses.
