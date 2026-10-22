"""Compatibility entry point for ``streamlit run app/app.py``.

The interface lives in :mod:`georesistivity.app.main`. Prefer ``georesistivity app``, which
works from any directory once the package is installed with the ``app`` extra.
"""

from georesistivity.app.main import main

main()
