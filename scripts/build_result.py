"""
Shared BuildResult dataclass for build steps to return metadata.
"""
from dataclasses import dataclass, field

@dataclass
class BuildResult:
    """Result from a build step, optionally containing metadata."""
    success: bool
    data: dict = field(default_factory=dict)
