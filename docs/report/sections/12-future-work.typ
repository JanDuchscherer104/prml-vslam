= Future Work

The next step is to expand the local evidence pass into a fully frozen benchmark matrix. This
requires complete LingBot coverage, dense-reference evidence for ADVIO, confidence intervals,
hardware-normalized efficiency measurements, and a documented comparison against an SfM baseline such
as COLMAP. The same matrix should also record frame-rate and resolution stress tests so that runtime,
tracking stability, and reconstruction quality can be interpreted under controlled input changes.

Future pipeline work should standardize pre-processing and post-processing across methods more
strictly. LingBot-Map in particular should be brought closer to upstream streaming parity by
persisting incremental outputs and native diagnostic artifacts rather than only the repository-level
depth-backprojection surface. Dense reconstruction should then be evaluated after explicit
post-reconstruction stages, including mesh or cloud filtering choices, so that placement errors and
local surface quality remain separable.
