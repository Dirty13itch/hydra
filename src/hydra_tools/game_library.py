"""
Game Library Module for Hydra
Manages adult game collection with save backups and playtime tracking.

Architecture:
- This module handles: Collection CRUD, session tracking, save management
- External data sources (VNDB, F95zone) are utilities called on-demand
- The library is the consumer of data, not the container of sources

Data Flow:
  [External Sources]     [Game Library Core]     [Storage]
  VNDB API        --->   Metadata enrichment     SQLite DB
  F95zone         --->   Version tracking        File system
  Local scanner   --->   Game detection          NFS storage
"""

import os
import json
import hashlib
import shutil
import sqlite3
import httpx
import re
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field

# Configuration - uses container paths when in Docker, host paths when not
DATA_DIR = os.environ.get("HYDRA_DATA_DIR", "/data")
GAMES_DB_PATH = os.environ.get("GAMES_DB_PATH", f"{DATA_DIR}/games.db")
GAMES_LIBRARY_PATH = os.environ.get("GAMES_LIBRARY_PATH", "/mnt/user/games/library")
GAMES_COVERS_PATH = os.environ.get("GAMES_COVERS_PATH", f"{DATA_DIR}/game_covers")
GAMES_SAVES_PATH = os.environ.get("GAMES_SAVES_PATH", f"{DATA_DIR}/game_saves")


class GameEngine(str, Enum):
    RENPY = "renpy"
    RPGM_MV = "rpgm_mv"
    RPGM_MZ = "rpgm_mz"
    RPGM_VX = "rpgm_vx"
    RPGM_VXACE = "rpgm_vxace"
    UNITY = "unity"
    UNREAL = "unreal"
    HTML = "html"
    FLASH = "flash"
    OTHER = "other"
    UNKNOWN = "unknown"


class GameStatus(str, Enum):
    COMPLETE = "complete"
    IN_DEVELOPMENT = "in_development"
    ABANDONED = "abandoned"
    ON_HOLD = "on_hold"
    UNKNOWN = "unknown"


class CompletionStatus(str, Enum):
    NOT_STARTED = "not_started"
    PLAYING = "playing"
    COMPLETED = "completed"
    DROPPED = "dropped"
    ON_HOLD = "on_hold"


# Pydantic Models
class GameCreate(BaseModel):
    title: str
    developer: Optional[str] = None
    version: Optional[str] = None
    engine: Optional[GameEngine] = GameEngine.UNKNOWN
    status: Optional[GameStatus] = GameStatus.UNKNOWN
    install_path: Optional[str] = None
    executable: Optional[str] = None
    description: Optional[str] = None
    vndb_id: Optional[str] = None
    f95_thread_id: Optional[str] = None
    tags: Optional[List[str]] = []


class GameUpdate(BaseModel):
    title: Optional[str] = None
    developer: Optional[str] = None
    version: Optional[str] = None
    engine: Optional[GameEngine] = None
    status: Optional[GameStatus] = None
    install_path: Optional[str] = None
    executable: Optional[str] = None
    description: Optional[str] = None
    vndb_id: Optional[str] = None
    f95_thread_id: Optional[str] = None
    tags: Optional[List[str]] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None
    favorite: Optional[bool] = None
    hidden: Optional[bool] = None
    completion_status: Optional[CompletionStatus] = None


class VNDBSearchRequest(BaseModel):
    query: str
    limit: int = 10


