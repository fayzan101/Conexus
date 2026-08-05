import json
from pathlib import Path
from unittest.mock import patch

from app.connectors.security import verify_github_signature, verify_slack_signature, with_backoff
from app.connectors.slack import SlackConnector, slack_oauth_authorize_url
from app.connectors.github import GitHubConnector, github_oauth_authorize_url
from app.config import Settings

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "connectors"


def test_slack_and_github_signature_verification():
    body = b'{"type":"event_callback"}'
    secret = "signing-secret"
    ts = "1710000000"
    # Fix time window by patching time.time
    with patch("app.connectors.security.time.time", return_value=1710000000):
        from app.connectors.security import verify_slack_signature as vss
        import hashlib
        import hmac

        basestring = f"v0:{ts}:{body.decode()}"
        sig = "v0=" + hmac.new(secret.encode(), basestring.encode(), hashlib.sha256).hexdigest()
        assert vss(signing_secret=secret, timestamp=ts, body=body, signature=sig)
        assert not vss(signing_secret=secret, timestamp=ts, body=body, signature="v0=bad")

    gh_sig = "sha256=" + __import__("hmac").new(b"gh-secret", body, __import__("hashlib").sha256).hexdigest()
    assert verify_github_signature(secret="gh-secret", body=body, signature_header=gh_sig)
    assert not verify_github_signature(secret="gh-secret", body=body, signature_header="sha256=nope")


def test_oauth_authorize_urls():
    settings = Settings(
        slack_client_id="slack-id",
        github_client_id="gh-id",
        api_base_url="http://localhost:8000",
        environment="test",
        auth_provider="dev",
    )
    slack_url = slack_oauth_authorize_url(settings, state="abc")
    assert "slack.com/oauth" in slack_url
    assert "client_id=slack-id" in slack_url
    gh_url = github_oauth_authorize_url(settings, state="xyz")
    assert "github.com/login/oauth/authorize" in gh_url


def test_recorded_fixture_sync_contracts():
    slack_payload = json.loads((FIXTURES / "slack_history.json").read_text(encoding="utf-8"))
    gh_payload = json.loads((FIXTURES / "github_issues.json").read_text(encoding="utf-8"))

    slack = SlackConnector()
    slack.authenticate({"access_token": "xoxb", "messages": slack_payload["messages"]})
    sres = slack.sync(limit=10)
    assert sres.stats["mode"] == "fixture"
    assert len(sres.artifacts) == len(slack_payload["messages"])

    gh = GitHubConnector()
    gh.authenticate({"access_token": "ghp", "items": gh_payload})
    gres = gh.sync(limit=10)
    assert gres.stats["mode"] == "fixture"
    assert len(gres.artifacts) >= 1


def test_backoff_retries_rate_limit():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            from app.connectors.security import RateLimitError

            raise RateLimitError(0.01)
        return "ok"

    assert with_backoff(flaky, retries=4, base_delay=0.01) == "ok"
    assert calls["n"] == 3
