"""Test de humo: verifica que el paquete y las dependencias clave importan."""

import importlib

import pytest


@pytest.mark.parametrize("module", ["src.data", "src.merton", "src.analysis"])
def test_project_modules_import(module: str) -> None:
    """Los módulos del proyecto deben poder importarse."""
    importlib.import_module(module)


@pytest.mark.parametrize("module", ["pandas", "numpy", "scipy", "yfinance", "plotly", "streamlit"])
def test_dependencies_import(module: str) -> None:
    """Las dependencias de requirements.txt deben estar instaladas."""
    importlib.import_module(module)
