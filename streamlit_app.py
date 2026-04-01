"""Thin Streamlit entrypoint for the PRML VSLAM metrics app.

The file stays intentionally tiny so that all application structure remains inside the
installable package. Streamlit executes this script directly, and it simply forwards
control to the packaged `run_app()` bootstrap function.
"""

from prml_vslam.app import run_app

run_app()
