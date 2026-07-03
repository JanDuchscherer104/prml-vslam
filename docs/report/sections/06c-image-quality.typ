= Image Quality Metrics

== Render-Based Reconstruction Fidelity

This metric evaluates the reconstruction in *image space*: how good does the
estimated scene look when viewed from the estimated camera poses? That is a
separate question from the geometric cloud-to-cloud comparison. The geometric check
measures how accurate the 3D shape is; our image check measures how well the cloud
reproduces the colours and structure of the scene and how much of each image it
fills. Together they give a fuller picture.

To apply the image metrics, the reconstruction first has to be rendered into an
image. As a simple baseline we render the dense point cloud by projection: each 3D
point lands directly on the image plane. The metrics themselves do not depend on
this choice, though. One could just as well replace the point cloud with a 3D
Gaussian Splatting or NeRF model and apply the same metrics to its rendered views
@mildenhall2020nerf @kerbl2023gaussian; only the renderer would change. We then
compare each rendered image with the real input frame, pixel by pixel.

The projection in detail: for a world point $X$ and a camera pose with rotation $R$
and translation $t$, the point in the camera frame is $X_c = R^top (X - t)$, and
its pixel position is $x = K X_c \/ Z_c$. Here $K$ holds the focal lengths
$f_x, f_y$ and the image centre $(c_x, c_y)$, and $Z_c$ is the depth of the point.
If several points fall on the same pixel, the nearest one wins; pixels with no
point stay empty. We do not implement this projection ourselves; Open3D computes it
@zhou2018open3d.

We only score the pixels that the cloud actually fills. These filled pixels form a
set $Omega$. We compare the real frame $I$ and the rendered image $hat(I)$ only on
$Omega$, so the cloud is not punished for pixels it never covered. There we compute
three simple errors,
$ "L1" = 1/N sum_(p in Omega) abs(I_p - hat(I)_p), quad
  "MSE" = 1/N sum_(p in Omega) (I_p - hat(I)_p)^2, $
$ "PSNR" = 10 log_10 (L^2 \/ "MSE"), $
where $N$ is the number of filled pixels and $L$ is the value range ($L = 255$ for
8-bit images). A higher PSNR means a better match. We also compute the structural
similarity index (SSIM), which checks how similar the local image structure is and
ranges from $-1$ to $1$ ($1$ means identical) @wang2004ssim. As a perceptual metric
we add LPIPS (Learned Perceptual Image Patch Similarity). Instead of comparing
pixels directly, LPIPS measures the distance over the features of a pre-trained
neural network and therefore correlates better with human perception than PSNR or
SSIM. Lower values mean a perceptually closer match, with $0$ meaning identical
images @zhang2018lpips. Finally we report the coverage, the share of pixels the
cloud fills, since the other scores only count those pixels.

A detail on the mask: since $Omega$ decides *which* pixels enter the mean, masking
works cleanly for L1 and PSNR, because these scores are computed pixel by pixel.
SSIM is different: its value is formed over a $7 times 7$ window around each pixel.
If a filled pixel lies at the edge of a hole, its window reaches into the empty
(black) areas and its SSIM value drops — even though the pixel itself is valid. The
mask can no longer repair this, because the hole's influence is already baked into
the value. A thin, holey cloud therefore hits SSIM harder than PSNR or L1. LPIPS shares
this problem and even amplifies it: it is computed over the whole image from deep
network features with a large receptive field, so the holes bleed in even more
strongly and cannot be masked out cleanly.

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

@tbl-image summarises the results split by dataset, averaged per method: over three
TUM RGB-D sequences (freiburg1-desk, freiburg1-360, freiburg1-plant) and over two
ADVIO sequences (advio-03, advio-05) @cortes2018advio. Compared to the previous
version, we added LPIPS as a perceptual metric (see the metric definition above);
lower values are better.

On TUM RGB-D, MASt3R-SLAM sets far fewer keyframes than ViSTA-SLAM (32 versus 96
pairs), yet reaches practically the same coverage (0.96 versus 0.96). In image
quality MASt3R-SLAM leads: PSNR 12.4 versus 10.0 dB, SSIM 0.26 versus 0.08, LPIPS
0.62 versus 1.06, and L1 0.16 versus 0.23.

On ADVIO, MASt3R-SLAM runs without a keyframe cap and therefore sets more keyframes
(365 versus 284 pairs); at the same time it reaches a higher coverage (0.72 versus
0.57). Here too the image quality is better: PSNR 11.2 versus 10.6 dB, SSIM 0.09
versus 0.03, LPIPS 1.13 versus 1.32, and L1 0.21 versus 0.23.

#figure(
  table(
    columns: 8,
    align: (left, left, center, center, center, center, center, center),
    table.header(
      [Dataset], [Method], [Pairs], [Coverage], [PSNR (dB)], [SSIM], [LPIPS], [L1],
    ),
    table.cell(rowspan: 2)[TUM RGB-D],
    [ViSTA-SLAM], [96], [0.96], [10.0], [0.08], [1.06], [0.23],
    [MASt3R-SLAM], [32], [0.96], [12.4], [0.26], [0.62], [0.16],
    table.cell(rowspan: 2)[ADVIO],
    [ViSTA-SLAM], [284], [0.57], [10.6], [0.03], [1.32], [0.23],
    [MASt3R-SLAM], [365], [0.72], [11.2], [0.09], [1.13], [0.21],
  ),
  caption: [
    Render-based image-quality results, averaged separately per dataset: over three
    TUM RGB-D sequences (freiburg1-desk/-360/-plant) and two ADVIO sequences
    (advio-03/-05). PSNR, SSIM, LPIPS and L1 are means over the filled pixels of all
    scored pairs; coverage is the mean share of filled pixels. Higher PSNR and SSIM
    and lower LPIPS and L1 are better.
  ],
) <tbl-image>

@fig-sbs shows an example. The rendered image (right) reproduces the main shapes
and colours of the scene, but it has holes where the cloud is thin. These holes are
exactly what the coverage reflects.

#figure(
  image("../../figures/render_eval/vista_advio15_sbs_a.png", width: 100%),
  caption: [
    Side-by-side example from the ViSTA-SLAM run on ADVIO advio-15: input frame
    (left) and the dense point cloud rendered from the same estimated pose (right).
    The rendering is semi-dense and leaves holes where the cloud is thin.
  ],
) <fig-sbs>

Overall, these numbers are meant as a comparison between methods on the same
sequences, not as an absolute image-quality score. Taken together they say: PSNR and
L1 measure the plain pixel error, SSIM and LPIPS the structural and perceptual
similarity, and the coverage how completely the scene is filled. Across both
datasets MASt3R-SLAM reconstructs the scene somewhat more faithfully throughout — on
TUM RGB-D at equal coverage and with fewer keyframes, on ADVIO at the same time with
higher coverage.
