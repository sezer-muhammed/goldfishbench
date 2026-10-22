"""GoldfishBench's offline scorer. No API clients or network calls."""

from .data import load_rows, model_input, validate_rows
from .metrics import score_predictions

__all__ = ["load_rows", "model_input", "validate_rows", "score_predictions"]
__version__ = "1.0.0"
