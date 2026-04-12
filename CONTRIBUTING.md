# Contributing to OpenZues

OpenZues is in active alpha, so the best contributions are the ones that make the control plane more reliable,
clearer to operate, and easier to recover when a run goes sideways.

## Before you start

- Read the current [README](README.md) first so the project scope and current gaps are clear.
- Prefer an issue or short discussion before starting large product-direction changes.
- Keep pull requests focused. Smaller verified slices are easier to review, revert, and checkpoint.

## Good contribution targets

- operator UX improvements
- approval and checkpoint reliability
- dashboard clarity and diagnostics
- setup and onboarding hardening
- mission continuity, routing, and recovery
- documentation, examples, and reproducible bug reports

## Development setup

1. Create a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install the project:

   ```powershell
   pip install -e .[dev]
   ```

3. Run the app locally:

   ```powershell
   openzues --reload
   ```

## Validation

Run the checks that match the surface you changed. For most Python changes, that means:

```powershell
ruff check .
pytest
mypy src
```

If you change UI or workflow behavior, include the exact validation steps you used in the PR description.

## Pull request guidelines

- Explain the user-facing problem first, then the implementation.
- Add or update tests for behavior changes whenever practical.
- Keep docs in sync with product behavior.
- Do not commit local runtime databases, screenshots, `.tmp-*` artifacts, or machine-specific debug files.
- If a change affects approvals, autonomy, or destructive actions, call out the safety tradeoff explicitly.

## Scope and honesty

OpenZues is ambitious, but it is still an alpha. Please avoid marketing-level claims in docs or UI that imply
capabilities we have not actually shipped yet. It is better to be specific and trustworthy than broad and vague.
