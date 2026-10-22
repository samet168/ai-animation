import os
import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("AIAnimationStudio.Database")

class Database:
    """SQLite Database manager for projects and storyboard scenes."""

    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            appdata_base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
            db_dir = os.path.join(appdata_base, "AIAnimationStudio", "database")
            os.makedirs(db_dir, exist_ok=True)
            self.db_path = os.path.join(db_dir, "studio.db")
        else:
            self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                topic TEXT,
                art_style TEXT,
                aspect_ratio TEXT DEFAULT '9:16',
                voice TEXT DEFAULT 'km-KH-PisethNeural',
                final_video_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS scenes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                scene_number INTEGER,
                narration_km TEXT,
                image_prompt TEXT,
                image_path TEXT,
                audio_path TEXT,
                audio_duration REAL DEFAULT 0.0,
                camera_motion TEXT DEFAULT 'zoom_in',
                video_clip_path TEXT,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
            )
            """)
            conn.commit()

    def create_project(self, title: str, topic: str, art_style: str, aspect_ratio: str, voice: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO projects (title, topic, art_style, aspect_ratio, voice)
                VALUES (?, ?, ?, ?, ?)
            """, (title, topic, art_style, aspect_ratio, voice))
            conn.commit()
            return cursor.lastrowid

    def update_project(self, project_id: int, **kwargs):
        allowed_keys = ["title", "topic", "art_style", "aspect_ratio", "voice", "final_video_path"]
        updates = []
        values = []
        for k, v in kwargs.items():
            if k in allowed_keys:
                updates.append(f"{k} = ?")
                values.append(v)
        if updates:
            values.append(project_id)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE projects SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)
                conn.commit()

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def list_projects(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def add_scene(self, project_id: int, scene_number: int, narration_km: str, 
                  image_prompt: str, camera_motion: str = "zoom_in") -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scenes (project_id, scene_number, narration_km, image_prompt, camera_motion)
                VALUES (?, ?, ?, ?, ?)
            """, (project_id, scene_number, narration_km, image_prompt, camera_motion))
            conn.commit()
            return cursor.lastrowid

    def update_scene(self, scene_id: int, **kwargs):
        allowed_keys = ["scene_number", "narration_km", "image_prompt", "image_path", 
                        "audio_path", "audio_duration", "camera_motion", "video_clip_path"]
        updates = []
        values = []
        for k, v in kwargs.items():
            if k in allowed_keys:
                updates.append(f"{k} = ?")
                values.append(v)
        if updates:
            values.append(scene_id)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE scenes SET {', '.join(updates)} WHERE id = ?", values)
                conn.commit()

    def get_scenes(self, project_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scenes WHERE project_id = ? ORDER BY scene_number ASC", (project_id,))
            return [dict(row) for row in cursor.fetchall()]

    def clear_project_scenes(self, project_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scenes WHERE project_id = ?", (project_id,))
            conn.commit()


# Global database instance
db = Database()
