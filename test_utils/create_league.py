from espn_api.basketball import League

from common.io import find_credential_folder, get_single_line_string_from_file, get_file_content_from_crendential_folder


def create_league() -> League:
    return League(
        league_id=int(get_file_content_from_crendential_folder("league_id.txt")),
        year=2025,
        espn_s2=get_file_content_from_crendential_folder("espn_s2.secret"),
        swid=get_file_content_from_crendential_folder("swid.secret")
    )


