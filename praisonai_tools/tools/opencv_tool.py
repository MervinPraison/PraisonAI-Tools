"""OpenCV Tool for PraisonAI Agents.

Image processing using OpenCV.

Usage:
    from praisonai_tools import OpenCVTool
    
    cv = OpenCVTool()
    result = cv.resize("image.jpg", width=800)
"""

import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class OpenCVTool(BaseTool):
    """Tool for OpenCV image processing."""
    
    name = "opencv"
    description = "Image processing using OpenCV."
    
    def run(
        self,
        action: str = "resize",
        image_path: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        action = action.lower().replace("-", "_")
        
        if action == "resize":
            return self.resize(image_path=image_path, **kwargs)
        elif action == "grayscale":
            return self.grayscale(image_path=image_path, **kwargs)
        elif action == "blur":
            return self.blur(image_path=image_path, **kwargs)
        elif action == "detect_faces":
            return self.detect_faces(image_path=image_path)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def resize(self, image_path: str, width: int = None, height: int = None, output_path: str = None) -> Dict[str, Any]:
        """Resize image."""
        if not image_path:
            return {"error": "image_path is required"}
        
        try:
            import cv2
        except ImportError:
            return {"error": "opencv-python not installed"}
        
        try:
            img = cv2.imread(image_path)
            if img is None:
                return {"error": "Could not read image"}
            
            h, w = img.shape[:2]
            if width and not height:
                height = int(h * width / w)
            elif height and not width:
                width = int(w * height / h)
            elif not width and not height:
                return {"error": "width or height required"}
            
            resized = cv2.resize(img, (width, height))
            out = output_path or image_path.replace(".", "_resized.")
            cv2.imwrite(out, resized)
            return {"success": True, "output_path": out, "width": width, "height": height}
        except Exception as e:
            logger.error(f"OpenCV resize error: {e}")
            return {"error": str(e)}
    
    def grayscale(self, image_path: str, output_path: str = None) -> Dict[str, Any]:
        """Convert to grayscale."""
        if not image_path:
            return {"error": "image_path is required"}
        
        try:
            import cv2
        except ImportError:
            return {"error": "opencv-python not installed"}
        
        try:
            img = cv2.imread(image_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            out = output_path or image_path.replace(".", "_gray.")
            cv2.imwrite(out, gray)
            return {"success": True, "output_path": out}
        except Exception as e:
            logger.error(f"OpenCV grayscale error: {e}")
            return {"error": str(e)}
    
    def blur(self, image_path: str, kernel_size: int = 5, output_path: str = None) -> Dict[str, Any]:
        """Apply blur."""
        if not image_path:
            return {"error": "image_path is required"}
        
        try:
            import cv2
        except ImportError:
            return {"error": "opencv-python not installed"}
        
        try:
            img = cv2.imread(image_path)
            blurred = cv2.GaussianBlur(img, (kernel_size, kernel_size), 0)
            out = output_path or image_path.replace(".", "_blur.")
            cv2.imwrite(out, blurred)
            return {"success": True, "output_path": out}
        except Exception as e:
            logger.error(f"OpenCV blur error: {e}")
            return {"error": str(e)}
    
    def detect_faces(self, image_path: str) -> Dict[str, Any]:
        """Detect faces in image."""
        if not image_path:
            return {"error": "image_path is required"}
        
        try:
            import cv2
        except ImportError:
            return {"error": "opencv-python not installed"}
        
        try:
            img = cv2.imread(image_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            return {"faces_count": len(faces), "faces": [{"x": int(x), "y": int(y), "w": int(w), "h": int(h)} for x, y, w, h in faces]}
        except Exception as e:
            logger.error(f"OpenCV detect_faces error: {e}")
            return {"error": str(e)}


def opencv_resize(image_path: str, width: int) -> Dict[str, Any]:
    """Resize image."""
    return OpenCVTool().resize(image_path=image_path, width=width)
