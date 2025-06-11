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


def cleanup_old_temp_directories(base_dir, max_age_hours=24):
    """
    Clean up temporary directories older than specified hours.
    Now also cleans up audio_chunks_temp directories in output folders.

    Args:
        base_dir (str): Base directory to search (typically 'output')
        max_age_hours (int): Maximum age in hours before cleanup

    Returns:
        tuple: (number_removed, list_of_remaining_dirs)
    """
    logger = setup_logging("Utils")
    removed_count = 0
    remaining_dirs = []

    try:
        # First, clean up any legacy system temp directories
        for item in os.listdir(tempfile.gettempdir()):
            if item.startswith("meeting_processor_") or item.startswith(
                "audio_processor_"
            ):
                temp_path = os.path.join(tempfile.gettempdir(), item)
                if os.path.isdir(temp_path):
                    # Check age
                    created_time = os.path.getctime(temp_path)
                    age_hours = (time.time() - created_time) / 3600

                    if age_hours > max_age_hours:
                        try:
                            shutil.rmtree(temp_path)
                            removed_count += 1
                            logger.info(f"Removed old temp directory: {temp_path}")
                        except Exception as e:
                            logger.warning(f"Failed to remove {temp_path}: {str(e)}")
                            remaining_dirs.append(temp_path)
                    else:
                        remaining_dirs.append(temp_path)

        # Now clean up audio_chunks_temp directories in output folders
        if os.path.exists(base_dir):
            for session_dir in os.listdir(base_dir):
                session_path = os.path.join(base_dir, session_dir)
                if os.path.isdir(session_path):
                    audio_chunks_path = os.path.join(session_path, "audio_chunks_temp")
                    if os.path.exists(audio_chunks_path):
                        # Check age
                        created_time = os.path.getctime(audio_chunks_path)
                        age_hours = (time.time() - created_time) / 3600

                        if age_hours > max_age_hours:
                            try:
                                shutil.rmtree(audio_chunks_path)
                                removed_count += 1
                                logger.info(f"Removed old audio chunks directory: {audio_chunks_path}")
                            except Exception as e:
                                logger.warning(f"Failed to remove {audio_chunks_path}: {str(e)}")
                                remaining_dirs.append(audio_chunks_path)
                        else:
                            remaining_dirs.append(audio_chunks_path)

        return removed_count, remaining_dirs

    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        return 0, []


def list_temp_directories(base_dir):
    """
    List all temporary directories with their information.
    Now lists both legacy system temp dirs and audio_chunks_temp dirs in output.

    Args:
        base_dir (str): Base directory to search (typically 'output')

    Returns:
        list: List of dictionaries with directory information
    """
    logger = setup_logging("Utils")
    dir_info = []

    try:
        # First, look for legacy system temp directories
        for item in os.listdir(tempfile.gettempdir()):
            if item.startswith("meeting_processor_") or item.startswith(
                "audio_processor_"
            ):
                temp_path = os.path.join(tempfile.gettempdir(), item)
                if os.path.isdir(temp_path):
                    # Get directory info
                    created_time = os.path.getctime(temp_path)
                    age_hours = (time.time() - created_time) / 3600

                    # Calculate size
                    total_size = 0
                    for dirpath, dirnames, filenames in os.walk(temp_path):
                        for filename in filenames:
                            filepath = os.path.join(dirpath, filename)
                            if os.path.exists(filepath):
                                total_size += os.path.getsize(filepath)

                    dir_info.append(
                        {
                            "path": temp_path,
                            "created": datetime.fromtimestamp(created_time).strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                            "age_hours": round(age_hours, 1),
                            "size_mb": round(total_size / (1024 * 1024), 2),
                            "type": "legacy_temp"
                        }
                    )

        # Now look for audio_chunks_temp directories in output folders
        if os.path.exists(base_dir):
            for session_dir in os.listdir(base_dir):
                session_path = os.path.join(base_dir, session_dir)
                if os.path.isdir(session_path):
                    audio_chunks_path = os.path.join(session_path, "audio_chunks_temp")
                    if os.path.exists(audio_chunks_path):
                        # Get directory info
                        created_time = os.path.getctime(audio_chunks_path)
                        age_hours = (time.time() - created_time) / 3600

                        # Calculate size
                        total_size = 0
                        for dirpath, dirnames, filenames in os.walk(audio_chunks_path):
                            for filename in filenames:
                                filepath = os.path.join(dirpath, filename)
                                if os.path.exists(filepath):
                                    total_size += os.path.getsize(filepath)

                        dir_info.append(
                            {
                                "path": audio_chunks_path,
                                "created": datetime.fromtimestamp(created_time).strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                "age_hours": round(age_hours, 1),
                                "size_mb": round(total_size / (1024 * 1024), 2),
                                "type": "audio_chunks"
                            }
                        )

        return sorted(dir_info, key=lambda x: x["age_hours"], reverse=True)

    except Exception as e:
        logger.error(f"Error listing temp directories: {str(e)}")
        return []
