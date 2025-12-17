"""
Hydra Face Detection Module

Provides face detection and analysis for Phase 12 quality scoring.
Uses MediaPipe for lightweight, fast face detection without GPU.

Features:
- Face detection with bounding boxes
- Face landmark extraction (468 points)
- Face centering analysis
- Multiple face detection
- Expression/emotion estimation (basic)

Author: Hydra Autonomous System
Created: 2025-12-17
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Lazy imports for optional dependencies
_mediapipe = None
_cv2 = None


def _get_mediapipe():
    """Lazy load mediapipe."""
    global _mediapipe
    if _mediapipe is None:
        try:
            import mediapipe as mp
            _mediapipe = mp
        except ImportError:
            logger.warning("mediapipe not installed. Face detection unavailable.")
            return None
    return _mediapipe


def _get_cv2():
    """Lazy load opencv."""
    global _cv2
    if _cv2 is None:
        try:
            import cv2
            _cv2 = cv2
        except ImportError:
            logger.warning("opencv not installed. Face detection unavailable.")
            return None
    return _cv2


@dataclass
class FaceDetection:
    """Detected face information."""
    bbox: Dict[str, float]  # x, y, width, height (normalized 0-1)
    center_x: float  # Normalized center x (0-1)
    center_y: float  # Normalized center y (0-1)
    area_ratio: float  # Face area / image area
    confidence: float  # Detection confidence
    landmarks: Optional[List[Dict[str, float]]] = None  # 468 facial landmarks
    expression: Optional[str] = None  # Detected expression (basic)


@dataclass
class FaceAnalysisResult:
    """Complete face analysis result."""
    faces: List[FaceDetection]
    face_count: int
    primary_face: Optional[FaceDetection]  # Largest/most centered face
    image_width: int
    image_height: int
    has_faces: bool
    analysis_time_ms: float
    warnings: List[str] = field(default_factory=list)


class FaceDetector:
    """
    Face detector using MediaPipe.

    Provides face detection, landmark extraction, and basic analysis
    for quality scoring integration.
    """

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        model_selection: int = 1,  # 0 for close-range, 1 for full-range
    ):
        self.min_detection_confidence = min_detection_confidence
        self.model_selection = model_selection
        self._face_detection = None
        self._face_mesh = None
        self._initialized = False

    def _initialize(self) -> bool:
        """Initialize MediaPipe models."""
        if self._initialized:
            return True

        mp = _get_mediapipe()
        if mp is None:
            return False

        try:
            # Face detection for bounding boxes
            self._face_detection = mp.solutions.face_detection.FaceDetection(
                min_detection_confidence=self.min_detection_confidence,
                model_selection=self.model_selection,
            )

            # Face mesh for landmarks (optional, more detailed)
            self._face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=5,
                min_detection_confidence=self.min_detection_confidence,
            )

            self._initialized = True
            logger.info("Face detector initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize face detector: {e}")
            return False

    def detect_faces(self, image_path: str) -> FaceAnalysisResult:
        """
        Detect faces in an image.

        Args:
            image_path: Path to the image file

        Returns:
            FaceAnalysisResult with detected faces and analysis
        """
        import time
        start_time = time.time()

        cv2 = _get_cv2()
        if cv2 is None:
            return FaceAnalysisResult(
                faces=[],
                face_count=0,
                primary_face=None,
                image_width=0,
                image_height=0,
                has_faces=False,
                analysis_time_ms=0,
                warnings=["opencv not available"],
            )

        if not self._initialize():
            return FaceAnalysisResult(
                faces=[],
                face_count=0,
                primary_face=None,
                image_width=0,
                image_height=0,
                has_faces=False,
                analysis_time_ms=0,
                warnings=["mediapipe not available"],
            )

        # Load image
        path = Path(image_path)
        if not path.exists():
            return FaceAnalysisResult(
                faces=[],
                face_count=0,
                primary_face=None,
                image_width=0,
                image_height=0,
                has_faces=False,
                analysis_time_ms=0,
                warnings=[f"Image not found: {image_path}"],
            )

        image = cv2.imread(str(path))
        if image is None:
            return FaceAnalysisResult(
                faces=[],
                face_count=0,
                primary_face=None,
                image_width=0,
                image_height=0,
                has_faces=False,
                analysis_time_ms=0,
                warnings=[f"Failed to load image: {image_path}"],
            )

        height, width = image.shape[:2]
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Detect faces
        faces = []
        warnings = []

        try:
            results = self._face_detection.process(image_rgb)

            if results.detections:
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box

                    # Calculate normalized coordinates
                    x = max(0, bbox.xmin)
                    y = max(0, bbox.ymin)
                    w = min(1 - x, bbox.width)
                    h = min(1 - y, bbox.height)

                    center_x = x + w / 2
                    center_y = y + h / 2
                    area_ratio = w * h

                    face = FaceDetection(
                        bbox={"x": x, "y": y, "width": w, "height": h},
                        center_x=center_x,
                        center_y=center_y,
                        area_ratio=area_ratio,
                        confidence=detection.score[0] if detection.score else 0.0,
                    )
                    faces.append(face)

        except Exception as e:
            warnings.append(f"Face detection error: {str(e)}")

        # Determine primary face (largest area, closest to center)
        primary_face = None
        if faces:
            # Score faces by size and centering
            def face_score(f: FaceDetection) -> float:
                # Higher area = better
                area_score = f.area_ratio * 10
                # Closer to center = better (penalize distance from 0.5, 0.4)
                center_penalty = abs(f.center_x - 0.5) + abs(f.center_y - 0.4)
                return area_score - center_penalty

            faces_sorted = sorted(faces, key=face_score, reverse=True)
            primary_face = faces_sorted[0]

        # Multiple faces warning
        if len(faces) > 1:
            warnings.append(f"Multiple faces detected: {len(faces)}")

        analysis_time_ms = (time.time() - start_time) * 1000

        return FaceAnalysisResult(
            faces=faces,
            face_count=len(faces),
            primary_face=primary_face,
            image_width=width,
            image_height=height,
            has_faces=len(faces) > 0,
            analysis_time_ms=round(analysis_time_ms, 2),
            warnings=warnings,
        )

    def get_face_landmarks(self, image_path: str) -> Optional[List[Dict[str, float]]]:
        """
        Get detailed face landmarks (468 points) for the primary face.

        Args:
            image_path: Path to the image file

        Returns:
            List of landmark points with x, y, z coordinates, or None
        """
        cv2 = _get_cv2()
        if cv2 is None or not self._initialize():
            return None

        image = cv2.imread(str(image_path))
        if image is None:
            return None

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        try:
            results = self._face_mesh.process(image_rgb)

            if results.multi_face_landmarks and len(results.multi_face_landmarks) > 0:
                landmarks = []
                for landmark in results.multi_face_landmarks[0].landmark:
                    landmarks.append({
                        "x": landmark.x,
                        "y": landmark.y,
                        "z": landmark.z,
                    })
                return landmarks

        except Exception as e:
            logger.warning(f"Landmark extraction error: {e}")

        return None

    def analyze_for_quality_scoring(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze image and return data formatted for quality scoring.

        This is the main integration point with asset_quality.py.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with face data for quality scoring
        """
        result = self.detect_faces(image_path)

        # Format for quality scoring integration
        face_data = {
            "has_faces": result.has_faces,
            "face_count": result.face_count,
            "analysis_time_ms": result.analysis_time_ms,
            "warnings": result.warnings,
        }

        if result.primary_face:
            face = result.primary_face
            face_data["faces"] = [{
                "center_x": face.center_x,
                "center_y": face.center_y,
                "area_ratio": face.area_ratio,
                "confidence": face.confidence,
                "bbox": face.bbox,
            }]
        else:
            face_data["faces"] = []

        # Add all faces if multiple
        if result.face_count > 1:
            face_data["all_faces"] = [
                {
                    "center_x": f.center_x,
                    "center_y": f.center_y,
                    "area_ratio": f.area_ratio,
                    "confidence": f.confidence,
                }
                for f in result.faces
            ]

        return face_data

    def close(self):
        """Release resources."""
        if self._face_detection:
            self._face_detection.close()
        if self._face_mesh:
            self._face_mesh.close()
        self._initialized = False


