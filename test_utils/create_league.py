from espn_api.basketball import League
import os


def find_credential_folder() -> str:
    curr_path = os.getcwd()
    directory = "fantasy_basketball_tools"
    index = curr_path.find(directory)
    if index == -1:
        raise Exception("Cannot find fatasy_basketball_tools")
    return os.path.join(curr_path[: index + len(directory)], "credentials")


def create_league() -> League:
    return League(
        league_id=int(get_single_line_string_from_file(find_credential_folder() + "/league_id.txt")),
        year=2023,
        espn_s2=get_single_line_string_from_file(find_credential_folder() + "/espn_s2.secret"),
        swid=get_single_line_string_from_file(find_credential_folder() + "/swid.secret")
    )


def get_single_line_string_from_file(filename: str) -> str:
    with open(filename) as f:
        content = f.readline().strip()
    return content
