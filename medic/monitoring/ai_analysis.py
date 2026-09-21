"""
AI Wound Image Analysis Service.

MEDICAL SAFETY NOTICE:
This module is a prototype decision-support heuristic, NOT a diagnostic system.
It is not clinically validated and does NOT detect infections or diagnose medical conditions.
Outputs are prototype indicators intended solely to assist clinical review.
"""
import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)


def analyze_wound_image(image_path):
    """
    Analyzes wound image redness ratio using HSV color space heuristics.
    
    Returns prototype decision-support observation strings.
    """
    try:
        image = cv2.imread(image_path)
        if image is None:
            return "Image not readable (prototype indicator)"

        # Convert to HSV color space
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Define red color ranges in HSV (covering hue wrap-around)
        lower_red1 = np.array([0, 100, 70])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 100, 70])
        upper_red2 = np.array([180, 255, 255])

        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)

        red_pixels = np.sum(mask > 0)
        total_pixels = mask.size

        if total_pixels == 0:
            return "Image not readable (prototype indicator)"

        redness_ratio = red_pixels / total_pixels

        if redness_ratio > 0.15:
            return "Possible visual concern; medical review recommended (prototype indicator)"

        return "Normal visual variation; routine observation recommended (prototype indicator)"

    except Exception as exc:
        logger.error(f"Error during OpenCV wound analysis for {image_path}: {exc}")
        return "Image analysis error; manual medical review recommended (prototype indicator)"