import { useMemo, useState } from "react";
import type { League, Pick, Player } from "../shared/types";
import {
  positionCategories,
  positionOverview,
  type PositionCategory,
} from "../shared/positions";

function Candidates({
  players,
  onPlayer,
  label,
}: {
  players: Player[];
  onPlayer: (id: number) => void;
  label: string;
}) {
  return (
    <div className="position-candidates" aria-label={label}>
      {players.length ? (
        players.map((p) => (
          <button
            key={p.id}
            className="position-player"
            onClick={() => onPlayer(p.id)}
          >
            <span className="position-rank">
              {p.rank === null ? "—" : `#${p.rank}`}
            </span>
            <span>
              <strong>{p.name}</strong>
              <small>
                {p.team} · {p.positions.join("/") || "Position unknown"}
              </small>
            </span>
          </button>
        ))
      ) : (
        <p className="helper">No qualified players.</p>
      )}
    </div>
  );
}

export function PositionsView({
  players,
  picks,
  league,
  practice,
  onPlayer,
}: {
  players: Player[];
  picks: Pick[];
  league: League;
  practice: boolean;
  onPlayer: (id: number) => void;
}) {
  const overview = useMemo(
    () => positionOverview(players, picks, league.teams),
    [players, picks, league.teams],
  );
  const [poolPosition, setPoolPosition] = useState<PositionCategory>("PG");
  const [teamSelection, setTeamSelection] = useState<{
    id: number;
    position: PositionCategory;
  }>({ id: league.teamId, position: "G" });
  const selectedTeam = overview.teams.find((t) => t.id === teamSelection.id);
  return (
    <div className="positions-view">
      <section
        className="panel position-pool"
        aria-labelledby="position-pool-heading"
      >
        <div className="section-title">
          <h2 id="position-pool-heading">ESPN top 150 remaining</h2>
          <span>
            {overview.remaining} / {overview.total} players left
          </span>
        </div>
        <p className="helper">
          ESPN ranks 1–150. Each player counts once in every eligible category.
          Select a position to see who’s left.
        </p>
        {overview.total < 150 && (
          <p className="helper">
            The loaded player pool contains {overview.total} players ranked
            1–150.
          </p>
        )}
        <div className="position-totals">
          {positionCategories.map((position) => (
            <button
              key={position}
              className={`position-total ${poolPosition === position ? "selected" : ""}`}
              aria-pressed={poolPosition === position}
              aria-label={`${position}: ${overview.available[position].length} of ${overview.top[position].length} top 150 players left`}
              onClick={() => setPoolPosition(position)}
            >
              <span>{position}</span>
              <strong>{overview.available[position].length}</strong>
              <small>of {overview.top[position].length} left</small>
            </button>
          ))}
        </div>
        <h3 className="position-list-heading">
          Available {poolPosition} candidates{" "}
          <span>{overview.available[poolPosition].length}</span>
        </h3>
        <Candidates
          players={overview.available[poolPosition]}
          onPlayer={onPlayer}
          label={`Available ${poolPosition} candidates`}
        />
      </section>
      <section
        className="panel position-teams"
        aria-labelledby="position-teams-heading"
      >
        <div className="section-title">
          <h2 id="position-teams-heading">
            {practice ? "Practice" : "League"} position coverage
          </h2>
          <span>{league.teams.length} teams</span>
        </div>
        <p className="helper">
          Qualified candidates from all recorded picks. G includes PG/SG; F
          includes SF/PF. A player can count in several columns but can only
          fill one lineup slot at a time. Select a count to see the candidates.
        </p>
        <div
          className="position-table-scroll"
          tabIndex={0}
          role="region"
          aria-label="Team position coverage"
        >
          <table className="position-table">
            <thead>
              <tr>
                <th scope="col">Team</th>
                {positionCategories.map((position) => (
                  <th key={position} scope="col">
                    {position}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {overview.teams.map((team) => (
                <tr
                  key={team.id}
                  className={team.id === league.teamId ? "mine" : ""}
                >
                  <th scope="row">
                    <strong>
                      {team.name}
                      {team.id === league.teamId ? " · You" : ""}
                    </strong>
                    <small>
                      {team.drafted} drafted
                      {team.unknown > 0
                        ? ` · ${team.unknown} missing player data`
                        : ""}
                    </small>
                  </th>
                  {positionCategories.map((position) => {
                    const count = team.positions[position].length;
                    const selected =
                      teamSelection.id === team.id &&
                      teamSelection.position === position;
                    return (
                      <td key={position}>
                        <button
                          className={`position-count ${count ? "covered" : "no-candidates"} ${selected ? "selected" : ""}`}
                          aria-pressed={selected}
                          aria-label={`${team.name}, ${position}: ${count} candidates`}
                          onClick={() =>
                            setTeamSelection({ id: team.id, position })
                          }
                        >
                          {count}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {selectedTeam && (
          <>
            <h3 className="position-list-heading">
              {selectedTeam.name} · {teamSelection.position} candidates{" "}
              <span>
                {selectedTeam.positions[teamSelection.position].length}
              </span>
            </h3>
            <Candidates
              players={selectedTeam.positions[teamSelection.position]}
              onPlayer={onPlayer}
              label={`${selectedTeam.name} ${teamSelection.position} candidates`}
            />
          </>
        )}
      </section>
    </div>
  );
}
