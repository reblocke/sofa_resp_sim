from __future__ import annotations

import pytest

streamlit_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = streamlit_testing.AppTest


def test_applet_initial_render_is_clean() -> None:
    at = AppTest.from_string(
        "from sofa_resp_sim.web.applet_streamlit import main\n\nmain()\n"
    )
    at.run()

    assert not at.exception
    assert at.title[0].value == "Respiratory SOFA Simulation Applet"
