from __future__ import annotations


class MissingParamsError(ValueError):
    """A model cannot run on a material because material constants are missing."""

    def __init__(self, model: str, missing, hint: str = ""):
        self.model, self.missing = model, sorted(missing)
        msg = f"Missing required material params for {model}: {self.missing}"
        super().__init__(msg + (f". {hint}" if hint else ""))


class NativeLifeError(ValueError):
    """A model's native life law cannot be fitted on this material (its damage values still can)."""
