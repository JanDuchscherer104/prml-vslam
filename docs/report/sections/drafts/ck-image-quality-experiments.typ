// DRAFT (Christopher Kirschner) — image-quality benchmark & tooling (experiments).
// MERGE TARGET: sections/07-experiments.typ, as a "== " subsection.
// Currently included by main.typ right after the 07 include so it previews as a
// subsection of "Experiments". On final merge, change image paths
// "../../../figures" -> "../../figures".

== Image-Quality Benchmark and Tooling

We run this evaluation as its own pipeline stage. For a finished run, the stage
loads the point cloud, the camera path, and the camera settings. It renders one
image per camera pose and pairs it with the closest input frame in time. It then
scores each pair and saves the numbers, together with a few example images. Because
everything runs from a script and is saved to disk, the evaluation can be repeated
at any time.

We also added a page to the app to inspect the results. There a user can pick a
run, see the main scores (PSNR, SSIM, coverage), follow the scores frame by frame,
browse the example images side by side, and compare several methods in one table.

@tbl-image shows the results on the ADVIO sequence advio-15 @cortes2018advio.
ViSTA-SLAM scores 357 image pairs and fills 79% of each image on average,
MASt3R-SLAM 154 pairs at 63% coverage. In pure image quality the two are close:
PSNR 10.8 versus 11.2 dB and L1 0.19 versus 0.18. The clearest difference is the
coverage: ViSTA-SLAM sets more keyframes, builds a denser cloud, and fills more of
each image.

#figure(
  table(
    columns: 6,
    align: (left, center, center, center, center, center),
    table.header(
      [Method], [Pairs], [Coverage], [PSNR (dB)], [SSIM], [L1],
    ),
    [ViSTA-SLAM], [357], [0.79], [10.8], [0.10], [0.19],
    [MASt3R-SLAM], [154], [0.63], [11.2], [0.07], [0.18],
  ),
  caption: [
    Render-based image-quality results on ADVIO advio-15. PSNR, SSIM and L1 are
    means over the filled pixels of all scored pairs; coverage is the mean share of
    filled pixels.
  ],
) <tbl-image>

@fig-sbs shows an example. The rendered image (right) reproduces the main shapes
and colours of the scene, but it has holes where the cloud is thin. These holes are
exactly what the coverage reflects.

#figure(
  image("../../../figures/render_eval/vista_advio15_sbs_a.png", width: 100%),
  caption: [
    Side-by-side example from the ViSTA-SLAM run on ADVIO advio-15: input frame
    (left) and the dense point cloud rendered from the same estimated pose (right).
    The rendering is semi-dense and leaves holes where the cloud is thin.
  ],
) <fig-sbs>

Overall, these numbers are meant as a comparison between methods on the same
sequence, not as an absolute image-quality score. On advio-15 MASt3R-SLAM and
ViSTA-SLAM deliver a similar reconstruction quality — PSNR and L1 are close. The
clearest difference is the coverage: ViSTA-SLAM sets more keyframes, while
MASt3R-SLAM in its default setting only adds a new keyframe once enough new image
content appears. SSIM also calls for extra care: it is sensitive to the estimated 
intrinsics — if the focal length is off, this acts like a zoom and shifts the 
image structure. Through its window it also counts the holes indirectly. 
Read together with the coverage, the values thus show how well and how completely a
method reconstructs the scene. MASt3R-SLAM shows its real strengths, where
things get difficult: with a zoom during the video or in low-texture scenes, for
example in front of a single-colour wall, where classical methods struggle to find
image features to track, while MASt3R still estimates the geometry thanks to its
pre-trained network.
