from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import logging

from fapi.llm import get_response

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

    return templates.TemplateResponse(
        request,
        "index.html",
        {"messages": request.session["chat_history"]}
    )


@app.post("/chat")
def chat(
    request: Request,
    prompt: str = Form(...),
    image_base64: str = Form(None)
):
    try:
        if "chat_history" not in request.session:
            request.session["chat_history"] = []

        history = request.session["chat_history"]

        clean_prompt = prompt.strip()

        if image_base64:
            clean_prompt += "\n\n[image attached]"

        conversation = []

        for msg in history:
            role = "human" if msg["role"] == "user" else "ai"
            conversation.append((role, msg["content"]))

        conversation.append(("human", clean_prompt))

        logger.info(f"Getting response for prompt: {clean_prompt[:50]}...")
        answer = get_response(conversation, image_base64=image_base64)
        logger.info(f"Got response: {answer[:100]}...")

        history.append({
            "role": "user",
            "content": clean_prompt
        })

        history.append({
            "role": "assistant",
            "content": answer.strip()
        })

        request.session["chat_history"] = history
        logger.info(f"Chat history updated. Total messages: {len(history)}")

        return RedirectResponse("/", status_code=302)
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        # Still add the user message even if LLM fails
        if "chat_history" not in request.session:
            request.session["chat_history"] = []
        
        history = request.session["chat_history"]
        clean_prompt = prompt.strip()
        
        if image_base64:
            clean_prompt += "\n\n[image attached]"
        
        history.append({
            "role": "user",
            "content": clean_prompt
        })
        
        history.append({
            "role": "assistant",
            "content": f"⚠️ Error getting response: {str(e)}"
        })
        
        request.session["chat_history"] = history
        return RedirectResponse("/", status_code=302)


@app.get("/clear")
def clear_chat(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)