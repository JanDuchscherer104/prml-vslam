= Candidate Methods

Candidate methods are integrated behind a shared benchmark workflow so they can be compared under
consistent inputs and output formats. The initial comparison focuses on ViSTA-SLAM
@zhang2026vistaslam and MASt3R-SLAM @murai2025mast3rslam because both are directly referenced by
the challenge brief.

Each method integration should define input expectations, output artifact locations, and any
required pre-processing. The method wrappers should stay thin and should document unsupported cases
explicitly instead of hiding them behind silent fallbacks.
