import inspect
from surya.foundation import FoundationPredictor
from surya.layout import LayoutPredictor
from surya.recognition import RecognitionPredictor
from surya.detection import DetectionPredictor

print("FoundationPredictor:", inspect.signature(FoundationPredictor.__init__))
print("LayoutPredictor:", inspect.signature(LayoutPredictor.__init__))
print("RecognitionPredictor:", inspect.signature(RecognitionPredictor.__init__))
print("DetectionPredictor:", inspect.signature(DetectionPredictor.__init__))
