from line_up.line_up_editer import LineUpEditor
from test_utils.create_league import create_league


def change_line_up_for_next_7_days():
    league = create_league()
    editor = LineUpEditor(league, 14)
    editor.fill_line_up(81, ignore_injury=True)


if __name__ == '__main__':
    change_line_up_for_next_7_days()
