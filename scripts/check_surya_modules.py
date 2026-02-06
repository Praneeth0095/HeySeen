
try:
    from surya.layout import LayoutPredictor
    print("surya.layout.LayoutPredictor available")
except ImportError:
    print("surya.layout.LayoutPredictor NOT available")
    
from surya.detection import DetectionPredictor
print("surya.detection.DetectionPredictor available")