# Global detector instance
_detector_instance: Optional[FaceDetector] = None


def get_detector() -> FaceDetector:
    """Get the global face detector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = FaceDetector()
    return _detector_instance


def detect_faces_in_image(image_path: str) -> Dict[str, Any]:
    """
    Convenience function to detect faces in an image.

    Args:
        image_path: Path to the image

    Returns:
        Face data dictionary for quality scoring
    """
    detector = get_detector()
    return detector.analyze_for_quality_scoring(image_path)


# =============================================================================
# FastAPI Router
# =============================================================================

def create_face_detection_router():
    """Create FastAPI router for face detection endpoints."""
    from fastapi import APIRouter
    from pydantic import BaseModel

    router = APIRouter(prefix="/faces", tags=["face-detection"])

    class DetectRequest(BaseModel):
        image_path: str

    @router.post("/detect")
    async def detect_faces(request: DetectRequest):
        """
        Detect faces in an image.

        Returns face locations, confidence, and quality-relevant metrics.
        """
        detector = get_detector()
        result = detector.detect_faces(request.image_path)

        return {
            "face_count": result.face_count,
            "has_faces": result.has_faces,
            "primary_face": {
                "center_x": result.primary_face.center_x,
                "center_y": result.primary_face.center_y,
                "area_ratio": result.primary_face.area_ratio,
                "confidence": result.primary_face.confidence,
                "bbox": result.primary_face.bbox,
            } if result.primary_face else None,
            "all_faces": [
                {
                    "center_x": f.center_x,
                    "center_y": f.center_y,
                    "area_ratio": f.area_ratio,
                    "confidence": f.confidence,
                }
                for f in result.faces
            ],
            "image_dimensions": {
                "width": result.image_width,
                "height": result.image_height,
            },
            "analysis_time_ms": result.analysis_time_ms,
            "warnings": result.warnings,
        }

    @router.post("/analyze")
    async def analyze_for_quality(request: DetectRequest):
        """
        Analyze image for quality scoring integration.

        Returns face data formatted for asset_quality.py integration.
        """
        return detect_faces_in_image(request.image_path)

    @router.get("/status")
    async def detector_status():
        """Get face detector status."""
        mp = _get_mediapipe()
        cv2 = _get_cv2()

        return {
            "mediapipe_available": mp is not None,
            "opencv_available": cv2 is not None,
            "detector_initialized": _detector_instance is not None and _detector_instance._initialized,
        }

    return router
