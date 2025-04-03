#!/usr/bin/env python3
"""Logging module for qgit operations with optimized storage and retrieval.

This module provides a centralized logging system that uses SQLite for storage
and leverages the resource manager for optimized performance on M4 systems.
"""

import asyncio
import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, List, Optional

from internal.resource_manager import get_resource_manager

from qgits.qgit_errors import FileOperationError


@dataclass
class LogEntry:
    """Represents a single log entry."""

    timestamp: str
    level: str
    command: str
    message: str
    metadata: Dict[str, Any]
    status: str
    duration: float


class QGitLogger:
    """Centralized logging system for qgit operations.

    This class provides thread-safe logging capabilities with optimized storage
    using SQLite and the resource manager for M4 systems.
    """

    _instance = None
    _lock = threading.Lock()
    _log_queue: Queue = Queue()
    _is_processing = False

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the logger.

        Args:
            db_path: Optional path to the log database. If None, uses default location.
        """
        if hasattr(self, "_initialized"):
            return

        self._initialized = True

        # Set up database path
        if db_path is None:
            home = os.path.expanduser("~")
            self.db_path = os.path.join(home, ".qgit", "logs", "qgit.db")
        else:
            self.db_path = db_path

        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Initialize resource manager
        self.resource_manager = get_resource_manager(
            Path(os.path.dirname(self.db_path))
        )

        # Initialize database
        self._init_db()

        # Start background processing
        self._start_background_processing()

    def _init_db(self):
        """Initialize the SQLite database with optimized settings."""
        with self._get_db() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    command TEXT NOT NULL,
                    message TEXT NOT NULL,
                    metadata TEXT,
                    status TEXT,
                    duration REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON logs(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_command ON logs(command)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_level ON logs(level)")

            # Set pragmas for optimization
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")

    @contextmanager
    def _get_db(self):
        """Get a database connection with automatic cleanup."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise FileOperationError(
                f"Database error: {str(e)}", filepath=self.db_path, operation="database"
            )
        finally:
            if conn:
                conn.close()

    def _start_background_processing(self):
        """Start background processing of log queue using ResourceManager."""

        async def process_entries(entries):
            """Process a batch of log entries using ResourceManager."""
            try:
                await self.resource_manager.perf_optimizer.run_io_bound(
                    self._write_entries_to_db, entries
                )
            except Exception as e:
                print(f"Error writing entries to database: {e}")

        def process_queue():
            """Main queue processing loop with improved error handling."""
            while True:
                try:
                    entries = []
                    # Process up to 100 entries at a time
                    for _ in range(100):
                        try:
                            entry = self._log_queue.get_nowait()
                            entries.append(entry)
                        except Empty:
                            break

                    if entries:
                        # Use asyncio to process entries
                        asyncio.run(process_entries(entries))
                    else:
                        # Use resource manager's optimized sleep
                        asyncio.run(asyncio.sleep(0.1))

                except Exception as e:
                    print(f"Error in queue processing: {e}")
                    asyncio.run(asyncio.sleep(1))

        # Start processing thread
        thread = threading.Thread(target=process_queue, daemon=True)
        thread.start()

    def _write_entries_to_db(self, entries: List[LogEntry]):
        """Write entries to database with optimized batch processing."""
        with self._get_db() as conn:
            conn.executemany(
                """
                INSERT INTO logs 
                (timestamp, level, command, message, metadata, status, duration)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        e.timestamp,
                        e.level,
                        e.command,
                        e.message,
                        json.dumps(e.metadata),
                        e.status,
                        e.duration,
                    )
                    for e in entries
                ],
            )

    def log(
        self,
        level: str,
        command: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "success",
        duration: float = 0.0,
    ):
        """Log a qgit operation with memory-optimized metadata handling."""
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            command=command,
            message=message,
            metadata=self.resource_manager.memory_manager.get_cached_data(str(metadata))
            or metadata
            or {},
            status=status,
            duration=duration,
        )
        self._log_queue.put(entry)

    def get_logs(
        self,
        limit: int = 100,
        level: Optional[str] = None,
        command: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get logs with optional filtering.

        Args:
            limit: Maximum number of logs to return
            level: Optional level filter
            command: Optional command filter
            start_date: Optional start date filter (ISO format)
            end_date: Optional end date filter (ISO format)

        Returns:
            List of log entries as dictionaries
        """
        query = "SELECT * FROM logs WHERE 1=1"
        params = []

        if level:
            query += " AND level = ?"
            params.append(level)

        if command:
            query += " AND command = ?"
            params.append(command)

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._get_db() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [
                {
                    "timestamp": row["timestamp"],
                    "level": row["level"],
                    "command": row["command"],
                    "message": row["message"],
                    "metadata": json.loads(row["metadata"]),
                    "status": row["status"],
                    "duration": row["duration"],
                }
                for row in rows
            ]

    async def cleanup_old_logs(self, days: int = 30):
        """Clean up logs older than specified days.

        Args:
            days: Number of days of logs to keep
        """
        cutoff_date = (
            datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            - timedelta(days=days)
        ).isoformat()

        with self._get_db() as conn:
            conn.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff_date,))
            conn.execute("VACUUM")  # Reclaim space

    async def optimize_storage(self):
        """Optimize database storage using resource manager."""
        try:
            # Use resource manager to optimize cache
            await self.resource_manager.cache_manager.optimize_cache()

            # Optimize database
            with self._get_db() as conn:
                conn.execute("PRAGMA optimize")
                conn.execute("ANALYZE")
        except Exception as e:
            print(f"Error optimizing log storage: {e}")

    async def cleanup(self):
        """Cleanup resources using ResourceManager."""
        try:
            await self.resource_manager.cleanup()
        except Exception as e:
            print(f"Error during logger cleanup: {e}")


# Global logger instance
logger = QGitLogger()
