from __future__ import annotations

from neo4j import GraphDatabase

from app.config import Settings


class GraphStore:
    def __init__(self, settings: Settings):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        self.default_tenant = settings.default_tenant_id

    def close(self) -> None:
        self.driver.close()

    def ping(self) -> bool:
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception:
            return False

    def upsert_node(self, label: str, node_id: str, properties: dict, *, tenant_id: str | None = None) -> None:
        tid = tenant_id or properties.get("tenant_id") or self.default_tenant
        props = {**properties, "id": node_id, "tenant_id": tid}
        cypher = (
            f"MERGE (n:{label} {{id: $id, tenant_id: $tenant_id}}) "
            "SET n += $props RETURN n"
        )
        with self.driver.session() as session:
            session.run(cypher, id=node_id, tenant_id=tid, props=props)

    def upsert_edge(
        self,
        from_label: str,
        from_id: str,
        to_label: str,
        to_id: str,
        rel_type: str,
        *,
        tenant_id: str | None = None,
    ) -> None:
        tid = tenant_id or self.default_tenant
        cypher = (
            f"MERGE (a:{from_label} {{id: $from_id, tenant_id: $tenant_id}}) "
            f"MERGE (b:{to_label} {{id: $to_id, tenant_id: $tenant_id}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) SET r.tenant_id = $tenant_id RETURN r"
        )
        with self.driver.session() as session:
            session.run(cypher, from_id=from_id, to_id=to_id, tenant_id=tid)

    def get_node(self, node_id: str, *, tenant_id: str | None = None) -> dict | None:
        tid = tenant_id or self.default_tenant
        with self.driver.session() as session:
            result = session.run(
                "MATCH (n {id: $id, tenant_id: $tenant_id}) "
                "RETURN labels(n) AS labels, properties(n) AS props",
                id=node_id,
                tenant_id=tid,
            )
            record = result.single()
            if not record:
                return None
            labels = record["labels"]
            return {
                "id": node_id,
                "label": labels[0] if labels else "Node",
                "properties": dict(record["props"]),
            }

    def neighbors(self, node_id: str, limit: int = 50, *, tenant_id: str | None = None) -> list[dict]:
        tid = tenant_id or self.default_tenant
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (n {id: $id, tenant_id: $tenant_id})-[r]-(m)
                WHERE coalesce(m.tenant_id, $tenant_id) = $tenant_id
                RETURN labels(m) AS labels, properties(m) AS props, type(r) AS rel
                LIMIT $limit
                """,
                id=node_id,
                tenant_id=tid,
                limit=limit,
            )
            out = []
            for record in result:
                labels = record["labels"]
                props = dict(record["props"])
                out.append(
                    {
                        "id": props.get("id", ""),
                        "label": labels[0] if labels else "Node",
                        "properties": {**props, "via": record["rel"]},
                    }
                )
            return out

    def search(
        self,
        label: str | None,
        name: str | None,
        limit: int = 20,
        *,
        tenant_id: str | None = None,
    ) -> list[dict]:
        tid = tenant_id or self.default_tenant
        if label and name:
            cypher = (
                f"MATCH (n:{label}) WHERE n.tenant_id = $tenant_id AND ("
                "toLower(n.name) CONTAINS toLower($name) "
                "OR toLower(n.title) CONTAINS toLower($name)) "
                "RETURN labels(n) AS labels, properties(n) AS props LIMIT $limit"
            )
            params = {"name": name, "limit": limit, "tenant_id": tid}
        elif label:
            cypher = (
                f"MATCH (n:{label}) WHERE n.tenant_id = $tenant_id "
                "RETURN labels(n) AS labels, properties(n) AS props LIMIT $limit"
            )
            params = {"limit": limit, "tenant_id": tid}
        elif name:
            cypher = (
                "MATCH (n) WHERE n.tenant_id = $tenant_id AND ("
                "toLower(coalesce(n.name, '')) CONTAINS toLower($name) "
                "OR toLower(coalesce(n.title, '')) CONTAINS toLower($name)) "
                "RETURN labels(n) AS labels, properties(n) AS props LIMIT $limit"
            )
            params = {"name": name, "limit": limit, "tenant_id": tid}
        else:
            cypher = (
                "MATCH (n) WHERE n.tenant_id = $tenant_id "
                "RETURN labels(n) AS labels, properties(n) AS props LIMIT $limit"
            )
            params = {"limit": limit, "tenant_id": tid}

        with self.driver.session() as session:
            result = session.run(cypher, **params)
            out = []
            for record in result:
                labels = record["labels"]
                props = dict(record["props"])
                out.append(
                    {
                        "id": props.get("id", ""),
                        "label": labels[0] if labels else "Node",
                        "properties": props,
                    }
                )
            return out

    def path(
        self,
        from_id: str,
        to_id: str,
        max_depth: int = 3,
        *,
        tenant_id: str | None = None,
    ) -> list[dict]:
        tid = tenant_id or self.default_tenant
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH p = shortestPath(
                  (a {id: $from_id, tenant_id: $tenant_id})-[*1..%d]-
                  (b {id: $to_id, tenant_id: $tenant_id})
                )
                WHERE all(n IN nodes(p) WHERE coalesce(n.tenant_id, $tenant_id) = $tenant_id)
                RETURN [n IN nodes(p) | {id: n.id, labels: labels(n), props: properties(n)}] AS nodes
                """
                % max_depth,
                from_id=from_id,
                to_id=to_id,
                tenant_id=tid,
            )
            record = result.single()
            if not record:
                return []
            nodes = []
            for n in record["nodes"]:
                labels = n["labels"]
                props = dict(n["props"])
                nodes.append(
                    {
                        "id": n["id"],
                        "label": labels[0] if labels else "Node",
                        "properties": props,
                    }
                )
            return nodes

    def delete_node(self, node_id: str, *, tenant_id: str | None = None) -> None:
        tid = tenant_id or self.default_tenant
        with self.driver.session() as session:
            session.run(
                "MATCH (n {id: $id, tenant_id: $tenant_id}) DETACH DELETE n",
                id=node_id,
                tenant_id=tid,
            )
