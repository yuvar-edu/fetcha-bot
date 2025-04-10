import json
import logging
import os
from typing import Dict, Set

# Define data directory path
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

# Ensure data directory exists
def ensure_data_dir():
    """Ensure the data directory exists"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_user_ids() -> Dict[str, int]:
    """
    Load Twitter user IDs from the JSON file.
    
    Returns:
        Dict mapping screen names to user IDs
    """
    try:
        user_ids_path = os.path.join(DATA_DIR, 'user_ids.json')
        with open(user_ids_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_user_ids(user_id_map: Dict[str, int]) -> None:
    """
    Save Twitter user IDs to the JSON file.
    
    Args:
        user_id_map: Dict mapping screen names to user IDs
    """
    ensure_data_dir()
    user_ids_path = os.path.join(DATA_DIR, 'user_ids.json')
    with open(user_ids_path, 'w') as file:
        json.dump(user_id_map, file)

def load_processed_ids() -> Dict[str, Set[str]]:
    """
    Load processed news and tweet IDs from the JSON file.
    
    Returns:
        Dict with 'news' and 'tweets' keys containing sets of processed IDs
    """
    try:
        processed_ids_path = os.path.join(DATA_DIR, 'processed_ids.json')
        with open(processed_ids_path, 'r') as file:
            data = json.load(file)
            return {
                'news': set(data.get('news', [])),
                'tweets': set(data.get('tweets', []))
            }
    except FileNotFoundError:
        return {'news': set(), 'tweets': set()}

def save_processed_ids(news_ids: Set[str], tweet_ids: Set[str]) -> None:
    """
    Save processed news and tweet IDs to the JSON file.
    Keeps only the most recent 1000 IDs for each type to prevent file growth.
    
    Args:
        news_ids: Set of processed news IDs
        tweet_ids: Set of processed tweet IDs
    """
    # Keep only the most recent 1000 IDs for each type to prevent file growth
    news_list = list(news_ids)[-1000:] if len(news_ids) > 1000 else list(news_ids)
    tweet_list = list(tweet_ids)[-1000:] if len(tweet_ids) > 1000 else list(tweet_ids)
    
    ensure_data_dir()
    processed_ids_path = os.path.join(DATA_DIR, 'processed_ids.json')
    with open(processed_ids_path, 'w') as file:
        json.dump({
            'news': news_list,
            'tweets': tweet_list
        }, file)