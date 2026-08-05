from fastapi import APIRouter, HTTPException

from app.deps import AppSettings, CurrentUser
from app.schemas import (
    GraphNeighborResponse,
    GraphNodeOut,
    GraphPathRequest,
    GraphSearchRequest,
)
from app.services.graph import GraphStore

router = APIRouter(prefix="/v1/graph", tags=["graph"])


@router.get("/nodes/{node_id}", response_model=GraphNodeOut)
def get_node(node_id: str, settings: AppSettings, _: CurrentUser):
    store = GraphStore(settings)
    try:
        node = store.get_node(node_id)
    finally:
        store.close()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return GraphNodeOut(**node)


@router.get("/nodes/{node_id}/neighbors", response_model=GraphNeighborResponse)
def get_neighbors(node_id: str, settings: AppSettings, _: CurrentUser):
    store = GraphStore(settings)
    try:
        node = store.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        neighbors = store.neighbors(node_id)
    finally:
        store.close()
    return GraphNeighborResponse(
        node=GraphNodeOut(**node),
        neighbors=[GraphNodeOut(**n) for n in neighbors],
    )


@router.post("/search", response_model=list[GraphNodeOut])
def search_nodes(payload: GraphSearchRequest, settings: AppSettings, _: CurrentUser):
    store = GraphStore(settings)
    try:
        nodes = store.search(payload.label, payload.name, payload.limit)
    finally:
        store.close()
    return [GraphNodeOut(**n) for n in nodes]


@router.post("/path", response_model=list[GraphNodeOut])
def path_nodes(payload: GraphPathRequest, settings: AppSettings, _: CurrentUser):
    store = GraphStore(settings)
    try:
        nodes = store.path(payload.from_id, payload.to_id, payload.max_depth)
    finally:
        store.close()
    return [GraphNodeOut(**n) for n in nodes]
