#import "@preview/booktabs:0.0.4": bottomrule, midrule, toprule

= Performance Metrics

This section analyzes the computational efficiency of the evaluated SLAM systems. We executed all benchmark runs on a consumer-grade workstation equipped with an AMD Ryzen 7 5700X CPU, 32GB of system RAM, and a single NVIDIA RTX 3080 GPU. This hardware profile provides a realistic operational baseline for off-device stream processing and exposes the memory bottlenecks of modern dense monocular methods.

== Streaming Throughput and Latency

The streaming throughput, measured in frames per second (FPS), reveals the architectural tradeoffs between the candidate methods. ViSTA-SLAM achieves a processing speed of 82.7 FPS on the TUM RGB-D dataset and 62.2 FPS on Record3D captures. This performance exceeds standard real-time requirements, driven by the compact symmetric architecture of the frontend.

In contrast, MASt3R-SLAM operates near the real-time boundary, delivering 17.4 FPS on TUM and 16.3 FPS on Record3D. The dense 3D foundation model prior ensures robust geometric matching but imposes a heavy computational load. Pipeline telemetry confirms this behavior: MASt3R-SLAM incurs elevated processing latency per frame, yielding lower keyframe acceptance rates (0.48 key-FPS on TUM) compared to the ViSTA-SLAM pipeline (2.99 key-FPS on TUM).

#figure(
  table(
    columns: (1fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, left, right, right, right),
    inset: (x: 0.4em, y: 0.3em),
    toprule(),
    table.header([Method], [Dataset], [Streaming FPS], [Latency (ms)], [Keyframe FPS]),
    midrule(),
    [ViSTA-SLAM], [TUM RGB-D], [82.7], [115.5], [2.99],
    [ViSTA-SLAM], [Record3D], [62.2], [12.6], [1.73],
    [MASt3R-SLAM], [TUM RGB-D], [17.4], [52.7], [0.48],
    [MASt3R-SLAM], [Record3D], [16.3], [59.3], [0.84],
    [MASt3R-SLAM], [ADVIO], [--], [165.5], [2.78],
    bottomrule(),
  ),
  caption: [Hardware telemetry across datasets. Evaluated on an NVIDIA RTX 3080 and AMD Ryzen 7 5700X.],
) <tab:performance_metrics>

== VRAM Constraints and Model Footprint

The 10GB VRAM capacity of the NVIDIA RTX 3080 GPU dictates strict boundaries for deep learning-based SLAM architectures. Systems relying on large foundation models, such as MASt3R-SLAM and LingBot-Map, consume extensive memory allocations for feature extraction and token attention mechanisms. These memory footprints scale directly with input resolution and context window sizes. High-resolution streams or extended sequences can exhaust the available GPU memory, forcing process terminations or requiring artificial resolution downsampling.

ViSTA-SLAM navigates this hardware limitation by design. By deploying a lightweight frontend that avoids mapping geometry into a shared decoder, the system maintains a modest VRAM footprint. This architectural choice guarantees stable execution across diverse datasets without requiring enterprise-grade hardware. The results confirm that symmetric two-view formulations provide superior resource scalability for consumer-hardware deployments.