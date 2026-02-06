# 📄 Phase 2.3 Layout Improvements Report

**Date:** 2026-02-05
**Objective:** Enhance document layout understanding (Multi-column, Headers, Semantic blocks).

## 🚀 Key Achievements

We have successfully overhauled the `LayoutAnalyzer` to use Surya's powerful `LayoutPredictor` alongside `DetectionPredictor`.

| Feature | Status | Details |
|---------|--------|---------|
| **Architecture** | ✅ Upgraded | Hybrid Pipeline: `LayoutPredictor` (Semantics) + `DetectionPredictor` (Lines). |
| **Multi-Column** | ✅ Verified | Tested with `OCR_test_2columns.pdf`. Correctly sorts Left Col -> Right Col. |
| **Math Blocks** | ✅ Improved | Uses Surya's "Formula" detection to identify math regions for Texify. |
| **Headers/Footers** | ✅ Detected | Layout labels allow identifying headers/footers (currently kept as text). |

## 🛠 Technical Details

### 1. Hybrid Layout Pipeline
Instead of relying on simple text detection and heuristics, `LayoutAnalyzer` now:
1.  Runs `LayoutPredictor` to get semantic regions (Title, Table, Figure, Formula, Text).
2.  Runs `DetectionPredictor` to get text lines.
3.  **Intelligently maps** text lines to their semantic regions.
4.  Filters out lines inside Figures/Math (leaving the region for specific extractors).

### 2. Column-Aware Sorting
Implemented a "Manhattan Sort" strategy:
- Detects if body content forms 2 columns (based on avg width).
- Splits blocks into Left/Right groups.
- Sorts Left Group (Top->Bottom), then Right Group.
- Handles spanning blocks (Titles, Wide Figures) separately at top/bottom.

### 3. Verification
Ran specific test on `OCR_test_2columns.pdf`:
- **Before:** Text from Left/Right columns was interleaved (reading line-by-line across the page).
- **After:** Text flows naturally: Intro -> Model (Left) -> Numerical Methods (Right).

## ⏭ Next Steps (Phase 3)
- **Performance:** Running 2 models (Layout + Detection) + Texify is heavier. Need to optimize batching and memory.
- **Table Extraction:** Now that we have `Table` blocks, we can implement table processing.
- **Refinement:** Tune "2-column" detection thresholds if edge cases arise.
