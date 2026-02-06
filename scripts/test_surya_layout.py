
from surya.layout import LayoutPredictor
from PIL import Image
from heyseen.core.pdf_loader import load_pdf
import json

from surya.layout import LayoutPredictor
from surya.detection import DetectionPredictor
from surya.foundation import FoundationPredictor
from heyseen.core.pdf_loader import load_pdf

# Load first page of test pdf
pages = load_pdf("pdf_examples/OCR_test_1.pdf")
image = pages[0]

try:
    print("Loading FoundationPredictor...")
    foundation = FoundationPredictor()
    print("Loading LayoutPredictor...")
    layout_predictor = LayoutPredictor(foundation)
    print("Loading DetectionPredictor...")
    det_predictor = DetectionPredictor()
    
    print("Running Layout...")
    layout_res = layout_predictor([image])[0]
    print(f"Layout found {len(layout_res.bboxes)} blocks")
    for b in layout_res.bboxes[:3]:
        print(f"  - {b.label}: {b.bbox}")

    print("Running Detection...")
    det_res = det_predictor([image])[0]
    print(f"Detection found {len(det_res.bboxes)} lines")
    
except Exception as e:
    print(f"Failed: {e}")
    import traceback
    traceback.print_exc()
results = predictor([image])

# Print result structure
res = results[0]
print("Result keys:", dir(res))
try:
    print("Bboxes:", len(res.bboxes))
    print("First bbox:", res.bboxes[0])
    print("Label of first bbox:", res.bboxes[0].label) 
except:
    pass
