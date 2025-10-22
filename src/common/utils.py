import os


def size_to_string(value: float) -> str:
    """
    Convert a size in bytes to a human-readable string representation.
    
    Converts a numeric byte value to a formatted string using appropriate
    binary units (B, KiB, MiB, GiB, TiB). The value is automatically scaled
    to the most suitable unit.
    
    Args:
        value: Size in bytes to convert
        
    Returns:
        Formatted string with the size and appropriate unit (e.g., "1.50 MiB")
        
    Raises:
        ValueError: If the value is negative
    """
    if value < 0:
        raise ValueError("Size must be non-negative")

    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    index = 0
    while value >= 1024 and index < len(units) - 1:
        value /= 1024.0
        index += 1

    return f"{value:.2f} {units[index]}"


def is_valid_destination_file_path(destination_file_path: str) -> bool:
    """
    Validate that a file path is suitable for writing.
    
    Checks if the provided path can be used as a destination for writing
    a file. Validates that the parent directory exists, has write permissions,
    and that the path itself is not a directory.
    
    Args:
        destination_file_path: Path to validate for file writing
        
    Returns:
        True if the path is valid for writing a file, False otherwise
    """
    if not destination_file_path or destination_file_path.isspace():
        return False

    # Get directory of destination
    dest_dir = os.path.dirname(destination_file_path) or "."

    # Check if directory exists
    if not os.path.exists(dest_dir):
        return False

    # Check if destination path is a directory
    if os.path.isdir(destination_file_path):
        return False

    # Check write permissions
    if not os.access(dest_dir, os.W_OK):
        return False

    return True

def is_valid_destination_directory_path(destination_directory_path: str) -> bool:
    """
    Validate that a directory path exists and is writable.
    
    Checks if the provided path points to an existing directory with
    write permissions, making it suitable for writing files into.
    
    Args:
        destination_directory_path: Directory path to validate
        
    Returns:
        True if the path is a valid writable directory, False otherwise
    """
    if not destination_directory_path or destination_directory_path.isspace():
        return False

    # Check if directory exists
    if not os.path.exists(destination_directory_path):
        return False

    # Check if destination path is not a directory
    if not os.path.isdir(destination_directory_path):
        return False

    # Check write permissions
    if not os.access(destination_directory_path, os.W_OK):
        return False

    return True
