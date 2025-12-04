"""
Chat History Manager for AgriGuard API.

Manages chat history persistence and retrieval for the AgriBot chat feature.
"""
import glob
import json
import os
import traceback
from typing import Dict, List, Optional

# Use a local directory for chat history (can be configured via env var)
persistent_dir = os.environ.get("CHAT_HISTORY_DIR", "./chat-history")


class ChatHistoryManager:
    """Manages chat history persistence and retrieval."""
    
    def __init__(self, model: str = "agriguard", history_dir: str = "chat-history"):
        """
        Initialize the chat history manager with the specified directory.
        
        Args:
            model: Model identifier (e.g., "agriguard")
            history_dir: Base directory for storing chat history
        """
        self.model = model
        self.history_dir = os.path.join(persistent_dir, history_dir, model)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure the chat history directory exists."""
        os.makedirs(self.history_dir, exist_ok=True)

    def _get_chat_filepath(self, chat_id: str, session_id: str) -> str:
        """
        Get the full file path for a chat JSON file.
        
        Args:
            chat_id: Unique chat identifier
            session_id: Session identifier (user session)
            
        Returns:
            Full file path for the chat JSON file
        """
        return os.path.join(self.history_dir, session_id, f"{chat_id}.json")

    def save_chat(self, chat_to_save: Dict, session_id: str) -> None:
        """
        Save a chat to file.
        
        Args:
            chat_to_save: Chat data dictionary containing chat_id, messages, etc.
            session_id: Session identifier (user session)
            
        Raises:
            Exception: If saving fails
        """
        chat_dir = os.path.join(self.history_dir, session_id)
        os.makedirs(chat_dir, exist_ok=True)

        # Save chat data
        filepath = self._get_chat_filepath(chat_to_save["chat_id"], session_id)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(chat_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving chat {chat_to_save['chat_id']}: {str(e)}")
            traceback.print_exc()
            raise e

    def get_chat(self, chat_id: str, session_id: str) -> Optional[Dict]:
        """
        Get a specific chat by ID.
        
        Args:
            chat_id: Unique chat identifier
            session_id: Session identifier (user session)
            
        Returns:
            Chat data dictionary or None if not found
        """
        filepath = os.path.join(self.history_dir, session_id, f"{chat_id}.json")
        chat_data = {}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                chat_data = json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Error loading chat history from {filepath}: {str(e)}")
            traceback.print_exc()
            return None
        return chat_data if chat_data else None

    def get_recent_chats(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get recent chats, optionally limited to a specific number.
        
        Args:
            session_id: Session identifier (user session)
            limit: Optional limit on number of chats to return
            
        Returns:
            List of chat data dictionaries, sorted by timestamp (most recent first)
        """
        chat_dir = os.path.join(self.history_dir, session_id)
        os.makedirs(chat_dir, exist_ok=True)
        recent_chats = []
        chat_files = glob.glob(os.path.join(chat_dir, "*.json"))
        for filepath in chat_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    chat_data = json.load(f)
                    recent_chats.append(chat_data)
            except Exception as e:
                print(f"Error loading chat history from {filepath}: {str(e)}")
                traceback.print_exc()

        # Sort by dts (timestamp) - most recent first
        recent_chats.sort(key=lambda x: x.get("dts", 0), reverse=True)
        if limit:
            return recent_chats[:limit]

        return recent_chats

