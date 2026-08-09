from __future__ import annotations

from neo4j import GraphDatabase

from app.config import Settings


class GraphStore:
    def __init__(self, settings: Settings):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def close(self) -> None:
        self.driver.close()

    def ping(self) -> bool:
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception:
            return False

    def upsert_node(self, label: str, node_id: str, properties: dict) -> None:
        props = {**properties, "id": node_id}
        cypher = f"MERGE (n:{label} {{id: $id}}) SET n += $props RETURN n"
        with self.driver.session() as session:
            session.run(cypher, id=node_id, props=props)

    def upsert_edge(
        self,
        from_label: str,
        from_id: str,
        to_label: str,
        to_id: str,
        rel_type: str,
    ) -> None:
        cypher = (
            f"MERGE (a:{from_label} {{id: $from_id}}) "
            f"MERGE (b:{to_label} {{id: $to_id}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) RETURN r"
        )
        with self.driver.session() as session:
            session.run(cypher, from_id=from_id, to_id=to_id)

    def get_node(self, node_id: str) -> dict | None:
        with self.driver.session() as session:
            result = session.run(
                "MATCH (n {id: $id}) RETURN labels(n) AS labels, properties(n) AS props",
                id=node_id,
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

    def neighbors(self, node_id: str, limit: int = 50) -> list[dict]:
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (n {id: $id})-[r]-(m)
                RETURN labels(m) AS labels, properties(m) AS props, type(r) AS rel
                LIMIT $limit
                """,
                id=node_id,
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

    def search(self, label: str | None, name: str | None, limit: int = 20) -> list[dict]:
        if label and name:
            cypher = (
                f"MATCH (n:{label}) WHERE toLower(n.name) CONTAINS toLower($name) "
                "OR toLower(n.title) CONTAINS toLower($name) "
                "RETURN labels(n) AS labels, properties(n) AS props LIMIT $limit"
            )
            params = {"name": name, "limit": limit}
        elif label:
            cypher = f"MATCH (n:{label}) RETURN labels(n) AS labels, properties(n) AS props LIMIT $limit"
            params = {"limit": limit}
        elif name:
            cypher = (
                "MATCH (n) WHERE toLower(coalesce(n.name, '')) CONTAINS toLower($name) "
                "OR toLower(coalesce(n.title, '')) CONTAINS toLower($name) "
                "RETURN labels(n) AS labels, properties(n) AS props LIMIT $limit"
            )
            params = {"name": name, "limit": limit}
        else:
            cypher = "MATCH (n) RETURN labels(n) AS labels, properties(n) AS props LIMIT $limit"
            params = {"limit": limit}

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

    def path(self, from_id: str, to_id: str, max_depth: int = 3) -> list[dict]:
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH p = shortestPath((a {id: $from_id})-[*1..%d]-(b {id: $to_id}))
                RETURN [n IN nodes(p) | {id: n.id, labels: labels(n), props: properties(n)}] AS nodes
                """
                % max_depth,
                from_id=from_id,
                to_id=to_id,
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

    def delete_node(self, node_id: str) -> None:
        with self.driver.session() as session:
            session.run("MATCH (n {id: $id}) DETACH DELETE n", id=node_id)
