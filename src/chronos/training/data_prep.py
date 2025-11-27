"""Data preparation utilities for DPO training."""

from typing import List, Dict, Any
import json
from pathlib import Path

from src.chronos.utils.logger import get_logger

logger = get_logger(__name__)


def prepare_preference_data(
    feedback_file: str,
    output_file: str = "data/training/preferences.json"
) -> List[Dict[str, Any]]:
    """
    Prepare preference data from user feedback.
    
    Args:
        feedback_file: Path to feedback JSON file
        output_file: Path to save prepared data
        
    Returns:
        List of preference examples
    """
    logger.info(f"Loading feedback from: {feedback_file}")
    
    with open(feedback_file, 'r') as f:
        feedback_data = json.load(f)
    
    preferences = []
    
    for item in feedback_data:
        # Each item should have:
        # - prompt: user request
        # - responses: list of possible responses
        # - user_rating: ratings for each response
        
        prompt = item.get("prompt", "")
        responses = item.get("responses", [])
        ratings = item.get("ratings", [])
        
        if len(responses) >= 2 and len(ratings) >= 2:
            # Find best and worst responses
            best_idx = ratings.index(max(ratings))
            worst_idx = ratings.index(min(ratings))
            
            preferences.append({
                "prompt": prompt,
                "chosen": responses[best_idx],
                "rejected": responses[worst_idx],
            })
    
    # Save prepared data
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(preferences, f, indent=2)
    
    logger.info(f"Prepared {len(preferences)} preference examples")
    logger.info(f"Saved to: {output_file}")
    
    return preferences


def collect_feedback_template() -> Dict[str, Any]:
    """
    Generate a template for collecting user feedback.
    
    Returns:
        Template dictionary
    """
    return {
        "prompt": "User's scheduling request",
        "responses": [
            "Response option 1",
            "Response option 2",
            "Response option 3"
        ],
        "ratings": [5, 3, 1],  # 5=best, 1=worst
        "timestamp": "2024-01-01T12:00:00",
        "user_id": "user_123",
        "notes": "Optional feedback notes"
    }

