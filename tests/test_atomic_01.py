"""Failing tests for atomic-01 Calculator class."""

import pytest


def test_add_returns_sum():
    from src.calculator import Calculator

    calculator = Calculator()
    assert calculator.add(2, 3) == 5


def test_subtract_returns_difference():
    from src.calculator import Calculator

    calculator = Calculator()
    assert calculator.subtract(5, 3) == 2


def test_multiply_returns_product():
    from src.calculator import Calculator

    calculator = Calculator()
    assert calculator.multiply(4, 3) == 12


def test_divide_returns_quotient():
    from src.calculator import Calculator

    calculator = Calculator()
    assert calculator.divide(8, 2) == 4
