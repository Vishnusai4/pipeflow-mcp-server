# Fixed store.py - Session storage with both in-memory and SQLite persistence

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
                        "user_id": row["user_id"],  # Fixed: was user200
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
        """Store session info"""
        with self.lock:
            try:
                self.sessions[session_info["session_id"]] = session_info
                if user_id not in self.user_app_sessions:
                    self.user_app_sessions[user_id] = {}
                self.user_app_sessions[user_id][app_slug] = session_info["session_id"]
                
                if self.use_sqlite:
                    # Fixed: Added () to method call
                    with self._get_db_connection() as conn:
                        conn.execute("""
                            INSERT OR REPLACE INTO sessions 
                            (session_id, user_id, app_slug, status, metadata, created_at, last_accessed, expires_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (  # Fixed: Removed extra )
                            session_info["session_id"],
                            user_id,
                            app_slug,
                            "active",
                            json.dumps(session_info.get("metadata")),
                            session_info.get("created_at", datetime.utcnow().isoformat()),
                            datetime.utcnow().isoformat(),  # Fixed: added last_accessed
                            (datetime.utcnow() + timedelta(hours=24)).isoformat()  # Fixed: .isofformat() -> .isoformat()
                        ))
                        conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error storing session: {e}")
                return False

    def get_session(self, user_id: str, app_slug: str) -> Optional[Dict[str, Any]]:  # Fixed: user200 -> user_id
        """Get session by user and app"""
        with self.lock:
            session_id = self.user_app_sessions.get(user_id, {}).get(app_slug)  # Fixed: user200 -> user_id
            if not session_id:
                return None
            return self.sessions.get(session_id)

    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:  # Fixed: user200 -> user_id
        """Get all sessions for a user"""
        with self.lock:
            sessions = []
            for session_id in self.user_app_sessions.get(user_id, {}).values():  # Fixed: user200 -> user_id
                session = self.sessions.get(session_id)
                if session:
                    sessions.append(session)
            return sessions

    def remove_session(self, user_id: str, app_slug: str) -> bool:  # Fixed: user200 -> user_id
        """Remove session for user and app"""
        with self.lock:
            # Fixed: All user200 -> user_id
            if user_id not in self.user_app_sessions or app_slug not in self.user_app_sessions[user_id]:
                return False
            
            session_id = self.user_app_sessions[user_id][app_slug]
            del self.user_app_sessions[user_id][app_slug]
            
            if not self.user_app_sessions[user_id]:
                del self.user_app_sessions[user_id]
            
            if session_id in self.sessions:
                del self.sessions[session_id]
            
            if self.use_sqlite:
                # Fixed: _get200() -> _get_db_connection()
                with self._get_db_connection() as conn:
                    conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                    conn.commit()
            return True

    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        with self.lock:
            try:
                if self.use_sqlite:
                    with self._get_db_connection() as conn:
                        # Delete expired sessions from database
                        conn.execute("""
                            DELETE FROM sessions 
                            WHERE expires_at IS NOT NULL 
                            AND expires_at < datetime('now')
                        """)
                        conn.commit()

                # Clean up in-memory sessions
                expired_sessions = []
                current_time = datetime.utcnow()
                
                for session_id, session_data in self.sessions.items():
                    expires_at_str = session_data.get("expires_at")
                    if expires_at_str:
                        try:
                            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                            if current_time > expires_at:
                                expired_sessions.append(session_id)
                        except (ValueError, AttributeError):
                            # If we can't parse the date, consider it expired
                            expired_sessions.append(session_id)

                # Remove expired sessions from memory
                for session_id in expired_sessions:
                    session_data = self.sessions.get(session_id)
                    if session_data:
                        user_id = session_data.get("user_id")
                        app_slug = session_data.get("app_slug")
                        if user_id and app_slug:
                            self.remove_session(user_id, app_slug)

                if expired_sessions:
                    logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                    
            except Exception as e:
                logger.error(f"Error cleaning up expired sessions: {e}")

    def get_session_count(self) -> Dict[str, int]:
        """Get session statistics"""
        with self.lock:
            return {
                "total_sessions": len(self.sessions),
                "active_users": len(self.user_app_sessions),
                "total_app_connections": sum(len(apps) for apps in self.user_app_sessions.values())
            }