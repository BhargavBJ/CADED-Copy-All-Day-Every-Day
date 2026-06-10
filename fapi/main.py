from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from markdown import markdown

from fapi.llm import get_response

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key="change-this-to-a-long-random-secret-key"
)

templates = Jinja2Templates(directory="fapi/templates")

@app.get("/")
def home(request: Request):

    if "chat_history" not in request.session:
        request.session["chat_history"] = []

    rendered_messages = []

    for msg in request.session["chat_history"]:

        content = msg["content"]

        if msg["role"] == "assistant":
            content = markdown(
                content,
                extensions=["fenced_code", "tables", "nl2br"]
            )

        rendered_messages.append({
            "role": msg["role"],
            "content": content
        })

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"messages": rendered_messages}
    )

@app.post("/chat")
def chat(
    request: Request,
    prompt: str = Form(...),
    image_base64: str = Form(None)
):

    if "chat_history" not in request.session:
        request.session["chat_history"] = []

    history = request.session["chat_history"]

    conversation = []

    for msg in history:
        if msg["role"] == "user":
            conversation.append(("user", msg["content"]))
        elif msg["role"] == "assistant":
            conversation.append(("assistant", msg["content"]))

    conversation.append(("user", prompt))

    answer = get_response(
        conversation,
        image_base64=image_base64
    )

    history.append({
        "role": "user",
        "content": prompt
    })

    history.append({
        "role": "assistant",
        "content": answer
    })

    request.session["chat_history"] = history

    rendered_messages = []

    for msg in history:

        content = msg["content"]

        if msg["role"] == "assistant":
            content = markdown(
                content,
                extensions=["fenced_code", "tables", "nl2br"]
            )

        rendered_messages.append({
            "role": msg["role"],
            "content": content
        })

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"messages": rendered_messages}
    )

@app.get("/clear")
def clear_chat(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)