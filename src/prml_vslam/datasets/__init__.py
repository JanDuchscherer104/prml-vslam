"""Dataset package entry surface for normalized dataset adapters.

The :mod:`prml_vslam.datasets` package owns repository-local dataset catalogs,
normalization helpers, replay preparation, and typed dataset contracts. It does
not own pipeline stage order or backend execution; instead it feeds normalized
inputs such as :class:`prml_vslam.pipeline.SequenceManifest` into
:mod:`prml_vslam.pipeline` and benchmark-side references into
:mod:`prml_vslam.benchmark`.
"""

from .contracts import DatasetId

__all__ = ["DatasetId"]
