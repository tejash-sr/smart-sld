"""Domain rule engine for SLD validation."""
from __future__ import annotations
import re
from src.models.sld_schema import (
    ComponentType, ExtractedSLD, ValidationResult,
    ValidationSeverity, ValidationIssue, Component
)

VOLTAGE_ORDER = [
    "765kV", "400kV", "220kV", "132kV", "66kV", "33kV", "22kV",
    "11kV", "6.6kV", "3.3kV", "2.3kV", "0.415kV", "415V",
]

class VoltageHierarchyValidator:
    """Validates voltage level consistency in SLD."""

    VOLTAGE_KV = {v: float(v.lower().replace("k", "").replace("v", "").replace(".", ""))
                  for v in VOLTAGE_ORDER}

    def __init__(self):
        self._voltage_re = re.compile(r"(\d+\.?\d*)\s*kV", re.IGNORECASE)
        self._voltage_order_rev = {v: i for i, v in enumerate(VOLTAGE_ORDER)}

    def extract_kv(self, voltage_str: str | None) -> float | None:
        if not voltage_str:
            return None
        m = self._voltage_re.search(str(voltage_str))
        return float(m.group(1)) if m else None

    def voltage_rank(self, voltage_str: str | None) -> int | None:
        if not voltage_str:
            return None
        kv = self.extract_kv(voltage_str)
        if kv is None:
            return None
        return self._voltage_order_rev.get(f"{kv}kV")

    def validate(self, sld: ExtractedSLD) -> ValidationResult:
        issues = []
        for comp in sld.components:
            issues.extend(self._check_transformer_voltage_consistency(comp, sld.components))
        for conn in sld.connections:
            issues.extend(self._check_connection_voltage_compatibility(conn, sld.components))
        issues.extend(self._check_orphan_components(sld))
        issues.extend(self._check_busbar_isolation(sld))
        return ValidationResult(
            is_valid=not any(i.severity == ValidationSeverity.ERROR for i in issues),
            issues=issues,
        )

    def _check_transformer_voltage_consistency(self, comp: Component, all_comps: list[Component]) -> list[ValidationIssue]:
        if comp.component_type not in (ComponentType.TRANSFORMER_2W, ComponentType.TRANSFORMER_3W):
            return []
        if not comp.voltage_level:
            return [ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"Transformer '{comp.label or comp.id}' has no voltage level",
                component_ids=[comp.id],
                rule_name="transformer_voltage_required",
            )]
        return []

    def _check_connection_voltage_compatibility(self, conn, all_comps: list[Component]) -> list[ValidationIssue]:
        from_comp = next((c for c in all_comps if c.id == conn.from_component), None)
        to_comp = next((c for c in all_comps if c.id == conn.to_component), None)
        if not from_comp or not to_comp:
            return [ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Connection '{conn.id}' references unknown component",
                component_ids=[conn.from_component, conn.to_component],
                rule_name="connection_refs_valid_component",
            )]
        if from_comp.voltage_level and to_comp.voltage_level:
            if from_comp.voltage_level != to_comp.voltage_level:
                rank_a = self.voltage_rank(from_comp.voltage_level)
                rank_b = self.voltage_rank(to_comp.voltage_level)
                if rank_a is not None and rank_b is not None:
                    diff = abs(rank_a - rank_b)
                    if diff > 2:
                        return [ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            message=f"Connection between mismatched voltages "
                                    f"'{from_comp.voltage_level}' and '{to_comp.voltage_level}' "
                                    f"(likely requires transformer)",
                            component_ids=[from_comp.id, to_comp.id],
                            rule_name="connection_voltage_compatibility",
                        )]
        return []

    def _check_orphan_components(self, sld: ExtractedSLD) -> list[ValidationIssue]:
        if not sld.connections:
            return [ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message="No connections detected — all components may be orphans",
                component_ids=[],
                rule_name="orphan_components",
            )]
        connected = {c for conn in sld.connections for c in [conn.from_component, conn.to_component]}
        orphans = [c for c in sld.components if c.id not in connected]
        if orphans:
            return [ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"{len(orphans)} orphan component(s) with no connections",
                component_ids=[c.id for c in orphans],
                rule_name="orphan_components",
            )]
        return []

    def _check_busbar_isolation(self, sld: ExtractedSLD) -> list[ValidationIssue]:
        busbars = {c.id for c in sld.components if c.component_type == ComponentType.BUSBAR}
        if len(busbars) < 2:
            return []
        issues = []
        conn_map: dict[str, set[str]] = {c.id: set() for c in sld.components}
        for conn in sld.connections:
            conn_map.setdefault(conn.from_component, set()).add(conn.to_component)
            conn_map.setdefault(conn.to_component, set()).add(conn.from_component)
        busbar_connected_to = {b: conn_map.get(b, set()) - busbars for b in busbars}
        for b_id, connected_to in busbar_connected_to.items():
            if not connected_to:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Busbar '{b_id}' has no connections to other busbars or components",
                    component_ids=[b_id],
                    rule_name="busbar_isolation",
                ))
        return issues


class RuleEngine:
    """Orchestrates all validation rules."""

    def __init__(self):
        self.validators = [VoltageHierarchyValidator()]

    def validate(self, sld: ExtractedSLD) -> ValidationResult:
        all_issues: list[ValidationIssue] = []
        for validator in self.validators:
            result = validator.validate(sld)
            all_issues.extend(result.issues)
        return ValidationResult(
            is_valid=not any(i.severity == ValidationSeverity.ERROR for i in all_issues),
            issues=all_issues,
        )
