import uuid
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from markdown import markdown
from datetime import datetime

from fapi.llm import get_response
from fapi.session import load_session, save_session, cleanup_sessions, get_session_file

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

templates = Jinja2Templates(directory="fapi/templates")

# Cleanup on startup
cleanup_sessions()


@app.get("/")
def home(request: Request):
    """Serve the chat UI."""
    try:
        # Get or create session ID from cookie
        session_id = request.cookies.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Load session
        session = load_session(session_id)
        messages = session.get("messages", [])
        
        # Render messages
        rendered_messages = []
        for msg in messages:
            content = msg["content"]
            if msg["role"] == "assistant":
                try:
                    content = markdown(
                        content,
                        extensions=["fenced_code", "tables", "nl2br"]
                    )
                except Exception as e:
                    logger.error(f"Error rendering markdown: {e}")
            
            rendered_messages.append({
                "role": msg["role"],
                "content": content
            })
        
        response = templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "messages": rendered_messages,
                "session_id": session_id
            }
        )
        response.set_cookie("session_id", session_id, max_age=7*24*60*60)
        return response
    except Exception as e:
        logger.error(f"Error in home endpoint: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Error loading chat interface"}
        )


@app.post("/api/chat/new")
def create_new_chat(request: Request):
    """Create a new chat session."""
    try:
        session_id = str(uuid.uuid4())
        session = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "messages": []
        }
        
        if not save_session(session_id, session):
            logger.error(f"Failed to save new session {session_id}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Failed to create chat session"}
            )
        
        logger.info(f"Created new chat session: {session_id}")
        response = JSONResponse(
            content={
                "session_id": session_id,
                "messages": []
            }
        )
        response.set_cookie("session_id", session_id, max_age=7*24*60*60)
        return response
    except Exception as e:
        logger.error(f"Error creating new chat: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Unable to create a new chat session. Error: {str(e)}"}
        )


@app.post("/api/chat/send")
async def send_message(request: Request):
    """Send a message and get an assistant response."""
    try:
        data = await request.json()
        prompt = data.get("prompt", "").strip()
        image_base64 = data.get("image_base64")
        session_id = data.get("session_id")
        
        if not session_id:
            logger.error("No session_id provided")
            return JSONResponse(
                status_code=400,
                content={"detail": "Session ID is required"}
            )
        
        if not prompt:
            logger.warning(f"Empty prompt from session {session_id}")
            return JSONResponse(
                status_code=400,
                content={"detail": "Message cannot be empty"}
            )
        
        # Load session
        session = load_session(session_id)
        messages = session.get("messages", [])
        
        # Prepare conversation for LLM
        conversation = []
        for msg in messages:
            conversation.append((msg["role"], msg["content"]))
        conversation.append(("user", prompt))
        
        # Add user message to session
        messages.append({
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().isoformat()
        })
        
        # Get response from LLM
        try:
            logger.info(f"Generating response for session {session_id}")
            answer = get_response(
                conversation,
                image_base64=image_base64
            )
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": f"Unable to generate an assistant response. Error: {str(e)}"}
            )
        
        # Add assistant message to session
        messages.append({
            "role": "assistant",
            "content": answer,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update and save session
        session["messages"] = messages
        if not save_session(session_id, session):
            logger.error(f"Failed to save session after message: {session_id}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Failed to save message"}
            )
        
        # Render assistant response
        rendered_content = markdown(
            answer,
            extensions=["fenced_code", "tables", "nl2br"]
        )
        
        logger.info(f"Response generated for session {session_id}")
        return JSONResponse(
            content={
                "session_id": session_id,
                "assistant_response": answer,
                "rendered_response": rendered_content,
                "messages": messages
            }
        )
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request")
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid JSON in request"}
        )
    except Exception as e:
        logger.error(f"Error in send_message: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": f"An error occurred: {str(e)}"}
        )


@app.post("/api/chat/clear")
def clear_chat(request: Request):
    """Delete the current session and create a new one."""
    try:
        data_dict = dict(request.cookies)
        session_id = data_dict.get("session_id")
        
        # Delete old session file if it exists
        if session_id:
            session_file = get_session_file(session_id)
            if session_file.exists():
                try:
                    session_file.unlink()
                    logger.info(f"Deleted session file: {session_id}")
                except Exception as e:
                    logger.error(f"Error deleting session file {session_id}: {e}")
        
        # Create new session
        new_session_id = str(uuid.uuid4())
        new_session = {
            "session_id": new_session_id,
            "created_at": datetime.now().isoformat(),
            "messages": []
        }
        
        if not save_session(new_session_id, new_session):
            logger.error(f"Failed to create new session during clear")
            return JSONResponse(
                status_code=500,
                content={"detail": "Failed to create new session"}
            )
        
        logger.info(f"Cleared chat and created new session: {new_session_id}")
        response = JSONResponse(
            content={
                "session_id": new_session_id,
                "messages": []
            }
        )
        response.set_cookie("session_id", new_session_id, max_age=7*24*60*60)
        return response
    except Exception as e:
        logger.error(f"Error clearing chat: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error clearing chat: {str(e)}"}
        )