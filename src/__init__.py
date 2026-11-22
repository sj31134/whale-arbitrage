"""Expose shared investor libraries to domain modules imported from the repository root."""
from pathlib import Path

__path__.append(str(Path(__file__).resolve().parents[1] / "branch" / "investor_agent" / "src"))