# Database Layer
class GameDatabase:
    """Handles all database operations for the game library."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id TEXT PRIMARY KEY,
                slug TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                developer TEXT,
                version TEXT,
                engine TEXT DEFAULT 'unknown',
                status TEXT DEFAULT 'unknown',
                install_path TEXT,
                executable TEXT,
                description TEXT,
                vndb_id TEXT,
                f95_thread_id TEXT,
                tags TEXT DEFAULT '[]',
                rating INTEGER CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
                notes TEXT,
                favorite INTEGER DEFAULT 0,
                hidden INTEGER DEFAULT 0,
                completion_status TEXT DEFAULT 'not_started',
                cover_path TEXT,
                size_bytes INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_played TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_sessions (
                id TEXT PRIMARY KEY,
                game_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                duration_seconds INTEGER,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_saves (
                id TEXT PRIMARY KEY,
                game_id TEXT NOT NULL,
                slot_name TEXT,
                backup_path TEXT NOT NULL,
                original_path TEXT,
                file_hash TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_slug ON games(slug)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_engine ON games(engine)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_game ON game_sessions(game_id)")

        conn.commit()
        conn.close()

    def list_games(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """List games with filtering."""
        conn = self._get_conn()
        cursor = conn.cursor()

        query = "SELECT * FROM games WHERE 1=1"
        params = []

        if not filters.get("hidden", False):
            query += " AND hidden = 0"

        if filters.get("engine"):
            query += " AND engine = ?"
            params.append(filters["engine"])

        if filters.get("status"):
            query += " AND status = ?"
            params.append(filters["status"])

        if filters.get("completion"):
            query += " AND completion_status = ?"
            params.append(filters["completion"])

        if filters.get("favorite") is not None:
            query += " AND favorite = ?"
            params.append(1 if filters["favorite"] else 0)

        if filters.get("search"):
            query += " AND (title LIKE ? OR developer LIKE ?)"
            term = f"%{filters['search']}%"
            params.extend([term, term])

        # Count
        count_q = query.replace("SELECT *", "SELECT COUNT(*)")
        cursor.execute(count_q, params)
        total = cursor.fetchone()[0]

        # Paginate
        query += " ORDER BY last_played DESC NULLS LAST, updated_at DESC"
        query += f" LIMIT {filters.get('limit', 50)} OFFSET {filters.get('offset', 0)}"
        cursor.execute(query, params)

        games = []
        for row in cursor.fetchall():
            game = dict(row)
            game["tags"] = json.loads(game["tags"]) if game["tags"] else []
            game["favorite"] = bool(game["favorite"])
            game["hidden"] = bool(game["hidden"])

            # Get playtime
            cursor.execute(
                "SELECT COALESCE(SUM(duration_seconds), 0) FROM game_sessions WHERE game_id = ?",
                (game["id"],)
            )
            game["playtime_seconds"] = cursor.fetchone()[0]
            games.append(game)

        conn.close()
        return {"games": games, "total": total}

    def get_game(self, game_id: str) -> Optional[Dict]:
        """Get a single game by ID."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM games WHERE id = ?", (game_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        game = dict(row)
        game["tags"] = json.loads(game["tags"]) if game["tags"] else []
        game["favorite"] = bool(game["favorite"])
        game["hidden"] = bool(game["hidden"])

        cursor.execute(
            "SELECT COALESCE(SUM(duration_seconds), 0) FROM game_sessions WHERE game_id = ?",
            (game_id,)
        )
        game["playtime_seconds"] = cursor.fetchone()[0]

        conn.close()
        return game

    def create_game(self, data: Dict) -> str:
        """Create a new game entry."""
        conn = self._get_conn()
        cursor = conn.cursor()

        game_id = str(uuid.uuid4())[:8]
        slug = self._generate_slug(data["title"])

        # Ensure unique slug
        cursor.execute("SELECT id FROM games WHERE slug = ?", (slug,))
        if cursor.fetchone():
            slug = f"{slug}-{game_id}"

        cursor.execute("""
            INSERT INTO games (id, slug, title, developer, version, engine, status,
                              install_path, executable, description, vndb_id, f95_thread_id,
                              tags, size_bytes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game_id, slug, data["title"], data.get("developer"), data.get("version"),
            data.get("engine", "unknown"), data.get("status", "unknown"),
            data.get("install_path"), data.get("executable"), data.get("description"),
            data.get("vndb_id"), data.get("f95_thread_id"),
            json.dumps(data.get("tags", [])), data.get("size_bytes")
        ))

        conn.commit()
        conn.close()
        return game_id

    def update_game(self, game_id: str, data: Dict) -> bool:
        """Update a game entry."""
        conn = self._get_conn()
        cursor = conn.cursor()

        updates = []
        params = []

        for field, value in data.items():
            if value is not None:
                if field == "tags":
                    value = json.dumps(value)
                elif field in ("favorite", "hidden"):
                    value = 1 if value else 0
                updates.append(f"{field} = ?")
                params.append(value)

        if not updates:
            conn.close()
            return False

        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(game_id)

        cursor.execute(f"UPDATE games SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def delete_game(self, game_id: str) -> bool:
        """Delete a game entry."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get library statistics."""
        conn = self._get_conn()
        cursor = conn.cursor()

        stats = {}

        cursor.execute("SELECT COUNT(*) FROM games WHERE hidden = 0")
        stats["total_games"] = cursor.fetchone()[0]

        cursor.execute("SELECT engine, COUNT(*) FROM games WHERE hidden = 0 GROUP BY engine")
        stats["by_engine"] = {r[0]: r[1] for r in cursor.fetchall()}

        cursor.execute("SELECT completion_status, COUNT(*) FROM games WHERE hidden = 0 GROUP BY completion_status")
        stats["by_completion"] = {r[0]: r[1] for r in cursor.fetchall()}

        cursor.execute("SELECT COALESCE(SUM(duration_seconds), 0) FROM game_sessions")
        stats["total_playtime_seconds"] = cursor.fetchone()[0]
        stats["total_playtime_hours"] = round(stats["total_playtime_seconds"] / 3600, 1)

        cursor.execute("SELECT COALESCE(SUM(size_bytes), 0) FROM games")
        stats["total_size_bytes"] = cursor.fetchone()[0]
        stats["total_size_gb"] = round(stats["total_size_bytes"] / (1024**3), 2)

        conn.close()
        return stats

    def start_session(self, game_id: str) -> str:
        """Start a play session."""
        conn = self._get_conn()
        cursor = conn.cursor()

        session_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat()

        cursor.execute(
            "INSERT INTO game_sessions (id, game_id, started_at) VALUES (?, ?, ?)",
            (session_id, game_id, now)
        )
        cursor.execute("UPDATE games SET last_played = ? WHERE id = ?", (now, game_id))

        conn.commit()
        conn.close()
        return session_id

    def end_session(self, session_id: str) -> Dict:
        """End a play session."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM game_sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        session = dict(row)
        if session["ended_at"]:
            conn.close()
            return session

        ended_at = datetime.utcnow()
        started_at = datetime.fromisoformat(session["started_at"])
        duration = int((ended_at - started_at).total_seconds())

        cursor.execute(
            "UPDATE game_sessions SET ended_at = ?, duration_seconds = ? WHERE id = ?",
            (ended_at.isoformat(), duration, session_id)
        )
        conn.commit()

        session["ended_at"] = ended_at.isoformat()
        session["duration_seconds"] = duration
        conn.close()
        return session

    def _generate_slug(self, title: str) -> str:
        slug = title.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        return slug.strip('-')[:100]


# Game Detection Utilities
class GameDetector:
    """Utility for detecting game engines and executables."""

    @staticmethod
    def detect_engine(game_path: Path) -> GameEngine:
        """Detect game engine from file structure."""
        if not game_path.exists():
            return GameEngine.UNKNOWN

        try:
            files = list(game_path.rglob("*"))
            file_names = [f.name.lower() for f in files if f.is_file()]
            dir_names = [d.name.lower() for d in files if d.is_dir()]

            # RenPy
            if any(f.endswith('.rpy') or f.endswith('.rpyc') for f in file_names):
                return GameEngine.RENPY
            if 'renpy' in dir_names:
                return GameEngine.RENPY

            # RPGM MV/MZ
            if 'www' in dir_names and ('package.json' in file_names or 'game.exe' in file_names):
                if any('rmmz' in f for f in file_names):
                    return GameEngine.RPGM_MZ
                return GameEngine.RPGM_MV

            # RPGM VX Ace
            if any(f.endswith('.rgss3a') for f in file_names):
                return GameEngine.RPGM_VXACE

            # Unity
            if any('unityplayer.dll' in f for f in file_names):
                return GameEngine.UNITY

            # Unreal
            if any(f.endswith('.pak') for f in file_names):
                return GameEngine.UNREAL

            # HTML
            if 'index.html' in file_names:
                return GameEngine.HTML

            return GameEngine.UNKNOWN
        except Exception:
            return GameEngine.UNKNOWN

    @staticmethod
    def find_executable(game_path: Path, engine: GameEngine) -> Optional[str]:
        """Find main executable for a game."""
        if not game_path.exists():
            return None

        patterns = {
            GameEngine.RENPY: ["*.exe", "*.sh"],
            GameEngine.RPGM_MV: ["game.exe", "nw.exe"],
            GameEngine.RPGM_MZ: ["game.exe", "nw.exe"],
            GameEngine.RPGM_VXACE: ["game.exe"],
            GameEngine.UNITY: ["*.exe"],
            GameEngine.HTML: ["index.html"],
        }

        for pattern in patterns.get(engine, ["*.exe"]):
            matches = list(game_path.glob(pattern))
            if matches:
                return str(matches[0].relative_to(game_path))
        return None

    @staticmethod
    def calculate_size(path: Path) -> int:
        """Calculate directory size in bytes."""
        total = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    total += entry.stat().st_size
        except Exception:
            pass
        return total


# VNDB Client (External Data Source)
class VNDBClient:
    """Client for VNDB API - metadata provider."""

    BASE_URL = "https://api.vndb.org/kana"

    async def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search VNDB for visual novels."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/vn",
                    json={
                        "filters": ["search", "=", query],
                        "fields": "id, title, alttitle, released, developers.name, tags.name, rating, image.url, description",
                        "results": limit
                    }
                )
                response.raise_for_status()
                return response.json().get("results", [])
            except Exception as e:
                print(f"VNDB error: {e}")
                return []

    async def get_by_id(self, vndb_id: str) -> Optional[Dict]:
        """Get VN by ID."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/vn",
                    json={
                        "filters": ["id", "=", vndb_id],
                        "fields": "id, title, alttitle, released, developers.name, tags.name, rating, image.url, description"
                    }
                )
                response.raise_for_status()
                results = response.json().get("results", [])
                return results[0] if results else None
            except Exception:
                return None


# Initialize services
db = GameDatabase(GAMES_DB_PATH)
vndb = VNDBClient()
detector = GameDetector()

# Ensure directories exist
for path in [GAMES_LIBRARY_PATH, GAMES_COVERS_PATH, GAMES_SAVES_PATH]:
    Path(path).mkdir(parents=True, exist_ok=True)


# Router Factory
def create_game_library_router() -> APIRouter:
    """Create and configure the game library router."""
    router = APIRouter(prefix="/games", tags=["Game Library"])

    @router.get("/")
    async def list_games(
        engine: Optional[str] = None,
        status: Optional[str] = None,
        completion: Optional[str] = None,
        favorite: Optional[bool] = None,
        hidden: bool = False,
        search: Optional[str] = None,
        limit: int = Query(50, le=200),
        offset: int = 0
    ):
        """List games with filtering and pagination."""
        return db.list_games({
            "engine": engine, "status": status, "completion": completion,
            "favorite": favorite, "hidden": hidden, "search": search,
            "limit": limit, "offset": offset
        })

    @router.get("/stats")
    async def get_stats():
        """Get library statistics."""
        return db.get_stats()

    @router.post("/")
    async def create_game(game: GameCreate):
        """Add a new game."""
        data = game.model_dump()

        # Auto-detect engine if path provided
        if game.install_path:
            path = Path(game.install_path)
            if path.exists():
                if game.engine == GameEngine.UNKNOWN:
                    data["engine"] = detector.detect_engine(path).value
                if not game.executable:
                    data["executable"] = detector.find_executable(path, GameEngine(data["engine"]))
                data["size_bytes"] = detector.calculate_size(path)

        game_id = db.create_game(data)
        return db.get_game(game_id)

    @router.get("/{game_id}")
    async def get_game(game_id: str):
        """Get a specific game."""
        game = db.get_game(game_id)
        if not game:
            raise HTTPException(404, "Game not found")
        return game

    @router.patch("/{game_id}")
    async def update_game(game_id: str, update: GameUpdate):
        """Update a game."""
        data = update.model_dump(exclude_unset=True)
        # Convert enums to values
        for k, v in list(data.items()):
            if hasattr(v, "value"):
                data[k] = v.value

        if not db.update_game(game_id, data):
            raise HTTPException(404, "Game not found")
        return db.get_game(game_id)

    @router.delete("/{game_id}")
    async def delete_game(game_id: str, delete_files: bool = False):
        """Delete a game."""
        game = db.get_game(game_id)
        if not game:
            raise HTTPException(404, "Game not found")

        if delete_files and game.get("install_path"):
            path = Path(game["install_path"])
            if path.exists():
                shutil.rmtree(path)

        db.delete_game(game_id)
        return {"status": "deleted", "id": game_id}

    # VNDB Integration
    @router.post("/vndb/search")
    async def vndb_search(request: VNDBSearchRequest):
        """Search VNDB for metadata."""
        results = await vndb.search(request.query, request.limit)
        return [{
            "id": vn.get("id"),
            "title": vn.get("title"),
            "developers": [d.get("name") for d in vn.get("developers", [])],
            "tags": [t.get("name") for t in vn.get("tags", [])[:15]],
            "rating": vn.get("rating"),
            "image_url": vn.get("image", {}).get("url") if vn.get("image") else None,
            "description": vn.get("description", "")[:500]
        } for vn in results]

    @router.post("/{game_id}/vndb-link")
    async def link_vndb(game_id: str, vndb_id: str, fetch_metadata: bool = True):
        """Link game to VNDB entry."""
        game = db.get_game(game_id)
        if not game:
            raise HTTPException(404, "Game not found")

        update_data = {"vndb_id": vndb_id}

        if fetch_metadata:
            vn = await vndb.get_by_id(vndb_id)
            if vn:
                devs = [d.get("name") for d in vn.get("developers", [])]
                tags = [t.get("name") for t in vn.get("tags", [])[:25]]
                update_data["developer"] = devs[0] if devs else None
                update_data["description"] = vn.get("description")
                update_data["tags"] = tags

                # Download cover
                img = vn.get("image", {})
                if img and img.get("url"):
                    try:
                        async with httpx.AsyncClient() as client:
                            resp = await client.get(img["url"])
                            if resp.status_code == 200:
                                cover_path = Path(GAMES_COVERS_PATH) / f"{game_id}.jpg"
                                cover_path.write_bytes(resp.content)
                                update_data["cover_path"] = str(cover_path)
                    except Exception:
                        pass

        db.update_game(game_id, update_data)
        return db.get_game(game_id)

    # Session Tracking
    @router.post("/{game_id}/sessions/start")
    async def start_session(game_id: str):
        """Start play session."""
        if not db.get_game(game_id):
            raise HTTPException(404, "Game not found")
        session_id = db.start_session(game_id)
        return {"session_id": session_id, "game_id": game_id, "started_at": datetime.utcnow().isoformat()}

    @router.post("/sessions/{session_id}/end")
    async def end_session(session_id: str):
        """End play session."""
        session = db.end_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        return session

    # Directory Scanning
    @router.post("/scan")
    async def scan_directory(path: str):
        """Scan directory for games."""
        scan_path = Path(path)
        if not scan_path.exists() or not scan_path.is_dir():
            raise HTTPException(400, "Invalid path")

        games = []
        for item in scan_path.iterdir():
            if item.is_dir():
                engine = detector.detect_engine(item)
                if engine != GameEngine.UNKNOWN:
                    games.append({
                        "path": str(item),
                        "name": item.name,
                        "engine": engine.value,
                        "executable": detector.find_executable(item, engine),
                        "size_bytes": detector.calculate_size(item)
                    })

        return {"path": str(scan_path), "found": len(games), "games": games}

    @router.post("/import")
    async def import_game(path: str, title: Optional[str] = None, search_vndb: bool = True):
        """Import game from directory."""
        game_path = Path(path)
        if not game_path.exists():
            raise HTTPException(400, "Path not found")

        engine = detector.detect_engine(game_path)
        game_title = title or game_path.name

        data = {
            "title": game_title,
            "engine": engine.value,
            "install_path": str(game_path),
            "executable": detector.find_executable(game_path, engine),
            "size_bytes": detector.calculate_size(game_path)
        }

        # Try VNDB lookup
        if search_vndb:
            results = await vndb.search(game_title, 1)
            if results:
                vn = results[0]
                devs = [d.get("name") for d in vn.get("developers", [])]
                data["vndb_id"] = vn.get("id")
                data["developer"] = devs[0] if devs else None
                data["tags"] = [t.get("name") for t in vn.get("tags", [])[:20]]

        game_id = db.create_game(data)
        return db.get_game(game_id)

    return router
