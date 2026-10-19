import math


def calculate_future_value(base_value: float, annual_rate: float, years: int) -> float:
    if not math.isfinite(base_value) or base_value < 0:
        raise ValueError("base_value must be a finite, non-negative number")
    if not math.isfinite(annual_rate) or annual_rate <= -1:
        raise ValueError("annual_rate must be finite and greater than -1")
    if years < 0 or years > 100:
        raise ValueError("years must be between 0 and 100")
    return base_value * math.pow(1 + annual_rate, years)
