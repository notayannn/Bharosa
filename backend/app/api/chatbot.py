from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_user, CurrentUser
from app.agents.chatbot import answer_query

router = APIRouter()


class ChatQuery(BaseModel):
    business_id: str
    question: str


@router.post("/ask")
def ask_chatbot(payload: ChatQuery, user: CurrentUser = Depends(get_current_user)):
    answer = answer_query(business_id=payload.business_id, question=payload.question)
    return {"answer": answer}