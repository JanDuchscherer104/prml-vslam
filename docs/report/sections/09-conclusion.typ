= Conclusion

This paper presents a benchmark framework for uncalibrated monocular VSLAM on smartphone video. Its
scientific value is the controlled transformation from heterogeneous sources into normalized method
inputs and interpretable outputs. Source manifests, prepared references, method adapters, explicit
frame placement, similarity alignment, gravity-aware alignment, ICP placement metadata, and durable
metric records are the core products of the framework.

The framework is most useful for domain experts when it is read as a reproducibility substrate. It
does not replace method papers such as ViSTA-SLAM, MASt3R-SLAM, or LingBot-Map; instead, it provides
the contracts needed to run such methods on comparable smartphone-like data and to audit the
transformations between method-native and benchmark-reference frames. The next scientific step is to
freeze the method-dataset matrix, execute the selected runs, and report quantitative trajectory,
dense-geometry, and efficiency results only from validated artifacts.
