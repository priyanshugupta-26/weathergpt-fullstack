"""WeatherGPT ML Model Registry and Storage Manager.
Handles artifact serialization, champion/challenger lifecycle, smoke testing, and atomic model swapping.
"""

import json
import logging
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, update

from backend.config import ROOT
from backend.database import Session, ModelVersion
from backend.ml.features import feature_registry, FeatureValidator

log = logging.getLogger("weathergpt.ml.registry")

REGISTRY_BASE = ROOT / "models" / "registry" / "weather"
REGISTRY_BASE.mkdir(parents=True, exist_ok=True)


class LoadedModelInfo:
    def __init__(self, model: Any, metadata: dict[str, Any], feature_names: list[str], target_names: list[str]):
        self.model = model
        self.metadata = metadata
        self.feature_names = feature_names
        self.target_names = target_names
        self.version = metadata.get("version", "unknown")


class ModelRegistry:
    """Thread-safe model registry managing versioned storage and the active Champion model."""

    def __init__(self):
        self._active_champion: LoadedModelInfo | None = None
        self.base_dir = REGISTRY_BASE

    @property
    def active_champion(self) -> LoadedModelInfo | None:
        return self._active_champion

    def next_version_tag(self) -> str:
        with Session() as db:
            count = db.scalar(select(ModelVersion).order_by(ModelVersion.id.desc()))
            if not count:
                return "v001"
            last_ver = count.version
            try:
                num = int(last_ver.lstrip("v")) + 1
                return f"v{num:03d}"
            except Exception:
                return f"v{count.id + 1:03d}"

    def get_version_dir(self, version: str) -> Path:
        p = self.base_dir / version
        p.mkdir(parents=True, exist_ok=True)
        return p

    def save_artifact(
        self,
        version: str,
        model: Any,
        metadata: dict[str, Any],
        metrics: dict[str, Any],
        features: list[str],
        targets: list[str],
    ) -> Path:
        """Saves a complete versioned artifact bundle into models/registry/weather/vXXX/."""
        v_dir = self.get_version_dir(version)
        model_path = v_dir / "model.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(model, f, protocol=pickle.HIGHEST_PROTOCOL)

        (v_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
        (v_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
        (v_dir / "feature_schema.json").write_text(json.dumps({"features": features, "count": len(features)}, indent=2))
        (v_dir / "target_schema.json").write_text(json.dumps({"targets": targets, "count": len(targets)}, indent=2))

        return model_path

    def load_artifact(self, artifact_path: str | Path) -> LoadedModelInfo:
        """Loads and smoke-tests an artifact from disk."""
        path = Path(artifact_path)
        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found at {path}")

        v_dir = path.parent
        meta_file = v_dir / "metadata.json"
        feat_file = v_dir / "feature_schema.json"
        targ_file = v_dir / "target_schema.json"

        if not (meta_file.exists() and feat_file.exists() and targ_file.exists()):
            raise ValueError(f"Incomplete artifact manifest in {v_dir}")

        metadata = json.loads(meta_file.read_text())
        features = json.loads(feat_file.read_text()).get("features", [])
        targets = json.loads(targ_file.read_text()).get("targets", [])

        with open(path, "rb") as f:
            model = pickle.load(f)

        # Smoke prediction check
        dummy_input = [[0.0] * len(features)]
        try:
            preds = model.predict(dummy_input)
            if preds is None:
                raise ValueError("Model smoke prediction returned None")
        except Exception as e:
            raise RuntimeError(f"Smoke test prediction failed for {path}: {e}")

        return LoadedModelInfo(model, metadata, features, targets)

    def load_active_champion(self) -> LoadedModelInfo | None:
        """Loads the current production CHAMPION model into cache."""
        with Session() as db:
            champ_row = db.scalar(
                select(ModelVersion).where(ModelVersion.status == "CHAMPION").order_by(ModelVersion.id.desc())
            )
            if not champ_row:
                # Discover bundled artifacts on disk if database is fresh
                if self.base_dir.exists():
                    subdirs = sorted([d for d in self.base_dir.iterdir() if d.is_dir() and (d / "model.pkl").exists()], key=lambda p: p.name)
                    if subdirs:
                        latest_dir = subdirs[-1]
                        meta_file = latest_dir / "metadata.json"
                        meta = {}
                        if meta_file.exists():
                            try:
                                meta = json.loads(meta_file.read_text())
                            except Exception:
                                pass

                        metrics_file = latest_dir / "metrics.json"
                        metrics = {}
                        if metrics_file.exists():
                            try:
                                metrics = json.loads(metrics_file.read_text())
                            except Exception:
                                pass

                        champ_row = ModelVersion(
                            model_name="weathergpt_ml",
                            model_type="multi_output_regressor",
                            version=latest_dir.name,
                            status="CHAMPION",
                            algorithm=meta.get("algorithm", "HistGradientBoosting"),
                            artifact_path=str(latest_dir / "model.pkl"),
                            training_rows=meta.get("training_rows", 0),
                            metrics=json.dumps(metrics),
                            promotion_reason="Initial baseline from model registry",
                        )
                        with Session.begin() as save_db:
                            save_db.add(champ_row)
                        log.info("Auto-registered baseline champion %s from filesystem", latest_dir.name)

            if not champ_row:
                log.info("No active CHAMPION found in database or filesystem.")
                return None

            try:
                loaded = self.load_artifact(champ_row.artifact_path)
                self._active_champion = loaded
                log.info("Loaded CHAMPION model version %s (%s)", loaded.version, champ_row.algorithm)
                return loaded
            except Exception as e:
                log.error("Failed to load active champion from %s: %s", champ_row.artifact_path, e)
                return None

    def promote_challenger(self, challenger_id_or_version: int | str, reason: str = "Surpassed Champion metrics") -> bool:
        """Atomically promotes a Challenger model to Champion after validation."""
        with Session.begin() as db:
            if isinstance(challenger_id_or_version, int):
                challenger = db.get(ModelVersion, challenger_id_or_version)
            else:
                challenger = db.scalar(select(ModelVersion).where(ModelVersion.version == challenger_id_or_version))

            if not challenger:
                raise ValueError(f"Challenger model {challenger_id_or_version} not found")

            # Load and smoke test before database change
            loaded = self.load_artifact(challenger.artifact_path)

            # Demote existing champion(s)
            current_champs = db.scalars(select(ModelVersion).where(ModelVersion.status == "CHAMPION")).all()
            for champ in current_champs:
                champ.status = "ARCHIVED"

            # Promote challenger
            challenger.status = "CHAMPION"
            challenger.promotion_reason = reason

            # Atomic swap in memory
            self._active_champion = loaded
            log.info("PROMOTED model %s to active CHAMPION! Reason: %s", challenger.version, reason)
            return True

    def reject_challenger(self, challenger_id_or_version: int | str, reason: str = "Did not improve on Champion") -> bool:
        """Marks a Challenger model as REJECTED, preserving the current Champion intact."""
        with Session.begin() as db:
            if isinstance(challenger_id_or_version, int):
                challenger = db.get(ModelVersion, challenger_id_or_version)
            else:
                challenger = db.scalar(select(ModelVersion).where(ModelVersion.version == challenger_id_or_version))

            if not challenger:
                return False

            challenger.status = "REJECTED"
            challenger.promotion_reason = f"Rejected: {reason}"
            log.info("REJECTED model %s: %s", challenger.version, reason)
            return True

    def rollback(self, target_version: str) -> bool:
        """Rolls back production Champion to a previously validated version."""
        with Session.begin() as db:
            target = db.scalar(select(ModelVersion).where(ModelVersion.version == target_version))
            if not target:
                raise ValueError(f"Target model version {target_version} not found")

            # Verify artifact exists and passes smoke test
            loaded = self.load_artifact(target.artifact_path)

            current_champs = db.scalars(select(ModelVersion).where(ModelVersion.status == "CHAMPION")).all()
            for champ in current_champs:
                champ.status = "ARCHIVED"

            target.status = "CHAMPION"
            target.promotion_reason = f"Manual admin rollback on {datetime.now(timezone.utc).isoformat()}"

            self._active_champion = loaded
            log.info("Successfully rolled back production Champion to %s", target_version)
            return True

    def predict(self, features: dict[str, float] | list[float]) -> dict[str, Any] | None:
        """Runs inference using the cached active Champion model."""
        if self._active_champion is None:
            self.load_active_champion()
        if self._active_champion is None:
            return None

        # Validate feature order and finite numbers
        expected_features = self._active_champion.feature_names
        val_vector = FeatureValidator.validate_features(features, expected_features)

        raw_pred = self._active_champion.model.predict([val_vector])

        # Extract predictions for all target variables
        target_names = self._active_champion.target_names
        pred_dict = {}

        if hasattr(raw_pred, "ndim") and raw_pred.ndim > 1:
            row = raw_pred[0]
        else:
            row = raw_pred

        if hasattr(row, "tolist"):
            row = row.tolist()

        if isinstance(row, (list, tuple)):
            for idx, val in enumerate(row):
                t_name = target_names[idx] if idx < len(target_names) else f"target_{idx+1}"
                pred_dict[t_name] = round(float(val), 2)
        else:
            # Single scalar output
            t_name = target_names[0] if target_names else "predicted_value"
            pred_dict[t_name] = round(float(row), 2)

        return {
            "prediction": pred_dict,
            "version": self._active_champion.version,
            "algorithm": self._active_champion.metadata.get("algorithm", "HistGradientBoosting"),
            "mode": "WeatherGPT Own Model (Champion)",
            "model_source": f"models/registry/weather/{self._active_champion.version}/model.pkl",
        }


model_registry = ModelRegistry()
