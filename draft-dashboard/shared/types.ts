export interface Pick {
  overall: number;
  round: number;
  teamId: number;
  playerId: number | null;
  local?: boolean;
}
export interface League {
  id: number;
  season: number;
  name: string;
  teamId: number;
  teams: { id: number; name: string }[];
  draftAt: number;
  secondsPerPick: number;
  draftType: string;
  inProgress: boolean;
  completed: boolean;
  slots: Record<string, number>;
  weights: Record<string, number>;
  picks: Pick[];
}
export interface StatLine {
  fppg: number | null;
  games: number | null;
  total: number | null;
  minutes: number | null;
  stats: Record<string, number>;
}
export interface PreseasonGame {
  eventId: string;
  date: string;
  starter: boolean;
  minutes: number;
  fantasyPoints: number;
  stats: Record<string, string>;
}
export interface Preseason {
  gamesPlayed: number;
  starts: number;
  minutesPerGame: number;
  fantasyPointsPerGame: number;
  games: PreseasonGame[];
}
export interface Player {
  id: number;
  name: string;
  team: string;
  positions: string[];
  slots: string[];
  rank: number | null;
  adp: number | null;
  adpUncertain: boolean;
  injury: string;
  outlook: string;
  projected: StatLine;
  previous: StatLine;
  preseason: Preseason | null;
}
export interface Freshness {
  source: "live" | "snapshot" | "cache";
  fetchedAt: string;
  error?: string;
}
export interface DraftResponse {
  league: League;
  meta: Freshness;
}
export interface Bootstrap extends DraftResponse {
  players: Player[];
  playerMeta: Freshness;
  preseasonThrough: string | null;
  preseasonError?: string;
}
export interface Preference {
  target: boolean;
  avoid: boolean;
  priority: number;
  tier: string;
  round: string;
  note: string;
}
export interface SavedState {
  version: 1;
  leagueId: number;
  season: number;
  teamId: number;
  preferences: Record<string, Preference>;
  manualPicks: Pick[];
  practicePicks: Pick[];
}
