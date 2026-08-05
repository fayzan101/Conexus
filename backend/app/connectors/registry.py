from __future__ import annotations

from typing import Callable

from app.connectors.base import BaseConnector
from app.connectors.drive import GoogleDriveConnector
from app.connectors.email import GmailConnector, OutlookConnector
from app.connectors.github import GitHubConnector
from app.connectors.jira import JiraConnector
from app.connectors.slack import SlackConnector
from app.connectors.teams import TeamsConnector

ConnectorFactory = Callable[[], BaseConnector]

REGISTRY: dict[str, ConnectorFactory] = {
    "slack": SlackConnector,
    "github": GitHubConnector,
    "jira": JiraConnector,
    "google_drive": GoogleDriveConnector,
    "outlook": OutlookConnector,
    "gmail": GmailConnector,
    "teams": TeamsConnector,
}


def list_connectors() -> list[str]:
    return sorted(REGISTRY.keys())


def get_connector(name: str) -> BaseConnector:
    if name not in REGISTRY:
        raise KeyError(f"Unknown connector: {name}")
    return REGISTRY[name]()
