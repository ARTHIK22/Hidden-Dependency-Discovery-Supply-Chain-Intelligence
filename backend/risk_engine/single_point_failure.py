"""Single-provider dependency detection."""

from __future__ import annotations


def single_source(dependency_count: int) -> tuple[bool, str]:
    if dependency_count == 1:
        return True, "Exactly one verified direct dependency is present in the investigation graph; alternatives are not represented in available data."
    if dependency_count > 1:
        return False, f"{dependency_count} verified direct dependencies are represented; supplier market shares are not inferred."
    return False, "No verified direct dependencies are available for single-source analysis."
