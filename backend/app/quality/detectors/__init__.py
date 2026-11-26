"""
Technology Detection Adapters
"""

from app.quality.detectors.base import (
    TechnologyDetector,
    BaseTechnologyDetector,
    WebTechnologyDetector,
    PythonTechnologyDetector,
    NodeTechnologyDetector,
    MobileTechnologyDetector,
    DatabaseTechnologyDetector,
    GenericDetector,
    TechnologySignature,
    TechnologyDetectionResult,
)

__all__ = [
    "TechnologyDetector",
    "BaseTechnologyDetector",
    "WebTechnologyDetector",
    "PythonTechnologyDetector",
    "NodeTechnologyDetector",
    "MobileTechnologyDetector",
    "DatabaseTechnologyDetector",
    "GenericDetector",
    "TechnologySignature",
    "TechnologyDetectionResult",
]
