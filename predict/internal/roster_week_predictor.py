from espn_api.basketball.player import Player
from common.week import Week


class RosterWeekPredictor:
    roster: [Player]
    week: Week

    def __init__(self, roster, week):
        self.roster = roster
        self.week = week

    def players_with_game(self, day: int) -> [Player]:
        team_playing = self.week.team_game_list[day]
        return [player for player in self.roster if player.proTeam in team_playing]

    def predict(self, daily_active_size=10, starting_day=0, injuryStatusList=['ACTIVE']) -> (int, int):
        lo = 0
        hi = 0
        for day in range(starting_day, self.week.scoring_period[1] - self.week.scoring_period[0] + 1):
            players_with_game = self.players_with_game(day)
            daily_lo = []
            daily_hi = []
            for player in players_with_game:
                if getattr(player, 'injuryStatus', 'ACTIVE') in injuryStatusList:
                    lo_stats, hi_stats = self.get_lo_hi_stats(player)
                    daily_lo.append(lo_stats)
                    daily_hi.append(hi_stats)
            daily_hi.sort(reverse=True)
            daily_lo.sort(reverse=True)
            lo += sum(daily_lo[:min(len(daily_lo), daily_active_size)])
            hi += sum(daily_hi[:min(len(daily_hi), daily_active_size)])
        return round(lo), round(hi)

    def get_total_number_of_games(self, daily_active_size=9, starting_day=0, injuryStatusList=['ACTIVE']) -> int:
        total = 0
        for day in range(starting_day, self.week.scoring_period[1] - self.week.scoring_period[0] + 1):
            players_with_game = self.players_with_game(day)
            eligible_players = [player for player in players_with_game if getattr(player, 'injuryStatus', 'ACTIVE') in injuryStatusList]
            total += min(len(eligible_players), daily_active_size)
        return total

    @staticmethod
    def get_lo_hi_stats(player: Player) -> (int, int):
        stat_period_list = ['2025', '2026_projected']
        fpts_for_stat_period = [RosterWeekPredictor.get_stat_from_stat_period(player, stat_period) for stat_period in stat_period_list]
        ignore_none_fpts_list = [fpts for fpts in fpts_for_stat_period if fpts is not None]
        if len(ignore_none_fpts_list) == 0:
            return 0, 0
        return min(ignore_none_fpts_list), max(ignore_none_fpts_list)

    @staticmethod
    def get_stat_from_stat_period(player: Player, stat_period: str):
        if stat_period not in player.stats:
            return None
        stats = player.stats[stat_period]
        return RosterWeekPredictor.get_fantasy_pts(stats['avg']) if 'avg' in stats else None

    @staticmethod
    def get_fantasy_pts(stats: dict) -> float:
        return (
                RosterWeekPredictor.get_stat_in_category(stats, 'PTS')
                + RosterWeekPredictor.get_stat_in_category(stats, '3PTM')
                - stats['FGA']
                + stats['FGM'] * 2
                - stats['FTA']
                + stats['FTM']
                + stats['REB']
                + stats['AST'] * 2
                + stats['STL'] * 4
                + RosterWeekPredictor.get_stat_in_category(stats, 'BLK') * 4
                - stats['TO'] * 2
        )
    @staticmethod
    def get_stat_in_category(stats: dict, cat: str) -> float:
        return stats.get(cat, 0)