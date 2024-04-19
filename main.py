import logging
import openai
from query_interface.chat_utils import ask
from query_interface.chat_utils import ask_with_flur
from secrets import OPENAI_API_KEY
from fastapi import FastAPI, Response, Request
from starlette.background import BackgroundTask
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import json
import uvicorn

# if __name__ == "__main__":
#     while True:
#         user_query = input("Enter your question: ")
#         logging.basicConfig(level=logging.WARNING,
#                             format="%(asctime)s %(levelname)s %(message)s")
#         print(ask(user_query))


class Event(BaseModel):
    name: str


class NodesVisitedItem(BaseModel):
    dialog_node: str
    title: str
    conditions: str


class Source(BaseModel):
    dialog_node: str
    title: str
    condition: str


class TurnEvent(BaseModel):
    event: str
    source: Source


class Debug(BaseModel):
    nodes_visited: List[NodesVisitedItem]
    turn_events: List[TurnEvent]
    log_messages: List
    branch_exited: bool
    branch_exited_reason: str


class Intent(BaseModel):
    intent: str
    confidence: float
    skill: str


class Metadata(BaseModel):
    numeric_value: int


class Interpretation(BaseModel):
    numeric_value: int
    subtype: str


class Entity(BaseModel):
    entity: str
    location: List[int]
    value: str
    confidence: int
    metadata: Metadata
    interpretation: Interpretation
    skill: str


class GenericItem(BaseModel):
    response_type: str
    text: str


class IBMOutput(BaseModel):
    debug: Any
    intents: Any
    entities: Any
    generic: List[GenericItem]


class System(BaseModel):
    session_start_time: str
    user_id: str
    turn_count: int
    state: str


class Global(BaseModel):
    system: Any
    session_id: str

class ChatInput(BaseModel):
    flur: str
    flstnrzae: str
    question: str

class UserDefined(BaseModel):
    flur: str
    error: Any | None = None
    flstnrzae: str
    apiinput: ChatInput
    question: str


class System1(BaseModel):
    state: str


class MainSkill(BaseModel):
    user_defined: UserDefined
    system: Any


class Skills(BaseModel):
    main_skill: MainSkill = Field(..., alias='main skill')
    actions_skill: Any = Field(default=None, alias='actions skill')

class IBMContext(BaseModel):
    global_: Global = Field(..., alias='global')
    integrations: Any | None = None
    skills: Skills


class IBMPayload(BaseModel):
    output: IBMOutput
    user_id: str
    context: IBMContext


class IBMChatInput(BaseModel):
    event: Event
    options: Dict[str, Any]
    payload: IBMPayload


app = FastAPI()
#app.answer = ''
# logging.basicConfig(filename='info.log', level=logging.DEBUG)

# def log_info(req_body, res_body):
#     logging.info(req_body)
#     logging.info(res_body)

# @app.middleware('http')
# async def some_middleware(request: Request, call_next):
#     req_body = await request.body()
#     print(req_body)
#
#     response = await call_next(request.body)
#
#     res_body = b''
#     async for chunk in response.body_iterator:
#         res_body += chunk
#
#     #task = BackgroundTask(log_info, req_body, res_body)
#     #print(res_body)
#     return Response(content=res_body, status_code=response.status_code,
#                     headers=dict(response.headers), media_type=response.media_type)



@app.post("/chat/")
async def ask_chat(item: ChatInput):
    #logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    res = str(ask_with_flur(item))
    return {"message": res}

@app.post("/chatIBM/")
async def ask_chat(item: IBMChatInput):
    print("before the main function")
    res = str(ask_with_flur(item.payload.context.skills.main_skill.user_defined.apiinput))
    #app.answer = res
    print("after the main function")
    item.payload.output.generic[0].response_type = "text"
    item.payload.output.generic[0].text = res
    #ibm_res = '{ body : { payload : { output : { generic : [ { "response_type": "text", "text": ' + res + ', y\'all. } ], }, }, }, }'
    return item

# @app.post("/chatBackendIBM/")
# async def ask_chat(item: ChatInput):
#     answer_local = app.answer
#     app.answer = ''
#     if answer_local != '':
#         return answer_local
#     else:
#         return ''
