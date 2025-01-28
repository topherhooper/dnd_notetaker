import json
import os
import logging
import functools

def load_config(config_path:str) -> dict:
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config
def setup_logging(name):
    """Configure logging with timestamps and appropriate formatting"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(name)

def save_text_output(content, output_filepath:str):
    """
    Save text content to a timestamped file in the output directory.
    
    Args:
        content (str): The text content to save
        prefix (str): Prefix for the filename (e.g., 'transcript', 'notes')
        output_dir (str): Directory to save the file
        
    Returns:
        str: Path to the saved file
    """
    logger = setup_logging('Utils')

    # Save the content
    logger.debug(f"Saving to: {output_filepath}")
    with open(output_filepath, "w", encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"Saved to: {output_filepath}")
    return output_filepath

def cache_to_file(filepath):
    """Caches function results to a specific file."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create directory if it doesn't exist
            cache_dir = os.path.dirname(filepath)
            if cache_dir:  # Only create if path has a directory component
                os.makedirs(cache_dir, exist_ok=True)
            
            # Check cache
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            
            # Cache miss - execute function
            result = func(*args, **kwargs)
            save_text_output(str(result), filepath)
            return result
            
        wrapper.clear_cache = lambda: os.remove(filepath) if os.path.exists(filepath) else None
        return wrapper
    return decorator