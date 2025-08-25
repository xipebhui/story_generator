#!/usr/bin/env python3
"""
漫画解说视频生成Pipeline
"""

from .pipeline import ComicVideoPipeline
from .models import ComicImage, ImageAnalysis, NarrationSegment
from .config import ComicPipelineConfig

__version__ = "1.0.0"
__all__ = [
    "ComicVideoPipeline",
    "ComicImage",
    "ImageAnalysis", 
    "NarrationSegment",
    "ComicPipelineConfig"
]