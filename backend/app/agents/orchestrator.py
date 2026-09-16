from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from app.agents.recon_agent import reconcile_payment, ReconciliationDecision


class ReconciliationFlowState(TypedDict):
    payment_id: str
    business_id: str
    decision: Optional[ReconciliationDecision]
    outcome: Optional[str]


def _reconcile_node(state: ReconciliationFlowState) -> ReconciliationFlowState:
    decision = reconcile_payment(
        payment_id=state["payment_id"], business_id=state["business_id"]
    )
    state["decision"] = decision
    return state


def _branch_on_decision(state: ReconciliationFlowState) -> str:
    return "owner_review" if state["decision"].requires_owner_review else "paid"


def _commit_paid_node(state: ReconciliationFlowState) -> ReconciliationFlowState:
    state["outcome"] = "paid"
    return state


def _owner_review_node(state: ReconciliationFlowState) -> ReconciliationFlowState:
    state["outcome"] = "owner_review"
    return state


_graph = StateGraph(ReconciliationFlowState)
_graph.add_node("reconcile", _reconcile_node)
_graph.add_node("commit_paid", _commit_paid_node)
_graph.add_node("owner_review", _owner_review_node)
_graph.set_entry_point("reconcile")
_graph.add_conditional_edges(
    "reconcile",
    _branch_on_decision,
    {"paid": "commit_paid", "owner_review": "owner_review"},
)
_graph.add_edge("commit_paid", END)
_graph.add_edge("owner_review", END)

_compiled_graph = _graph.compile()


def run_reconciliation_flow(payment_id: str, business_id: str) -> ReconciliationFlowState:
    """
    Entry point called by the payments upload route
    """
    initial_state: ReconciliationFlowState = {
        "payment_id": payment_id,
        "business_id": business_id,
        "decision": None,
        "outcome": None,
    }
    return _compiled_graph.invoke(initial_state)