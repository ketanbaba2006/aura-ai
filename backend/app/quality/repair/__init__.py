"""
Autonomous Repair Engine

Provides safe, bounded, rollback-capable autonomous repair of defects
found by the quality engine, with Global Repair Registry integration.
"""

from app.quality.repair.engine import (
    AutonomousRepairEngine,
    SafePatcher,
    RepairAttempt,
    RepairResult,
    repair_engine,
)

__all__ = [
    "AutonomousRepairEngine",
    "SafePatcher",
    "RepairAttempt",
    "RepairResult",
    "repair_engine",
]
