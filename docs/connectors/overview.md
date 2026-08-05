# Data Connectors

## Purpose

Connectors synchronize enterprise systems into the ingestion pipeline with provenance, incremental sync, and ACL hints.

---

## Catalog

### Communication

| System | Phase |
|--------|-------|
| Slack | 2 |
| Microsoft Teams | 2 |
| Discord | 2+ |
| Zoom | 2+ |
| Google Meet | 2+ |

### Email

| System | Phase |
|--------|-------|
| Outlook | 2 |
| Gmail | 2 |

### Project Management

| System | Phase |
|--------|-------|
| Jira | 2 |
| Linear | 2+ |
| Asana | 2+ |
| Trello | 2+ |
| Azure DevOps | 2+ |

### Source Control

| System | Phase |
|--------|-------|
| GitHub | 2 |
| GitLab | 2+ |
| Bitbucket | 2+ |

### Knowledge Systems

| System | Phase |
|--------|-------|
| Confluence | 2+ |
| Notion | 2+ |
| Google Drive | 2 |
| SharePoint | 2+ |
| OneDrive | 2+ |

### CRM

| System | Phase |
|--------|-------|
| Salesforce | 3 |
| HubSpot | 3 |

### HR

| System | Phase |
|--------|-------|
| Workday | 3 |
| BambooHR | 3 |

### Storage

| System | Phase |
|--------|-------|
| S3 | 1 (backend storage) / 2 (customer buckets) |
| MinIO | 1 |
| Local Files | 1 (upload) |

### Business Systems

| System | Phase |
|--------|-------|
| SAP | 3+ |
| Oracle | 3+ |
| Dynamics | 3+ |

### Calendar

| System | Phase |
|--------|-------|
| Google Calendar | 2+ |
| Outlook Calendar | 2+ |

---

## Connector Contract

Each connector must implement:

| Capability | Description |
|------------|-------------|
| `authenticate` | OAuth / token / service account |
| `list` / `sync` | Incremental cursor or webhook |
| `fetch` | Normalize to canonical artifact schema |
| `acl_hints` | Map source permissions to EB principals when possible |
| `health` | Connectivity and lag metrics |
| `revoke` | Cleanup tokens and scheduled jobs |

### Canonical Artifact (simplified)

```json
{
  "tenant_id": "uuid",
  "source_system": "github",
  "source_id": "string",
  "source_uri": "https://...",
  "artifact_type": "document|message|issue|pr|email|meeting|file",
  "title": "string",
  "content_text": "string",
  "occurred_at": "ISO-8601",
  "authors": ["email_or_id"],
  "acl": {"principals": [], "visibility": "private|team|org"},
  "raw_ref": "s3://..."
}
```

---

## Phase 2 Priority Connectors

1. Slack  
2. Microsoft Teams  
3. GitHub  
4. Jira  
5. Google Drive  
6. Outlook  
7. Gmail  

These unlock Decision Memory, Project Memory, Timeline, Expert Discovery, and Knowledge Freshness with real enterprise signal density.
