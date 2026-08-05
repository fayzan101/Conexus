from app.connectors.base import ConnectorAuthError
from app.connectors.github import GitHubConnector
from app.connectors.jira import JiraConnector
from app.connectors.registry import get_connector, list_connectors
from app.connectors.slack import SlackConnector


def test_registry_lists_priority_connectors():
    providers = list_connectors()
    for name in ["slack", "github", "jira", "google_drive", "outlook", "gmail", "teams"]:
        assert name in providers


def test_slack_normalize_and_sync():
    conn = SlackConnector()
    try:
        conn.authenticate({})
        assert False, "expected auth error"
    except ConnectorAuthError:
        pass

    conn.authenticate(
        {
            "access_token": "xoxb-test",
            "messages": [
                {"ts": "1710000000.1", "channel": "eng", "text": "Ship Project Phoenix", "user": "U1"},
                {"ts": "1710000001.1", "channel": "eng", "text": "Follow up", "user": "U2"},
            ],
        }
    )
    result = conn.sync(limit=1)
    assert len(result.artifacts) == 1
    assert result.artifacts[0].source_system == "slack"
    assert result.next_cursor == "1"
    art = SlackConnector.normalize_message(
        {"ts": "1.0", "channel": "general", "text": "hello", "user": "U"}
    )
    assert art.artifact_type == "message"
    assert "hello" in art.content_text


def test_github_and_jira_normalize():
    gh = GitHubConnector.normalize_item(
        {
            "type": "pull_request",
            "number": 12,
            "title": "Add connectors",
            "body": "phase 2",
            "html_url": "https://github.com/x/y/pull/12",
            "user": {"login": "dev"},
            "created_at": "2026-01-01T00:00:00Z",
        }
    )
    assert gh.artifact_type == "pr"
    assert gh.authors == ["dev"]

    jira = JiraConnector.normalize_issue(
        {
            "key": "EB-1",
            "fields": {"summary": "Wire Slack", "description": "do it", "created": "2026-01-02T00:00:00Z"},
        }
    )
    assert jira.source_id == "EB-1"
    assert "Wire Slack" in jira.title


def test_get_connector_unknown():
    try:
        get_connector("sap")
        assert False
    except KeyError:
        pass
