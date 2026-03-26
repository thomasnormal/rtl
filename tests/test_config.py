from pathlib import Path

from rtl_training.config import VerifierTrainingConfig
from rtl_training.datasets import DatasetManifest


ROOT = Path(__file__).resolve().parents[1]


def test_training_config_matches_manifest() -> None:
    manifest = DatasetManifest.load(ROOT / "configs" / "datasets.json")
    config = VerifierTrainingConfig.load(ROOT / "configs" / "verifier_smoke.json")
    assert config.validate_against_manifest(manifest) == ()
