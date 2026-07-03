// DRAFT (Christopher Kirschner) — render-based reconstruction fidelity (metric).
// MERGE TARGET: sections/06-metrics.typ, as a "== " subsection.
// Currently included by main.typ right after the 06 include so it previews as a
// subsection of "Metrics". On final merge, change image paths
// "../../../figures" -> "../../figures".

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
ranges from $-1$ to $1$ ($1$ means identical) @wang2004ssim. Finally we report the
coverage, the share of pixels the cloud fills, since the other scores only count
those pixels.

A detail on the mask: since $Omega$ decides *which* pixels enter the mean, masking
works cleanly for L1 and PSNR, because these scores are computed pixel by pixel.
SSIM is different: its value is formed over a $7 times 7$ window around each pixel.
If a filled pixel lies at the edge of a hole, its window reaches into the empty
(black) areas and its SSIM value drops — even though the pixel itself is valid. The
mask can no longer repair this, because the hole's influence is already baked into
the value. A thin, holey cloud therefore hits SSIM harder than PSNR or L1.

Overall, these numbers are best used to compare methods on the same sequence, not
as an absolute image-quality score.
