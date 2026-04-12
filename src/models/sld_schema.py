"""Core domain models for SLD interpretation."""
from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum
from typing import Annotated, Literal
from pydantic import BaseModel, Field, field_validator

class ComponentType(str, Enum):
    TRANSFORMER_2W = "transformer_2w"
    TRANSFORMER_3W = "transformer_3w"
    BUSBAR = "busbar"
    CIRCUIT_BREAKER = "circuit_breaker"
    DISCONNECT_SWITCH = "disconnect_switch"
    LOAD_BREAK_SWITCH = "load_break_switch"
    CURRENT_TRANSFORMER = "current_transformer"
    VOLTAGE_TRANSFORMER = "voltage_transformer"
    REACTOR = "reactor"
    CAPACITOR = "capacitor"
    GENERATOR = "generator"
    MOTOR = "motor"
    FEEDER_TERMINAL = "feeder_terminal"
    JUMPER = "jumper"
    GROUND = "ground"
    SURGE_ARRESTER = "surge_arrester"
    FUSE = "fuse"
    UNKNOWN = "unknown"

class ConnectionType(str, Enum):
    AC_LINE = "ac_line"
    FEEDER = "feeder"
    JUMPER = "jumper"
    GROUND_CONNECTION = "ground_connection"
    CONTROL_WIRE = "control_wire"
    DIRECT = "direct"  # used internally by graph builder

class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class Point(BaseModel):
    x: float
    y: float

class BoundingBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min

    @property
    def center_x(self) -> float:
        return (self.x_min + self.x_max) / 2

    @property
    def center_y(self) -> float:
        return (self.y_min + self.y_max) / 2

class Component(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    component_type: ComponentType
    label: str | None = None
    voltage_level: str | None = None
    position: Point
    bbox: BoundingBox | None = None
    confidence: float = 1.0
    connected_to: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    def __repr__(self):
        return f"<Component {self.id}[{self.component_type.value}] '{self.label}' @{self.position.x:.0f},{self.position.y:.0f}>"

class Connection(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    from_component: str
    to_component: str
    connection_type: ConnectionType = ConnectionType.AC_LINE
    intermediate_points: list[Point] = Field(default_factory=list)
    label: str | None = None

class BusSection(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    label: str
    voltage: str | None = None
    component_ids: list[str] = Field(default_factory=list)

class Bus(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    voltage_level: str
    component_ids: list[str] = Field(default_factory=list)

class NetworkGraph(BaseModel):
    nodes: list[Component] = Field(default_factory=list)
    edges: list[Connection] = Field(default_factory=list)
    buses: list[Bus] = Field(default_factory=list)

class ValidationIssue(BaseModel):
    severity: ValidationSeverity
    message: str
    component_ids: list[str] = Field(default_factory=list)
    rule_name: str

class ValidationResult(BaseModel):
    is_valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)

class ConfidenceSummary(BaseModel):
    avg_symbol_confidence: float
    avg_ocr_confidence: float
    avg_connectivity_confidence: float

class ExtractedSLD(BaseModel):
    version: str = "1.0"
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    source_filename: str | None = None
    voltage_levels: list[str] = Field(default_factory=list)
    components: list[Component] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)
    buses: list[Bus] = Field(default_factory=list)
    network_graph: NetworkGraph | None = None
    validation: ValidationResult | None = None
    confidence: ConfidenceSummary | None = None
    metadata: dict = Field(default_factory=dict)

    def to_json(self, **kwargs) -> str:
        return self.model_dump_json(**kwargs)

    def to_dict(self, **kwargs) -> dict:
        return self.model_dump(**kwargs)
