# GraphQL API (Phase 2)

GraphQL complements REST for flexible graph and dashboard queries.

## Endpoint

`POST /graphql` (authenticated)

## Schema Outline

```graphql
type User {
  id: ID!
  email: String!
  name: String
  roles: [Role!]!
}

type Document {
  id: ID!
  title: String!
  sourceSystem: String
  createdAt: DateTime!
  projects: [Project!]!
}

type Project {
  id: ID!
  name: String!
  documents: [Document!]!
  meetings: [Meeting!]!
  decisions: [Decision!]!
}

type Meeting {
  id: ID!
  title: String!
  occurredAt: DateTime
  summary: String
  decisions: [Decision!]!
  tasks: [Task!]!
}

type Decision {
  id: ID!
  title: String!
  status: String!
  owner: User
  approver: User
  evidence: [Document!]!
}

type Query {
  me: User
  search(query: String!, limit: Int = 10): [SearchResult!]!
  node(id: ID!): GraphNode
  project(id: ID!): Project
  decision(id: ID!): Decision
}

type Mutation {
  createChatSession: ChatSession!
  sendMessage(sessionId: ID!, content: String!): ChatMessage!
}
```

## Notes

- Enforce the same ACL filters as REST resolvers.  
- Avoid unbounded nested graph walks; require `depth` / `limit` arguments.  
- Prefer persisted queries for production clients.
