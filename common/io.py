import os


def get_match_up_output_html_path(league_id:int, week: int) -> str:
    return os.path.join(find_output_folder(), "{}_{}.html".format(league_id, week))

def find_output_folder() -> str:
    return os.path.join(find_root_folder(), "output")


def find_credential_folder() -> str:
    return os.path.join(find_root_folder(), "credentials")


def find_root_folder() -> str:
    curr_path = os.getcwd()
    directory = "fantasy_basketball_tools"
    index = curr_path.find(directory)
    if index == -1:
        raise Exception("Cannot find fatasy_basketball_tools")
    return curr_path[: index + len(directory)]

def get_file_content_from_crendential_folder(filename: str) -> str:
    return get_single_line_string_from_file(os.path.join(find_credential_folder(), filename))


def get_single_line_string_from_file(filename: str) -> str:
    with open(filename) as f:
        content = f.readline().strip()
    return content