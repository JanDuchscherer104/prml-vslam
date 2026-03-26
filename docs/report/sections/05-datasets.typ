= Datasets

Trajectory quality is benchmarked on the ADVIO dataset @cortes2018advio and on a custom smartphone capture
dataset recorded for this project. The custom capture workflow is expected to store raw video and
baseline ARCore logs with enough metadata to reproduce alignment and evaluation.

Dense reconstruction quality is assessed on self-recorded data because the challenge explicitly asks
for a comparison against ARCore mapping results on a custom test dataset. Reference reconstructions
for these captures can be generated with tools such as COLMAP @schoenberger2016sfm
@schoenberger2016mvs.
