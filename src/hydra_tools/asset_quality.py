"""
Asset Quality Scoring System for Empire of Broken Queens

Phase 12 module providing automated quality assessment of generated assets.
Evaluates technical quality, style consistency, and character accuracy.

Quality Metrics:
- Technical: Resolution, artifacts, noise level
- Composition: Face detection, symmetry, framing
- Style: Consistency with reference, color palette
- Character: Identity matching, expression accuracy
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class QualityTier(Enum):
    """Quality tier classifications."""
    EXCELLENT = "excellent"  # 90-100
    GOOD = "good"            # 75-89
    ACCEPTABLE = "acceptable"  # 60-74
    POOR = "poor"            # 40-59
    REJECT = "reject"        # 0-39


class QualityDimension(Enum):
    """Dimensions of quality assessment."""
    TECHNICAL = "technical"
    COMPOSITION = "composition"
    STYLE = "style"
    CHARACTER = "character"


@dataclass
class QualityScore:
    """Quality score for a single dimension."""
    dimension: QualityDimension
    score: float  # 0-100
    details: Dict[str, Any] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class AssetQualityReport:
    """Complete quality report for an asset."""
    asset_id: str
    asset_path: str
    timestamp: str
    overall_score: float
    tier: QualityTier
    dimension_scores: Dict[str, QualityScore]
    passed: bool
    auto_action: str  # "approve", "review", "reject"
    metadata: Dict[str, Any] = field(default_factory=dict)


class QualityThresholds(BaseModel):
    """Configurable quality thresholds."""
    min_resolution: int = 768
    max_aspect_ratio_deviation: float = 0.3
    min_technical_score: float = 60.0
    min_overall_score: float = 65.0
    auto_approve_threshold: float = 85.0
    auto_reject_threshold: float = 40.0


class AssetQualityScorer:
    """
    Automated quality scoring for generated assets.

    Evaluates images based on multiple dimensions and provides
    actionable feedback for the generation pipeline.
    """

    def __init__(
        self,
        thresholds: Optional[QualityThresholds] = None,
        qdrant_url: str = "http://192.168.1.244:6333",
        storage_path: str = "/data/quality_reports",
    ):
        """
        Initialize the quality scorer.

        Args:
            thresholds: Quality thresholds for pass/fail decisions
            qdrant_url: URL to Qdrant for reference embeddings
            storage_path: Path to store quality reports
        """
        self.thresholds = thresholds or QualityThresholds()
        self.qdrant_url = qdrant_url
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._reports: Dict[str, AssetQualityReport] = {}
        self._load_reports()

    def _load_reports(self) -> None:
        """Load existing quality reports from storage."""
        reports_file = self.storage_path / "reports.json"
        if reports_file.exists():
            try:
                data = json.loads(reports_file.read_text())
                for report_data in data.get("reports", []):
                    report = AssetQualityReport(
                        asset_id=report_data["asset_id"],
                        asset_path=report_data["asset_path"],
                        timestamp=report_data["timestamp"],
                        overall_score=report_data["overall_score"],
                        tier=QualityTier(report_data["tier"]),
                        dimension_scores={},
                        passed=report_data["passed"],
                        auto_action=report_data["auto_action"],
                        metadata=report_data.get("metadata", {}),
                    )
                    self._reports[report.asset_id] = report
            except Exception as e:
                logger.warning(f"Failed to load quality reports: {e}")

    def _save_reports(self) -> None:
        """Save quality reports to storage."""
        reports_file = self.storage_path / "reports.json"
        data = {
            "reports": [
                {
                    "asset_id": r.asset_id,
                    "asset_path": r.asset_path,
                    "timestamp": r.timestamp,
                    "overall_score": r.overall_score,
                    "tier": r.tier.value,
                    "passed": r.passed,
                    "auto_action": r.auto_action,
                    "metadata": r.metadata,
                }
                for r in self._reports.values()
            ],
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        reports_file.write_text(json.dumps(data, indent=2))

    def _generate_asset_id(self, asset_path: str) -> str:
        """Generate a unique ID for an asset."""
        hash_input = f"{asset_path}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def score_technical(self, image_info: Dict[str, Any]) -> QualityScore:
        """
        Score technical quality of an image.

        Checks resolution, format, file size, and basic image statistics.
        """
        issues = []
        suggestions = []
        details = {}
        score = 100.0

        # Resolution check
        width = image_info.get("width", 0)
        height = image_info.get("height", 0)
        details["resolution"] = f"{width}x{height}"

        if width < self.thresholds.min_resolution or height < self.thresholds.min_resolution:
            score -= 30
            issues.append(f"Resolution below minimum ({self.thresholds.min_resolution}px)")
            suggestions.append("Regenerate at higher resolution")
        elif width < 1024 or height < 1024:
            score -= 10
            suggestions.append("Consider higher resolution for print quality")

        # Aspect ratio check (should be close to 1:1 for portraits)
        aspect_ratio = width / height if height > 0 else 0
        details["aspect_ratio"] = round(aspect_ratio, 2)

        if abs(aspect_ratio - 1.0) > self.thresholds.max_aspect_ratio_deviation:
            score -= 15
            issues.append(f"Unusual aspect ratio for portrait: {aspect_ratio:.2f}")
            suggestions.append("Crop or regenerate with standard aspect ratio")

        # File format check
        file_format = image_info.get("format", "unknown").lower()
        details["format"] = file_format

        if file_format not in ["png", "webp", "jpg", "jpeg"]:
            score -= 10
            issues.append(f"Non-standard format: {file_format}")
            suggestions.append("Convert to PNG or WebP for best quality")

        # File size (too small might indicate low quality)
        file_size = image_info.get("file_size", 0)
        details["file_size_kb"] = round(file_size / 1024, 1)

        if file_size > 0 and file_size < 50000:  # Less than 50KB
            score -= 15
            issues.append("File size unusually small")
            suggestions.append("Check for compression artifacts")

        return QualityScore(
            dimension=QualityDimension.TECHNICAL,
            score=max(0, min(100, score)),
            details=details,
            issues=issues,
            suggestions=suggestions,
        )

    def score_composition(self, image_info: Dict[str, Any]) -> QualityScore:
        """
        Score composition quality.

        Checks face detection, centering, and framing.
        """
        issues = []
        suggestions = []
        details = {}
        score = 100.0

        # Face detection (if available)
        faces = image_info.get("faces", [])
        details["faces_detected"] = len(faces)

        if len(faces) == 0:
            # No face detection data - assume OK but note it
            details["face_detection"] = "not_available"
            score -= 5  # Small penalty for missing data
        elif len(faces) == 1:
            face = faces[0]
            # Check face centering
            face_center_x = face.get("center_x", 0.5)
            face_center_y = face.get("center_y", 0.5)

            if abs(face_center_x - 0.5) > 0.2:
                score -= 10
                issues.append("Face not centered horizontally")
            if abs(face_center_y - 0.4) > 0.2:  # Face should be slightly above center
                score -= 10
                issues.append("Face not positioned correctly vertically")

            # Check face size (should be prominent for portraits)
            face_area = face.get("area_ratio", 0)
            details["face_area_ratio"] = round(face_area, 3)

            if face_area < 0.1:
                score -= 15
                issues.append("Face too small in frame")
                suggestions.append("Zoom in or regenerate closer crop")
            elif face_area > 0.6:
                score -= 5
                issues.append("Face may be too close/cropped")
        elif len(faces) > 1:
            score -= 20
            issues.append(f"Multiple faces detected ({len(faces)})")
            suggestions.append("Regenerate focusing on single character")

        return QualityScore(
            dimension=QualityDimension.COMPOSITION,
            score=max(0, min(100, score)),
            details=details,
            issues=issues,
            suggestions=suggestions,
        )

    def score_style(
        self,
        image_info: Dict[str, Any],
        reference_embedding: Optional[List[float]] = None,
    ) -> QualityScore:
        """
        Score style consistency.

        Compares against reference style embeddings if available.
        """
        issues = []
        suggestions = []
        details = {}
        score = 85.0  # Start at good baseline without reference

        if reference_embedding and image_info.get("embedding"):
            # Calculate cosine similarity
            img_emb = image_info["embedding"]
            similarity = self._cosine_similarity(img_emb, reference_embedding)
            details["style_similarity"] = round(similarity, 3)

            if similarity > 0.9:
                score = 95.0
            elif similarity > 0.8:
                score = 85.0
            elif similarity > 0.7:
                score = 75.0
                suggestions.append("Style drifting from reference")
            elif similarity > 0.6:
                score = 60.0
                issues.append("Style inconsistent with reference")
                suggestions.append("Review prompt or regenerate with stronger guidance")
            else:
                score = 40.0
                issues.append("Style significantly different from reference")
                suggestions.append("Major prompt revision needed")
        else:
            details["reference_comparison"] = "not_available"

        # Check for common style issues based on metadata
        if image_info.get("has_text_artifacts"):
            score -= 15
            issues.append("Text artifacts detected")
            suggestions.append("Add text-related negatives to prompt")

        if image_info.get("watermark_detected"):
            score -= 25
            issues.append("Watermark detected")
            suggestions.append("Remove watermark or regenerate")

        return QualityScore(
            dimension=QualityDimension.STYLE,
            score=max(0, min(100, score)),
            details=details,
            issues=issues,
            suggestions=suggestions,
        )

    def score_character(
        self,
        image_info: Dict[str, Any],
        character_embedding: Optional[List[float]] = None,
        expected_emotion: Optional[str] = None,
    ) -> QualityScore:
        """
        Score character accuracy.

        Checks identity matching and expression accuracy.
        """
        issues = []
        suggestions = []
        details = {}
        score = 85.0  # Start at good baseline without reference

        # Character identity check
        if character_embedding and image_info.get("face_embedding"):
            face_emb = image_info["face_embedding"]
            identity_similarity = self._cosine_similarity(face_emb, character_embedding)
            details["identity_similarity"] = round(identity_similarity, 3)

            if identity_similarity > 0.85:
                score = 95.0
            elif identity_similarity > 0.75:
                score = 85.0
            elif identity_similarity > 0.65:
                score = 70.0
                issues.append("Character identity drifting")
                suggestions.append("Use stronger reference conditioning")
            else:
                score = 50.0
                issues.append("Character identity mismatch")
                suggestions.append("Regenerate with reference image")
        else:
            details["identity_comparison"] = "not_available"

        # Emotion/expression check
        if expected_emotion:
            detected_emotion = image_info.get("detected_emotion", "unknown")
            details["expected_emotion"] = expected_emotion
            details["detected_emotion"] = detected_emotion

            if detected_emotion == "unknown":
                pass  # No penalty for missing detection
            elif detected_emotion.lower() == expected_emotion.lower():
                score += 5
            else:
                score -= 10
                issues.append(f"Emotion mismatch: expected {expected_emotion}, got {detected_emotion}")
                suggestions.append("Adjust emotion keywords in prompt")

        return QualityScore(
            dimension=QualityDimension.CHARACTER,
            score=max(0, min(100, score)),
            details=details,
            issues=issues,
            suggestions=suggestions,
        )

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _determine_tier(self, score: float) -> QualityTier:
        """Determine quality tier from overall score."""
        if score >= 90:
            return QualityTier.EXCELLENT
        elif score >= 75:
            return QualityTier.GOOD
        elif score >= 60:
            return QualityTier.ACCEPTABLE
        elif score >= 40:
            return QualityTier.POOR
        else:
            return QualityTier.REJECT

    def _determine_action(self, score: float, passed: bool) -> str:
        """Determine automatic action based on score."""
        if score >= self.thresholds.auto_approve_threshold:
            return "approve"
        elif score < self.thresholds.auto_reject_threshold:
            return "reject"
        else:
            return "review"

    def evaluate_asset(
        self,
        asset_path: str,
        image_info: Dict[str, Any],
        reference_embedding: Optional[List[float]] = None,
        character_embedding: Optional[List[float]] = None,
        expected_emotion: Optional[str] = None,
    ) -> AssetQualityReport:
        """
        Perform full quality evaluation of an asset.

        Args:
            asset_path: Path to the asset file
            image_info: Dictionary with image metadata and analysis results
            reference_embedding: Style reference embedding for comparison
            character_embedding: Character face embedding for identity check
            expected_emotion: Expected emotion tag

        Returns:
            Complete quality report with scores and recommendations
        """
        asset_id = self._generate_asset_id(asset_path)

        # Score each dimension
        technical_score = self.score_technical(image_info)
        composition_score = self.score_composition(image_info)
        style_score = self.score_style(image_info, reference_embedding)
        character_score = self.score_character(
            image_info, character_embedding, expected_emotion
        )

        # Calculate weighted overall score
        weights = {
            QualityDimension.TECHNICAL: 0.25,
            QualityDimension.COMPOSITION: 0.25,
            QualityDimension.STYLE: 0.25,
            QualityDimension.CHARACTER: 0.25,
        }

        overall_score = (
            technical_score.score * weights[QualityDimension.TECHNICAL] +
            composition_score.score * weights[QualityDimension.COMPOSITION] +
            style_score.score * weights[QualityDimension.STYLE] +
            character_score.score * weights[QualityDimension.CHARACTER]
        )

        # Determine pass/fail
        passed = (
            overall_score >= self.thresholds.min_overall_score and
            technical_score.score >= self.thresholds.min_technical_score
        )

        tier = self._determine_tier(overall_score)
        action = self._determine_action(overall_score, passed)

        report = AssetQualityReport(
            asset_id=asset_id,
            asset_path=asset_path,
            timestamp=datetime.utcnow().isoformat() + "Z",
            overall_score=round(overall_score, 1),
            tier=tier,
            dimension_scores={
                QualityDimension.TECHNICAL.value: technical_score,
                QualityDimension.COMPOSITION.value: composition_score,
                QualityDimension.STYLE.value: style_score,
                QualityDimension.CHARACTER.value: character_score,
            },
            passed=passed,
            auto_action=action,
            metadata={
                "weights": {k.value: v for k, v in weights.items()},
                "thresholds": self.thresholds.model_dump(),
            },
        )

        # Store report
        self._reports[asset_id] = report
        self._save_reports()

        return report

    def get_report(self, asset_id: str) -> Optional[AssetQualityReport]:
        """Get a quality report by asset ID."""
        return self._reports.get(asset_id)

    def get_reports_by_tier(self, tier: QualityTier) -> List[AssetQualityReport]:
        """Get all reports of a specific quality tier."""
        return [r for r in self._reports.values() if r.tier == tier]

    def get_pending_reviews(self) -> List[AssetQualityReport]:
        """Get all reports pending human review."""
        return [r for r in self._reports.values() if r.auto_action == "review"]

    def get_statistics(self) -> Dict[str, Any]:
        """Get quality statistics across all evaluated assets."""
        if not self._reports:
            return {"total": 0, "message": "No reports available"}

        scores = [r.overall_score for r in self._reports.values()]
        tiers = [r.tier.value for r in self._reports.values()]
        actions = [r.auto_action for r in self._reports.values()]

        return {
            "total": len(self._reports),
            "average_score": round(sum(scores) / len(scores), 1),
            "min_score": round(min(scores), 1),
            "max_score": round(max(scores), 1),
            "tier_distribution": {
                tier: tiers.count(tier) for tier in set(tiers)
            },
            "action_distribution": {
                action: actions.count(action) for action in set(actions)
            },
            "pass_rate": round(
                sum(1 for r in self._reports.values() if r.passed) / len(self._reports) * 100,
                1
            ),
        }


# API Router
def create_quality_router() -> APIRouter:
    """Create FastAPI router for quality scoring endpoints."""
    router = APIRouter(prefix="/quality", tags=["asset-quality"])
    scorer = AssetQualityScorer()

    class EvaluateRequest(BaseModel):
        """Request to evaluate an asset."""
        asset_path: str
        image_info: Dict[str, Any]
        reference_embedding: Optional[List[float]] = None
        character_embedding: Optional[List[float]] = None
        expected_emotion: Optional[str] = None

    class ThresholdsUpdate(BaseModel):
        """Request to update quality thresholds."""
        min_resolution: Optional[int] = None
        min_technical_score: Optional[float] = None
        min_overall_score: Optional[float] = None
        auto_approve_threshold: Optional[float] = None
        auto_reject_threshold: Optional[float] = None

    @router.post("/evaluate")
    async def evaluate_asset(request: EvaluateRequest):
        """Evaluate quality of a generated asset."""
        report = scorer.evaluate_asset(
            asset_path=request.asset_path,
            image_info=request.image_info,
            reference_embedding=request.reference_embedding,
            character_embedding=request.character_embedding,
            expected_emotion=request.expected_emotion,
        )

        return {
            "asset_id": report.asset_id,
            "overall_score": report.overall_score,
            "tier": report.tier.value,
            "passed": report.passed,
            "action": report.auto_action,
            "dimensions": {
                dim: {
                    "score": score.score,
                    "issues": score.issues,
                    "suggestions": score.suggestions,
                }
                for dim, score in report.dimension_scores.items()
            },
        }

    @router.get("/report/{asset_id}")
    async def get_report(asset_id: str):
        """Get quality report for a specific asset."""
        report = scorer.get_report(asset_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        return {
            "asset_id": report.asset_id,
            "asset_path": report.asset_path,
            "timestamp": report.timestamp,
            "overall_score": report.overall_score,
            "tier": report.tier.value,
            "passed": report.passed,
            "action": report.auto_action,
        }

    @router.get("/pending-reviews")
    async def get_pending_reviews():
        """Get all assets pending human review."""
        reports = scorer.get_pending_reviews()
        return {
            "count": len(reports),
            "reports": [
                {
                    "asset_id": r.asset_id,
                    "asset_path": r.asset_path,
                    "overall_score": r.overall_score,
                    "tier": r.tier.value,
                }
                for r in reports
            ],
        }

    @router.get("/statistics")
    async def get_statistics():
        """Get quality statistics across all evaluated assets."""
        return scorer.get_statistics()

    @router.get("/thresholds")
    async def get_thresholds():
        """Get current quality thresholds."""
        return scorer.thresholds.model_dump()

    @router.put("/thresholds")
    async def update_thresholds(updates: ThresholdsUpdate):
        """Update quality thresholds."""
        current = scorer.thresholds.model_dump()
        for key, value in updates.model_dump().items():
            if value is not None:
                current[key] = value
        scorer.thresholds = QualityThresholds(**current)
        return scorer.thresholds.model_dump()

    @router.get("/tier/{tier}")
    async def get_reports_by_tier(tier: str):
        """Get all reports of a specific quality tier."""
        try:
            quality_tier = QualityTier(tier)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid tier. Valid options: {[t.value for t in QualityTier]}"
            )

        reports = scorer.get_reports_by_tier(quality_tier)
        return {
            "tier": tier,
            "count": len(reports),
            "reports": [
                {
                    "asset_id": r.asset_id,
                    "overall_score": r.overall_score,
                    "passed": r.passed,
                }
                for r in reports
            ],
        }

    return router
