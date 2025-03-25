
def format_file_size(size_in_bytes: int) -> str:
    """
    Converts a file size in bytes to a human-readable format (Bytes, KB, MB, GB, etc.).

    Args:
        size_in_bytes (int): The file size in bytes.

    Returns:
        str: Human-readable file size.
    """
    units = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']  # Add more if needed
    size = float(size_in_bytes)
    for unit in units:
        if size < 1024:
            return f"{size:.2f} {unit}"  # Format to 2 decimal places
        size /= 1024
    return f"{size:.2f} {units[-1]}"  # For extremely large sizes


def format_length_from_milliseconds(milliseconds: int) -> str:
    # Convert milliseconds to total seconds
    total_seconds = milliseconds // 1000
    seconds = total_seconds % 60
    total_minutes = total_seconds // 60
    minutes = total_minutes % 60
    hours = total_minutes // 60

    # Format seconds as double digits
    seconds_str = f"{seconds:02}"

    # Format minutes: double digits only if more than 9 minutes or if hours are present
    if hours > 0 or minutes >= 10:
        minutes_str = f"{minutes:02}"
    else:
        minutes_str = f"{minutes}"

    # Format hours (if any): just as they are, no padding
    if hours > 0:
        return f"{hours}:{minutes_str}:{seconds_str}"
    else:
        return f"{minutes_str}:{seconds_str}"
