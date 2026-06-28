// DRAFT (Christopher Kirschner) — MASt3R-SLAM integration.
// MERGE TARGET: sections/04-candidate-methods.typ, as a "== " subsection.
// Currently included by main.typ right after the 04 include so it previews as a
// subsection of "Candidate Methods".

== MASt3R-SLAM Integration

MASt3R-SLAM is the second method we add to the benchmark. It is a learning-based
SLAM method that builds a dense 3D reconstruction from a single camera
@murai2025mast3rslam. It estimates the 3D scene directly from the images and does
not need the camera calibration. This is why it fits uncalibrated input such as a
smartphone video.

Three things set MASt3R apart from a classical SLAM system. First, a large,
pre-trained network sits behind it (a foundation model): it has learned 3D geometry
from very many images and therefore gives robust 3D estimates even for unfamiliar
footage.

Second, MASt3R does not need the camera parameters in advance, above all not the
focal length. A classical method needs the focal length to turn a pixel into a
viewing ray into the scene, and only then determines the depth. MASt3R turns this
around: the network predicts the 3D point for each pixel directly — that is,
direction and depth at once. You do not need to know the focal length; it can be
read off these 3D points afterwards. The matching between two images therefore also
happens directly in 3D space and not through classical 2D image features.

Third, the camera is allowed to change during the recording — for example a zoom in
the middle of the video. This is possible because the focal length is not fixed in
advance.

We connect MASt3R-SLAM through the same interface as ViSTA-SLAM. Both methods read
the same input frames and write the same output files.

MASt3R-SLAM can run with or without a known calibration. If the calibration is
given, we pass it to the method. If not, the method estimates the camera focal
length on its own. Either way it runs on the raw video.

A second setting controls how dense the reconstruction is. It defines how often a
new keyframe is added. More keyframes give a denser point cloud and cover more of
the image, but the run takes longer.

Each run produces two files: the camera path in the TUM format, and a dense,
coloured point cloud. Both files are the input for the trajectory and
reconstruction evaluation in the next sections.
