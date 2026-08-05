# Functional Modules Overview

Enterprise Brain is delivered as fifteen modules. MVP ships a subset; later phases unlock the full platform.

| # | Module | MVP | Phase 2 | Phase 3 |
|---|--------|-----|---------|---------|
| 1 | Enterprise Knowledge Graph | Basic | Advanced | Advanced |
| 2 | Meeting Memory | Transcript ingest | Live / full extract | Enrichment |
| 3 | Decision Intelligence | Basic nodes | Full | Analytics |
| 4 | Company Timeline | — | Yes | Yes |
| 5 | Project Memory | Partial | Yes | Yes |
| 6 | Expertise Discovery | — | Yes | Yes |
| 7 | Knowledge Freshness | — | Yes | Yes |
| 8 | Business Dependency Graph | — | Partial | Yes |
| 9 | Enterprise Search | Semantic + chat | Advanced | Advanced |
| 10 | AI Research Agent | — | — | Yes |
| 11 | Opportunity Discovery | — | — | Yes |
| 12 | Workflow Intelligence | — | — | Yes |
| 13 | Predictive Analytics | — | — | Yes |
| 14 | Enterprise AI Assistant | Core chat | Rich context | Multi-agent |
| 15 | Executive Dashboard | Basic ops | Knowledge KPIs | Full exec |

---

## Module 1 – Enterprise Knowledge Graph

**Purpose:** Unified representation of organizational knowledge.

**Features:** Graph visualization, relationship discovery, automatic linking, entity resolution, duplicate detection, graph search.

---

## Module 2 – Meeting Memory

**Capabilities:** Live transcription, AI summaries, action items, decisions, speaker ID, tagging, linked projects, follow-up reminders.

**Outputs:** Transcript, Summary, Decisions, Risks, Open Questions, Tasks, Referenced Documents.

---

## Module 3 – Decision Intelligence

Every decision stores: Decision, Owner, Approver, Date, Context, Evidence, Alternatives, Expected Outcome, Status, Expiration Date.

**Example queries:**

- Why was Kubernetes adopted?  
- Who approved pricing changes?  
- Which assumptions proved incorrect?  

---

## Module 4 – Company Timeline

Chronological organizational memory: projects, funding, hiring, incidents, launches, policy changes, architecture changes, security events, mergers, releases.

---

## Module 5 – Project Memory

Automatically captures requirements, meetings, designs, architecture, code, issues, releases, lessons learned, retrospectives.

---

## Module 6 – Expertise Discovery

Signals: git history, meetings, tickets, docs, code reviews, presentations, internal discussions.

**Returns:** Expert ranking, confidence, evidence, availability.

---

## Module 7 – Knowledge Freshness

Continuous scores: freshness, trust, completeness, risk, ownership, duplicate likelihood, suggested updates.

---

## Module 8 – Business Dependency Graph

Maps customers, products, infrastructure, services, databases, APIs, teams, engineers, vendors, applications.

Supports impact analysis and change planning.

---

## Module 9 – Enterprise Search

Natural language examples:

- Who approved Project Phoenix?  
- Find GDPR discussions.  
- Why was Feature X removed?  
- Show invoices related to Customer ABC.  
- Who solved similar outages?  
- What APIs depend on Service Y?  

---

## Module 10 – AI Research Agent

```
Problem → Collect Evidence → Analyze → Detect Patterns
→ Identify Root Cause → Generate Recommendations → Executive Report
```

---

## Module 11 – Opportunity Discovery

Detects repeated complaints, missing features, customer demand, revenue opportunities, product ideas, process inefficiencies, documentation gaps.

---

## Module 12 – Workflow Intelligence

Observes work patterns; finds repetitive workflows; suggests automation, approvals, notifications, AI agents, RPA opportunities.

---

## Module 13 – Predictive Analytics

Predicts project delays, budget overruns, employee overload, knowledge loss, documentation decay, customer churn, operational risks.

---

## Module 14 – Enterprise AI Assistant

Capabilities: Q&A, reasoning, summarization, recommendations, cross-system analysis, timeline generation, decision reconstruction, evidence-backed responses.

Each answer contains: confidence, sources, related documents, related projects, people involved, timeline, supporting evidence.

---

## Module 15 – Executive Dashboard

**KPIs:** Knowledge Health, Decision Velocity, Project Risks, Team Capacity, Expert Availability, Knowledge Growth, Knowledge Loss Risk, Customer Trends, Automation Opportunities, Operational Efficiency.

---

## Deeper Specs

- [mvp-modules.md](mvp-modules.md) — MVP module acceptance criteria  
- [../architecture/data-model.md](../architecture/data-model.md) — graph schema  
- [../roadmap/phases.md](../roadmap/phases.md) — delivery phases
