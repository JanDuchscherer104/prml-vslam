"""Focused tests for image-pair quality metrics and the evaluation service."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from prml_vslam.eval.contracts import ImageQualityMetrics, ImageQualitySummary
from prml_vslam.eval.image_metrics import (
    compute_image_metrics,
    l1_error,
    peak_signal_noise_ratio,
    structural_similarity_index,
)
from prml_vslam.eval.image_service import ImageQualityEvaluationService


def _rng_image(seed: int, *, shape: tuple[int, ...] = (32, 32, 3)) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 256, size=shape, dtype=np.uint8)


def test_identical_images_are_perfect() -> None:
    image = _rng_image(0)
    metrics = compute_image_metrics(image, image)
    assert metrics.l1 == 0.0
    assert metrics.l2 == 0.0
    assert metrics.mse == 0.0
    assert metrics.psnr == float("inf")
    assert metrics.ssim == pytest.approx(1.0)
    assert metrics.coverage == 1.0
    assert metrics.data_range == 255.0


def test_uint8_and_float_inputs_agree() -> None:
    reference = _rng_image(1)
    generated = _rng_image(2)
    uint8_metrics = compute_image_metrics(reference, generated)
    float_metrics = compute_image_metrics(
        reference.astype(np.float64) / 255.0,
        generated.astype(np.float64) / 255.0,
    )
    assert float_metrics.l1 == pytest.approx(uint8_metrics.l1)
    assert float_metrics.mse == pytest.approx(uint8_metrics.mse)
    assert float_metrics.psnr == pytest.approx(uint8_metrics.psnr)
    assert float_metrics.ssim == pytest.approx(uint8_metrics.ssim)


def test_constant_offset_matches_closed_form() -> None:
    delta = 10
    reference = np.zeros((16, 16), dtype=np.uint8)
    generated = np.full((16, 16), delta, dtype=np.uint8)
    metrics = compute_image_metrics(reference, generated)
    assert metrics.l1 == pytest.approx(delta / 255.0)
    assert metrics.mse == pytest.approx((delta / 255.0) ** 2)
    assert metrics.psnr == pytest.approx(10.0 * np.log10(1.0 / (delta / 255.0) ** 2))


def test_psnr_and_ssim_degrade_with_noise() -> None:
    reference = _rng_image(3).astype(np.float64) / 255.0
    rng = np.random.default_rng(4)
    low_noise = np.clip(reference + rng.normal(0.0, 0.02, reference.shape), 0.0, 1.0)
    high_noise = np.clip(reference + rng.normal(0.0, 0.2, reference.shape), 0.0, 1.0)
    low = compute_image_metrics(reference, low_noise, data_range=1.0)
    high = compute_image_metrics(reference, high_noise, data_range=1.0)
    assert low.psnr > high.psnr
    assert low.ssim > high.ssim
    assert high.l1 > low.l1


def test_mask_restricts_scoring_to_covered_region() -> None:
    reference = np.zeros((16, 16, 3), dtype=np.uint8)
    generated = np.zeros((16, 16, 3), dtype=np.uint8)
    generated[8:, :, :] = 255  # corrupt the bottom half only
    mask = np.zeros((16, 16), dtype=bool)
    mask[:8, :] = True  # score only the matching top half
    metrics = compute_image_metrics(reference, generated, mask=mask)
    assert metrics.l1 == 0.0
    assert metrics.coverage == pytest.approx(0.5)


def test_single_metric_helpers_match_bundle() -> None:
    reference = _rng_image(5)
    generated = _rng_image(6)
    bundle = compute_image_metrics(reference, generated)
    assert l1_error(reference, generated) == pytest.approx(bundle.l1)
    assert peak_signal_noise_ratio(reference, generated) == pytest.approx(bundle.psnr)
    assert structural_similarity_index(reference, generated) == pytest.approx(bundle.ssim)


def test_shape_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="share a shape"):
        compute_image_metrics(_rng_image(7, shape=(16, 16, 3)), _rng_image(8, shape=(8, 8, 3)))


def test_non_positive_data_range_raises() -> None:
    with pytest.raises(ValueError, match="data_range must be positive"):
        compute_image_metrics(_rng_image(9), _rng_image(10), data_range=0.0)


def test_empty_mask_raises() -> None:
    with pytest.raises(ValueError, match="zero pixels"):
        compute_image_metrics(_rng_image(11), _rng_image(12), mask=np.zeros((32, 32), dtype=bool))


def test_summary_from_frames_aggregates() -> None:
    frames = [compute_image_metrics(_rng_image(seed), _rng_image(seed + 100)) for seed in range(3)]
    summary = ImageQualitySummary.from_frames(frames)
    assert summary.pair_count == 3
    assert summary.mean_coverage == 1.0
    assert set(summary.stats) == {"image.l1", "image.l2", "image.mse", "image.psnr", "image.ssim"}
    assert summary.stats["image.l1"].mean == pytest.approx(np.mean([frame.l1 for frame in frames]))


def test_lpips_is_none_without_scorer() -> None:
    metrics = compute_image_metrics(_rng_image(0), _rng_image(1))
    assert metrics.lpips is None


def test_lpips_scorer_is_injected_and_ignores_mask() -> None:
    calls: list[tuple[tuple[int, ...], tuple[int, ...]]] = []

    def scorer(reference01: np.ndarray, generated01: np.ndarray) -> float:
        calls.append((reference01.shape, generated01.shape))
        return 0.42

    mask = np.zeros((32, 32), dtype=bool)
    mask[:16, :] = True  # masked metrics restrict to the top half; LPIPS must still see the full frame.
    metrics = compute_image_metrics(_rng_image(0), _rng_image(1), mask=mask, lpips_scorer=scorer)
    assert metrics.lpips == pytest.approx(0.42)
    assert calls == [((32, 32, 3), (32, 32, 3))]  # full image passed, not the masked subset


def test_summary_includes_lpips_only_when_all_frames_have_it() -> None:
    scorer = lambda reference01, generated01: 0.3  # noqa: E731 - tiny stand-in scorer
    with_lpips = [
        compute_image_metrics(_rng_image(seed), _rng_image(seed + 100), lpips_scorer=scorer) for seed in range(3)
    ]
    summary = ImageQualitySummary.from_frames(with_lpips)
    assert "image.lpips" in summary.stats
    assert summary.stats["image.lpips"].mean == pytest.approx(0.3)

    mixed = [
        compute_image_metrics(_rng_image(0), _rng_image(100), lpips_scorer=scorer),
        compute_image_metrics(_rng_image(1), _rng_image(101)),  # no LPIPS -> excluded from the summary
    ]
    assert "image.lpips" not in ImageQualitySummary.from_frames(mixed).stats


def test_summary_from_frames_rejects_empty() -> None:
    with pytest.raises(ValueError, match="zero image pairs"):
        ImageQualitySummary.from_frames([])


def test_service_directory_round_trip(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    generated_dir = tmp_path / "generated"
    reference_dir.mkdir()
    generated_dir.mkdir()
    for index in range(2):
        reference = _rng_image(index)
        generated = np.clip(reference.astype(np.int16) + 5, 0, 255).astype(np.uint8)
        # cv2 writes BGR; round-trip is consistent because both sides load via the service.
        cv2.imwrite(str(reference_dir / f"{index:06d}.png"), cv2.cvtColor(reference, cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(generated_dir / f"{index:06d}.png"), cv2.cvtColor(generated, cv2.COLOR_RGB2BGR))

    service = ImageQualityEvaluationService()
    summary = service.evaluate_directories(reference_dir=reference_dir, generated_dir=generated_dir)
    assert summary.pair_count == 2
    assert all(isinstance(frame, ImageQualityMetrics) for frame in summary.frames)

    run_root = tmp_path / "run"
    result_path = service.persist(summary, run_root)
    assert result_path == run_root / "evaluation" / "image_metrics.json"
    assert result_path.exists()

    reloaded = service.load(run_root)
    assert reloaded is not None
    assert reloaded.pair_count == summary.pair_count
    assert reloaded.stats["image.psnr"].mean == pytest.approx(summary.stats["image.psnr"].mean)


def test_service_load_missing_returns_none(tmp_path: Path) -> None:
    assert ImageQualityEvaluationService().load(tmp_path / "absent") is None
