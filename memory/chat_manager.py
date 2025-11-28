from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pymongo import MongoClient

# Assuming this imports your previous compaction logic
from ai_processing.compaction import compact_history
from utils.logger import get_logger

logger = get_logger()

class ChatManager:
    def __init__(self, config: Dict[str, Any], uid: str, tid: str):
        """
        Initialize MongoDB connection and set up collections.
        """
        self.model_name = config['ai_processing']['model']
        self.client = MongoClient(config['mongodb']['uri'])
        self.db = self.client[config['mongodb']['database_name']]
        self.threads = self.db["threads"]
        self.uid = uid
        self.tid = tid
        self.threads.create_index([("uid", 1), ("tid", 1)], unique=True)

    def create_thread(self) -> str:
        """Create a new chat thread for a user if it doesn't exist."""
        try:
            if not self.threads.find_one({"uid": self.uid, "tid": self.tid}):
                logger.info(f"(chat manager) - Creating new thread {self.tid} for user {self.uid}")
                self.threads.insert_one({
                    "uid": self.uid,
                    "tid": self.tid,
                    "created_at": datetime.now(timezone.utc),
                    "history": [],
                })
                return f"Thread {self.tid} created for user {self.uid}"
            
            return f"Thread {self.tid} already exists for user {self.uid}"
        except Exception as e:
            logger.error(f"(chat manager) - Error creating thread: {e}")
            return "Error creating thread"
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to a chat thread with a timestamp."""
        mssg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat() 
        }
        
        # Check if the thread exists, if not create it
        if not self.threads.find_one({"uid": self.uid, "tid": self.tid}):
            logger.info(f"(chat manager) - Thread {self.tid} does not exist. Creating new thread for user {self.uid}.")
            self.create_thread()

        # Retry adding the message
        result = self.threads.update_one(
            {"uid": self.uid, "tid": self.tid},
            {"$push": {"history": mssg}}
        )
        
        if result.modified_count > 0:
            logger.info(f"(chat manager) - Message added to thread {self.tid} for user {self.uid}")
        else:
            logger.warning(f"(chat manager) - Failed to add message. Thread {self.tid} may not exist.")

    def get_thread_messages(self, llm_client) -> Optional[List[Dict[str, str]]]:
        """
        Retrieve messages. 
        ensures timestamps are STRIPPED before returning to user or sending to LLM.
        """
        thread_doc = self.threads.find_one({"uid": self.uid, "tid": self.tid})
        
        if thread_doc:
            logger.info(f"(chat manager) - Retrieved messages for thread {self.tid} of user {self.uid}")
            
            raw_history = thread_doc.get("history", [])

            if len(raw_history) > 10:
                logger.info(f"History length {len(raw_history)} > 10. Attempting compaction...")
                
                clean_history_for_llm = self._sanitize_messages(raw_history)
                
                compacted_history = compact_history(clean_history_for_llm, llm_client, False)

                if len(compacted_history) < len(raw_history):
                    self.update_history(compacted_history)
                    
                    return compacted_history
                else:
                    logger.warning("(chat manager) - Compaction did not reduce history size. Returning original.")

            return self._sanitize_messages(raw_history)
            
        logger.warning(f"(chat manager) - Thread {self.tid} for user {self.uid} not found")
        return None
    
    def update_history(self, new_history: List[Dict[str, str]]) -> None:
        """
        Completely replaces the message history in MongoDB.
        """
        result = self.threads.update_one(
            {"uid": self.uid, "tid": self.tid},
            {"$set": {"history": new_history}}
        )
        if result.modified_count > 0:
            logger.info(f"(chat manager) - History replaced for {self.tid}. New length: {len(new_history)}")
        else:
            logger.warning(f"(chat manager) - History update called for {self.tid} but no doc modified.")
    
    def clear_history(self) -> None:
        """Clear the message history for the current thread."""
        try:
            # Check if the thread exists, if not create it
            if not self.threads.find_one({"uid": self.uid, "tid": self.tid}):
                logger.info(f"(chat manager) - Thread {self.tid} does not exist. Creating new thread for user {self.uid}.")
                self.create_thread()

            result = self.threads.update_one(
                {"uid": self.uid, "tid": self.tid},
                {"$set": {"history": []}}
            )
            if result.modified_count > 0:
                logger.info(f"(chat manager) - Cleared history for thread {self.tid} of user {self.uid}")
            else:
                logger.warning(f"(chat manager) - No history to clear for thread {self.tid} of user {self.uid}")
        except Exception as e:
            logger.error(f"(chat manager) - Error clearing history: {e}")

    def _sanitize_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Helper to filter out internal fields (like timestamps, IDs) 
        and return only standard role/content pairs.
        """
        return [
            {
                "role": msg.get("role"), 
                "content": msg.get("content")
            } 
            for msg in messages
        ]