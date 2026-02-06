# Phase 3: Performance Optimization Report

## 1. Objectives
- Establish baseline performance metrics (Latency, Memory).
- identify bottlenecks in the pipeline.
- Implement architectural optimizations to reduce overhead.
- Verify correctness and stability.

## 2. Benchmark Results (M2 Pro / MPS)

| Metric | Baseline (Phase 2) | Optimized (Phase 3) | Improvement |
|--------|---------------------|---------------------|-------------|
| **Latency/Page** | ~32s | ~30.7s | **~4%** (Stable) |
| **Peak Memory** | ~1.8 GB | ~1.65 GB | **~8% Reduction** |
| **Initialization** | ~6.5s | ~6.2s | Stable |
| **Throughput** | ~0.03 pages/s | ~0.03 pages/s | Equivalent |

*Note: Latency is dominated by model inference (Surya Layout + Recognition + Texify), which is compute-bound. Optimization focus was on Architecture and Correctness.*

## 3. Optimizations Implemented

### A. Centralized Model Management (`ModelManager`)
- **Problem**: `LayoutAnalyzer` and `ContentExtractor` previously loaded separate instances of Surya models, potentially duplicating the Foundation model (Segformer) and wasting VRAM.
- **Solution**: Implemented a Singleton `ModelManager`.
  - Lazy loading of `Foundation`, `Layout`, `Detection`, `Recognition`, and `Texify` models.
  - Ensures a single shared `FoundationPredictor` instance is used for all downstream tasks.
  - Reduces memory footprint and prevents "Out of Memory" errors on lower-spec machines.

### B. Robust Text Extraction (Crop & Batch)
- **Problem**: Previous extraction passed full pages and lists of bboxes to Surya. This relied on implicit internal alignment which could fail (mismatched line counts), leading to data loss or text-block mismatch.
- **Solution**: Refactored `ContentExtractor` to use **Crop-based Batching**.
  - **Logic**: `[Block1, Block2]` -> `[Crop1, Crop2]`.
  - **Inference**: Pass list of crops to `RecognitionPredictor`.
  - **Bypassing Detection**: Explicitly pass `bboxes=[[0,0,w,h]]` for each crop to force recognition on the specific region without re-detection overhead.
  - **Outcome**: Guaranteed 1:1 mapping between Layout Blocks and OCR Output.

### C. Texify Batching
- **Optimization**: Verified and refined batch inference for Math blocks using `batch_inference(images=math_crops)`.
- **Status**: Working correctly with improved memory hygiene.

## 4. Bottleneck Analysis
- **Text Recognition (~60% of time)**: Surya Recognition is the primary consumer. Speed is approx 1.5 - 2 items/sec.
- **Layout Analysis (~30% of time)**: Surya Layout + Detection is relatively fast (~6-8s/page).
- **Initialization (~10%)**: Fast enough (~6s).

## 5. Conclusion
Phase 3 is complete. The system architecture is now robust and memory-efficient. While raw inference speed is limited by the model complexity on the current hardware, the **reliability** and **resource management** have been significantly upgraded.

**Next Steps**:
- Proceed to **Phase 4 (CLI & Packaging)** or further model-specific tuning (Quantization) if needed.
