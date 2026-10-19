import pytest

from app.calculator import calculate_future_value


def test_cagr_formula_matches_assignment_inputs():
    assert calculate_future_value(4.21 * 0.38, 0.112, 6) == pytest.approx(3.0, abs=0.03)


def test_calculator_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        calculate_future_value(-1, 0.1, 3)
