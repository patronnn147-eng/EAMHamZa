@echo off
echo Installing pre-commit...
pip install pre-commit
pre-commit install
echo.
echo Done. Hooks will now run automatically on every git commit.
