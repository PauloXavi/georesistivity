"""Streamlit interface for GeoResistivity.

Requires the ``app`` extra (``pip install "georesistivity[app]"``). Start it with
``georesistivity app``. Importing this package does not import Streamlit.
"""

from pathlib import Path

MAIN_SCRIPT = Path(__file__).with_name("main.py")
"""Script that ``streamlit run`` executes."""
