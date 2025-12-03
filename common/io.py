"""IO utilities for file and path management."""
import os


def get_match_up_output_html_path(league_id: int, week: int) -> str:
    """Get the output path for a match-up HTML file.
    
    Args:
        league_id: The league ID
        week: The week number
        
    Returns:
        The full path to the HTML file
    """
    return os.path.join(find_output_folder(), "{}_{}.html".format(league_id, week))


def find_output_folder() -> str:
    """Find the output folder path.
    
    Returns:
        The full path to the output folder
    """
    return os.path.join(find_root_folder(), "output")


def find_credential_folder() -> str:
    """Find the credentials folder path.
    
    Returns:
        The full path to the credentials folder
    """
    return os.path.join(find_root_folder(), "credentials")


def find_configs_folder() -> str:
    """Find the configs folder path.
    
    Returns:
        The full path to the configs folder
    """
    return os.path.join(find_root_folder(), "configs")


def find_root_folder() -> str:
    """Find the root project folder.
    
    Returns:
        The full path to the root folder
        
    Raises:
        Exception: If the project root folder cannot be found
    """
    curr_path: str = os.getcwd()
    directory: str = "fantasy_basketball_tools"
    index: int = curr_path.rfind(directory)
    if index == -1:
        raise Exception("Cannot find fatasy_basketball_tools")
    return curr_path[: index + len(directory)]


def get_file_content_from_crendential_folder(filename: str) -> str:
    """Read a single line from a file in the credentials folder.
    
    Args:
        filename: The filename to read from
        
    Returns:
        The first line of the file, stripped of whitespace
    """
    return get_single_line_string_from_file(os.path.join(find_credential_folder(), filename))


def get_single_line_string_from_file(filename: str) -> str:
    """Read a single line from a file.
    
    Args:
        filename: The full path to the file
        
    Returns:
        The first line of the file, stripped of whitespace
    """
    with open(filename) as f:
        content: str = f.readline().strip()
    return content
