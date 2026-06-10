import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Session directory
SESSIONS_DIR = Path("sessions")
SESSIONS_DIR.mkdir(exist_ok=True)


def get_session_file(session_id: str) -> Path:
    """Get the path to a session file."""
    return SESSIONS_DIR / f"{session_id}.json"


def load_session(session_id: str) -> dict:
    """Load a session from disk. Create new if doesn't exist."""
    try:
        session_file = get_session_file(session_id)
        if session_file.exists():
            with open(session_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading session {session_id}: {e}")
    
    # Return new empty session
    return {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "messages": []
    }


def save_session(session_id: str, session: dict) -> bool:
    """Save a session to disk."""
    try:
        session_file = get_session_file(session_id)
        with open(session_file, 'w') as f:
            json.dump(session, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving session {session_id}: {e}")
        return False


def cleanup_sessions():
    """Clean up orphaned session files on startup."""
    try:
        for session_file in SESSIONS_DIR.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    session = json.load(f)
                    # Cleanup logic - remove sessions older than 7 days if needed
                    # For now, just validate they're valid JSON
            except json.JSONDecodeError:
                logger.warning(f"Removing corrupted session file: {session_file}")
                session_file.unlink()
    except Exception as e:
        logger.error(f"Error during session cleanup: {e}")
