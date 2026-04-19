"""Audit trail for topology changes and operations."""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AuditLog:
    """SQLite-based audit trail for all topology operations."""
    
    def __init__(self, db_path: str = "data/audit.db"):
        """Initialize audit database."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True, parents=True)
        
        self._init_schema()
    
    def _init_schema(self):
        """Create database schema if not exists."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                user_id TEXT,
                batch_id TEXT,
                source TEXT,
                object_id TEXT,
                object_type TEXT,
                action TEXT NOT NULL,
                details TEXT,
                severity TEXT
            )
        """)
        
        # Create indices for fast queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_type ON audit_events(event_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_id ON audit_events(batch_id)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Audit database initialized at {self.db_path}")
    
    def log_ingestion(self, batch_id: str, source: str, 
                      component_count: int, connection_count: int,
                      user_id: str = "system"):
        """Log SLD ingestion event."""
        self._log_event(
            event_type="ingestion",
            action="ingest_sld",
            user_id=user_id,
            batch_id=batch_id,
            source=source,
            details=json.dumps({
                "components": component_count,
                "connections": connection_count
            }),
            severity="info"
        )
    
    def log_comparison(self, old_batch_id: str, new_batch_id: str,
                       differences: dict, user_id: str = "system"):
        """Log SLD comparison/diff operation."""
        self._log_event(
            event_type="comparison",
            action="compare_sld",
            user_id=user_id,
            batch_id=new_batch_id,
            details=json.dumps({
                "old_batch": old_batch_id,
                "new_batch": new_batch_id,
                "components_added": differences.get("components_added"),
                "components_removed": differences.get("components_removed"),
                "connections_added": differences.get("connections_added"),
                "connections_removed": differences.get("connections_removed"),
            }),
            severity="info"
        )
    
    def log_anomaly_detected(self, batch_id: str, anomaly_type: str,
                            object_id: str, object_type: str,
                            description: str, severity: str = "warning",
                            user_id: str = "system"):
        """Log anomaly detection."""
        self._log_event(
            event_type="anomaly_detected",
            action=f"anomaly_{anomaly_type}",
            user_id=user_id,
            batch_id=batch_id,
            object_id=object_id,
            object_type=object_type,
            details=json.dumps({"description": description}),
            severity=severity
        )
    
    def log_fault_analysis(self, batch_id: str, fault_location: str,
                          affected_areas: list[str], user_id: str = "system"):
        """Log fault analysis operation."""
        self._log_event(
            event_type="fault_analysis",
            action="analyze_fault",
            user_id=user_id,
            batch_id=batch_id,
            object_id=fault_location,
            details=json.dumps({"affected_areas": affected_areas}),
            severity="critical"
        )
    
    def log_unauthorized_change(self, batch_id: str, change_type: str,
                               object_id: str, description: str,
                               user_id: str = "unknown"):
        """Log potential unauthorized modification."""
        self._log_event(
            event_type="unauthorized_change",
            action=f"change_{change_type}",
            user_id=user_id,
            batch_id=batch_id,
            object_id=object_id,
            details=json.dumps({"description": description}),
            severity="critical"
        )
    
    def _log_event(self, event_type: str, action: str, user_id: str,
                   batch_id: Optional[str] = None, source: Optional[str] = None,
                   object_id: Optional[str] = None, object_type: Optional[str] = None,
                   details: Optional[str] = None, severity: str = "info"):
        """Internal method to log an event."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO audit_events 
            (timestamp, event_type, user_id, batch_id, source, object_id, 
             object_type, action, details, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            event_type,
            user_id,
            batch_id,
            source,
            object_id,
            object_type,
            action,
            details,
            severity
        ))
        
        conn.commit()
        conn.close()
    
    def get_recent_events(self, limit: int = 100, event_type: Optional[str] = None) -> list[dict]:
        """Get recent audit events."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if event_type:
            cursor.execute("""
                SELECT * FROM audit_events 
                WHERE event_type = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (event_type, limit))
        else:
            cursor.execute("""
                SELECT * FROM audit_events 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_batch_history(self, batch_id: str) -> list[dict]:
        """Get all events related to a specific batch."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM audit_events 
            WHERE batch_id = ? 
            ORDER BY timestamp ASC
        """, (batch_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_critical_events(self, limit: int = 50) -> list[dict]:
        """Get critical severity events."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM audit_events 
            WHERE severity IN ('critical', 'error')
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
