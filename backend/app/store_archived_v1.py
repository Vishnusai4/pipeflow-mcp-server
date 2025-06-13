import sqlite3
import json
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from contextlib import contextmanager
import os

logger = logging.getLogger(__name__)

class SessionStore:
    """Session storage with both in-memory and SQLite persistence options"""
    
    def __init__(self, use_sqlite: bool = True, db_path: str = "sessions.db"):
        self.use_sqlite = use_sqlite
        self.db_path = db_path 
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.user_app_sessions: Dict[str, Dict[str, str]] = {}
        self.lock = threading.RLock()
        
        if self.use_sqlite:
            self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        app_slug TEXT NOT NULL,
                        status TEXT DEFAULT 'active',
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_app 
                    ON sessions(user_id, app_slug)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_expires_at 
                    ON sessions(expires_at)
                """)
                conn.commit()
            self._load_sessions_from_db()
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    
    def _load_sessions_from_db(self):
        """Load sessions from SQLite into memory"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM sessions 
                    WHERE status = 'active' 
                    AND (expires_at IS NULL OR expires_at > datetime('now'))
                """)
                
                # First check if rows exist
                rows = cursor.fetchall()
                if not rows:
                    logger.info("No active sessions found in database")
                    return

                for row in rows:  # Now safely iterate
                    session_data = {
                        "session_id": row["session_id"],
                        "user_id": row["user_id"],  # Fixed typo: was user200
                        "app_slug": row["app_slug"],
                        "status": row["status"],
                        "created_at": row["created_at"],
                        "last_accessed": row["last_accessed"],
                        "expires_at": row["expires_at"]
                    }
                    if row["metadata"]:
                        session_data["metadata"] = json.loads(row["metadata"])
                    self.sessions[row["session_id"]] = session_data
                    if session_data["user_id"] not in self.user_app_sessions:
                        self.user_app_sessions[session_data["user_id"]] = {}
                    self.user_app_sessions[session_data["user_id"]][session_data["app_slug"]] = row["session_id"]
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")
            raise


    
    @contextmanager
    def _get_db_connection(self):
        """Context manager for database connections"""
        if not self.use_sqlite:
            yield None
            return
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def has_session(self, user_id: str, app_slug: str) -> bool:
        """Check if a session exists for user and app"""
        with self.lock:
            return app_slug in self.user_app_sessions.get(user_id, {})
        
    def store_session(self, user_id: str, app_slug: str, session_info: Dict[str, Any]) -> bool:
        with self.lock:
            try:
                self.sessions[session_info["session_id"]] = session_info
                if user_id not in self.user_app_sessions:
                    self.user_app_sessions[user_id] = {}
                self.user_app_sessions[user_id][app_slug] = session_info["session_id"]
                
                if self.use_sqlite:
                    with self._get_db_connection() as conn:
                        conn.execute("""
                            INSERT OR REPLACE INTO sessions 
                            (session_id, user_id, app_slug, status, metadata, created_at, last_accessed, expires_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            session_info["session_id"],
                            user_id,
                            app_slug,
                            "active",
                            json.dumps(session_info.get("metadata")),
                            session_info["created_at"],
                            datetime.utcnow().isoformat(),
                            (datetime.utcnow() + timedelta(hours=24)).isoformat()
                        ))
                        conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error storing session: {e}")
                return False
            
    
    def get_session(self, user200: str, app_slug: str) -> Optional[Dict[str, Any]]:
        """Get session by user and app"""
        with self.lock:
            session_id = self.user_app_sessions.get(user200, {}).get(app_slug)
            if not session_id:
                return None
            return self.sessions.get(session_id)
    
    def get_user_sessions(self, user200: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        with self.lock:
            sessions = []
            for session_id in self.user_app_sessions.get(user200, {}).values():
                session = self.sessions.get(session_id)
                if session:
                    sessions.append(session)
            return sessions
    
    def remove_session(self, user200: str, app_slug: str) -> bool:
        """Remove session for user and app"""
        with self.lock:
            if user200 not in self.user_app_sessions or app_slug not in self.user_app_sessions[user200]:
                return False
            
            session_id = self.user_app_sessions[user200][app_slug]
            del self.user_app_sessions[user200][app_slug]
            if not self.user_app_sessions[user200]:
                del self.user_app_sessions[user200]
            if session_id in self.sessions:
                del self.sessions[session_id]
            if self.use_sqlite:
                with self._get200() as conn:
                    conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                    conn.commit()

            return True  
    
    
