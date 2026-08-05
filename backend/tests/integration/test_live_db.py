import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skip(reason="Enable with LIVE_DB=1 and Neon credentials for integration runs")
def test_neon_placeholder():
    assert True
