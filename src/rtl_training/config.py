from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .datasets import DatasetManifest
from .reward import VerifierRewardConfig


@dataclass(frozen=True)
class ToolBudgetConfig:
    max_steps: int
    max_cost: float

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "ToolBudgetConfig":
        return cls(
            max_steps=int(raw["max_steps"]),
            max_cost=float(raw["max_cost"]),
        )


@dataclass(frozen=True)
class TrainingDatasets:
    train: tuple[str, ...]
    eval: tuple[str, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "TrainingDatasets":
        return cls(
            train=tuple(str(item) for item in raw["train"]),
            eval=tuple(str(item) for item in raw["eval"]),
        )

    def all_names(self) -> tuple[str, ...]:
        return self.train + self.eval


@dataclass(frozen=True)
class VerifierTrainingConfig:
    base_model: str
    renderer_name: str
    loss_fn: str
    group_size: int
    max_new_tokens: int
    episodes_per_step: int
    budget: ToolBudgetConfig
    reward: VerifierRewardConfig
    datasets: TrainingDatasets

    @classmethod
    def load(cls, path: str | Path) -> "VerifierTrainingConfig":
        raw = json.loads(Path(path).read_text())
        return cls(
            base_model=str(raw["base_model"]),
            renderer_name=str(raw["renderer_name"]),
            loss_fn=str(raw["loss_fn"]),
            group_size=int(raw["group_size"]),
            max_new_tokens=int(raw["max_new_tokens"]),
            episodes_per_step=int(raw["episodes_per_step"]),
            budget=ToolBudgetConfig.from_dict(raw["budget"]),
            reward=VerifierRewardConfig.from_dict(raw["reward"]),
            datasets=TrainingDatasets.from_dict(raw["datasets"]),
        )

    def validate_against_manifest(self, manifest: DatasetManifest) -> tuple[str, ...]:
        return manifest.validate_dataset_names(self.datasets.all_names())
