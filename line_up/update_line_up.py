from line_up.line_up_editer import LineUpEditor
from utils.create_league import create_league

MONEY_PRO_TEAM_ID = 2

def change_line_up_for_next_7_days():
    league = create_league()
    editor = LineUpEditor(league, MONEY_PRO_TEAM_ID)
    editor.fill_line_up(81, ignore_injury=True)


if __name__ == '__main__':
    change_line_up_for_next_7_days()
