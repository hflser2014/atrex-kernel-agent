"""Validated legacy problem facts without execution or evaluation side effects."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class LoadedProblem:
    name: str
    directory: Path
    reference: Path
    bench_root: Path | None
    public_contract: Path | None
    public_contract_source: Literal["none", "provided", "auto"]

