"""Roster performance predictor for a given week."""
import math
import statistics
from typing import List, Tuple, Optional, Dict, Any

from espn_api.basketball.player import Player
from common.week import Week


class RosterWeekPredictor:
    """Predicts roster performance for a given week.
    
    Attributes:
        roster: List of players in the roster
        week: The Week object containing game schedule
    """

    roster: List[Player]
    week: Week

    def __init__(self, roster: List[Player], week: Week) -> None:
        """Initialize the predictor.
        
        Args:
            roster: List of Player objects
            week: Week object with game schedule
        """
        self.roster = roster
        self.week = week

    def players_with_game(self, day: int) -> List[Player]:
        """Get players whose team is playing on a given day.
        
        Args:
            day: The day index within the week
            
        Returns:
            List of players from teams playing that day
        """
        team_playing = self.week.team_game_list[day]
        return [player for player in self.roster if player.proTeam in team_playing]

    def predict(self, daily_active_size: int = 10, starting_day: int = 0, 
                injuryStatusList: List[str] = None) -> Tuple[float, float]:
        """Predict total points and variance for the week.
        
        Args:
            daily_active_size: Max number of players to count per day
            starting_day: Starting day index
            injuryStatusList: List of injury statuses to include (default: ['ACTIVE'])
            
        Returns:
            Tuple of (total_points, standard_deviation)
        """
        if injuryStatusList is None:
            injuryStatusList = ['ACTIVE']
            
        total_points: float = 0.0
        variances: float = 0.0
        
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
            day_points: float = sum(avg for avg, var, player in top_stats)
            day_variance: float = sum(var for avg, var, player in top_stats)
            total_points += day_points
            variances += day_variance
            
        return total_points, math.sqrt(variances)

    def get_total_number_of_games(self, daily_active_size: int = 9, starting_day: int = 0,
                                   injuryStatusList: List[str] = None) -> int:
        """Count total eligible player-days for the week.
        
        Args:
            daily_active_size: Max number of players to count per day
            starting_day: Starting day index
            injuryStatusList: List of injury statuses to include (default: ['ACTIVE'])
            
        Returns:
            Total number of player-days
        """
        if injuryStatusList is None:
            injuryStatusList = ['ACTIVE']
            
        total: int = 0
        for day in range(starting_day, self.week.scoring_period[1] - self.week.scoring_period[0] + 1):
            players_with_game = self.players_with_game(day)
            eligible_players = [
                player for player in players_with_game 
                if getattr(player, 'injuryStatus', 'ACTIVE') in injuryStatusList
            ]
            total += min(len(eligible_players), daily_active_size)
        return total

    @staticmethod
    def get_avg_variance_stats(player: Player) -> Tuple[float, float]:
        """Get average and variance of fantasy points for a player.
        
        Args:
            player: The player object
            
        Returns:
            Tuple of (average_fpts, variance_fpts)
        """
        stat_period_list: List[str] = ['2026_last_30', '2026_last_15', '2026_last_7', '2026_projected']
        fpts_for_stat_period: List[Optional[float]] = [
            RosterWeekPredictor.get_stat_from_stat_period(player, stat_period) 
            for stat_period in stat_period_list
        ]
        ignore_none_fpts_list: List[float] = [fpts for fpts in fpts_for_stat_period if fpts is not None]
        
        if len(ignore_none_fpts_list) == 0:
            return 0.0, 0.0
            
        avg: float = statistics.mean(ignore_none_fpts_list)
        variance: float = statistics.variance(ignore_none_fpts_list) if len(ignore_none_fpts_list) > 1 else 0.0
        return avg, variance

    @staticmethod
    def get_stat_from_stat_period(player: Player, stat_period: str) -> Optional[float]:
        """Get fantasy points from a specific stat period.
        
        Args:
            player: The player object
            stat_period: The stat period key (e.g., '2026_last_30')
            
        Returns:
            Fantasy points or None if period/stats not available
        """
        if stat_period not in player.stats:
            return None
        stats = player.stats[stat_period]
        return RosterWeekPredictor.get_fantasy_pts(stats['avg']) if 'avg' in stats else None

    @staticmethod
    def get_fantasy_pts(stats: Dict[str, Any]) -> float:
        """Calculate fantasy points from player stats.
        
        Args:
            stats: Dictionary of player statistics
            
        Returns:
            Total fantasy points
        """
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
    def get_stat_in_category(stats: Dict[str, Any], cat: str) -> float:
        """Get a stat value, defaulting to 0 if not present.
        
        Args:
            stats: Dictionary of statistics
            cat: Stat category name
            
        Returns:
            Stat value or 0 if not found
        """
        return stats.get(cat, 0)