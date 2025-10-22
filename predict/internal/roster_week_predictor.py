import math

from espn_api.basketball.player import Player
from common.week import Week

import statistics

class RosterWeekPredictor:
    roster: [Player]
    week: Week

    def __init__(self, roster, week):
        self.roster = roster
        self.week = week

    def players_with_game(self, day: int) -> [Player]:
        team_playing = self.week.team_game_list[day]
        return [player for player in self.roster if player.proTeam in team_playing]

    def predict(self, daily_active_size=10, starting_day=0, injuryStatusList=['ACTIVE']) -> (float, float):
        total_points = 0
        variances = 0
        for day in range(starting_day, self.week.scoring_period[1] - self.week.scoring_period[0] + 1):
            players_with_game = [
                player for player in self.players_with_game(day)
                if getattr(player, 'injuryStatus', 'ACTIVE') in injuryStatusList
            ]
            # Get (avg, var, player) for each eligible player
            player_stats = [
                (self.get_avg_variance_stats(player)[0], self.get_avg_variance_stats(player)[1], player)
                for player in players_with_game
            ]
            # Sort by avg descending
            player_stats.sort(reverse=True, key=lambda x: x[0])
            # Take top N
            top_stats = player_stats[:daily_active_size]
            # Sum their avg and variance
            day_points = sum(avg for avg, var, player in top_stats)
            day_variance = sum(var for avg, var, player in top_stats)
            total_points += day_points
            variances += day_variance
        return total_points, math.sqrt(variances)

    def get_total_number_of_games(self, daily_active_size=9, starting_day=0, injuryStatusList=['ACTIVE']) -> int:
        total = 0
        for day in range(starting_day, self.week.scoring_period[1] - self.week.scoring_period[0] + 1):
            players_with_game = self.players_with_game(day)
            eligible_players = [player for player in players_with_game if getattr(player, 'injuryStatus', 'ACTIVE') in injuryStatusList]
            total += min(len(eligible_players), daily_active_size)
        return total


    @staticmethod
    def get_avg_variance_stats(player: Player) -> (float, float):
        stat_period_list = ['2026_last_30', '2026_last_15', '2026_last_7', '2026_projected']
        fpts_for_stat_period = [RosterWeekPredictor.get_stat_from_stat_period(player, stat_period) for stat_period in stat_period_list]
        ignore_none_fpts_list = [fpts for fpts in fpts_for_stat_period if fpts is not None]
        if len(ignore_none_fpts_list) == 0:
            return 0, 0
        avg = statistics.mean(ignore_none_fpts_list)
        variance = statistics.variance(ignore_none_fpts_list) if len(ignore_none_fpts_list) > 1 else 0.0
        return avg, variance

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