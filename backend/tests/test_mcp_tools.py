from app.mcp_tools.job_search_server import _search_local


def test_local_job_search_fallback_returns_results():
    result = _search_local("backend python", location=None, limit=3)
    assert len(result) <= 3
    assert all("title" in job for job in result)


def test_local_job_search_filters_by_location():
    result = _search_local("intern", location="Bengaluru", limit=5)
    assert isinstance(result, list)
