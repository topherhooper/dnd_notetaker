import logging
import os
import shutil
import tempfile
import time
from datetime import datetime


def setup_logging(name):
    """Configure logging with timestamps and appropriate formatting"""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    return logging.getLogger(name)


def save_text_output(content, prefix, output_dir):
    """
    Save text content to a timestamped file in the output directory.

    Args:
        content (str): The text content to save
        prefix (str): Prefix for the filename (e.g., 'transcript', 'notes')
        output_dir (str): Directory to save the file

    Returns:
        str: Path to the saved file
    """
    logger = setup_logging("Utils")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    logger.debug(f"Ensuring output directory exists: {output_dir}")

    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.txt"
    filepath = os.path.join(output_dir, filename)

    # Save the content
    logger.debug(f"Saving {prefix} to: {filepath}")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"Saved {prefix} to: {filepath}")
    return filepath


