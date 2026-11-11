# Verified ESPN basketball transaction API

Read endpoint:
`https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{season}/segments/0/leagues/{league}`

Write endpoint: same path on `lm-api-writes.fantasy.espn.com`, ending `/transactions/`.

Authentication: existing `espn_s2` and `SWID` cookies. HTTP JSON headers; Origin/Referer `https://fantasy.espn.com`. Do not expose member IDs or cookie values in output.

GET views:
- `mSettings&mTeam`: identity, current/effective periods, primaryOwner, transaction limits and roster settings.
- `mRoster&scoringPeriodId={effective}`: effective roster entries/slots.
- `kona_player_info&scoringPeriodId={effective}` with `x-fantasy-filter: {"players":{"filterIds":{"value":[ADD_ID,DROP_ID]}}}`: exact IDs, fullName, onTeamId, status, droppable, eligibleSlots and lock flags.
- `mTransactions2`: transaction records. Compare the exact team and ADD/DROP pair, and distinguish IDs already present before the request.

For unknown IDs, paginate `kona_player_info` with `players.limit=500`, `players.offset`, and `sortDraftRanks={"sortPriority":1,"sortAsc":true,"value":"STANDARD"}`. Match fullName and proTeamId; confirm ambiguous names with the user. Do not recommend owned players as free agents.

Request shape, supported by executed transactions in the live basketball league:

```json
{
  "isLeagueManager": false,
  "teamId": 2,
  "type": "FREEAGENT",
  "scoringPeriodId": 2,
  "executionType": "EXECUTE",
  "items": [
    {"playerId": 5061589, "type": "ADD", "fromTeamId": 0, "toTeamId": 2,
     "fromLineupSlotId": -1, "toLineupSlotId": 12},
    {"playerId": 4684793, "type": "DROP", "fromTeamId": 2, "toTeamId": 0,
     "fromLineupSlotId": 12, "toLineupSlotId": -1}
  ]
}
```

IDs above are historical examples only. Use the current period in POST, and the drop slot from the effective roster. ESPN may normalize the drop's source slot to its current-day slot in the executed response; verify IDs/ownership, not exact echo equality. Bench is basketball slot 12; confirm its capacity in the league settings and eligibility on the add player.

The successful October 21, 2026 transaction used season 2027, current period 2 and effective roster period 3. Missi became ONTEAM/team 2, Filipowski unowned; both changes were in one EXECUTED record, `isPending=false`. Readback of period 3 showed Missi in BE. Evidence remains at `/home/hong/fantasy_basketball_tools/output/missi_add_2026-10-21/corrected_result.json`.

HTTP 200 alone is insufficient: inspect business status/messages and perform independent readback. Preserve only sanitized transaction/error fields, player identities, ownership and lineup summaries in journals. Do not log full league/member payloads or HTTP headers.

## Waiver claim submission

Verified for this league's `WAIVERS_TRADITIONAL` mode with `isUsingAcquisitionBudget=false`: use the same paired ADD/DROP item structure as above, set `type` to `WAIVER`, retain `executionType: EXECUTE`, and send the current `scoringPeriodId`. Do not include an invented FAAB bid or force a claim priority/rank. In this context EXECUTE submits the claim; it does not mean that the player is awarded immediately.

On October 26, 2026, the live request used ADD 4433249 / DROP 4431785, team 2, season 2027, current period 7 and effective roster period 8. ESPN returned HTTP 200 with type WAIVER, status PENDING and `isPending=true`; a separate `mTransactions2` read verified the same transaction and the effective roster was unchanged. Evidence: `output/diabate_waiver_20261027/submission.json` and `readback.json`. ESPN normalized the DROP source slot from the requested period-8 bench slot to the current-day slot; exact player pair and ownership/roster verification are authoritative.

The existing `add_drop.py` transaction matching and verification helpers only accept FREEAGENT. A waiver runner must explicitly match WAIVER and use the pending/award checks in [waivers.md](waivers.md). Preserve one-shot journaling; historical runners are not reusable submission commands. This request shape does not establish support for FAAB bids, claim reordering, or cancellation.

## Pickup lineup activation

Use the explicit CLI in `line_up/line_up_editer.py` after the add/drop readback. Current-period lineup changes require transaction type `ROSTER`; future-period changes use `FUTURE_ROSTER`. Each item has `type: LINEUP`, player ID, and source/destination lineup slots. Submit the pickup activation and any displaced-player bench move together.

Verified October 25, 2026: period 6 `ROSTER` transaction `7ce250ef-55a1-4d71-9081-14636e8401ac` moved Collier from BE to UT and Duren from UT to BE; Post was already at C. Exact full-roster slot readback passed. Evidence: `output/activate_collier_post_20261025_current/`. An initial `FUTURE_ROSTER` request for the current period was definitively rejected with `TRAN_INVALID_SCORINGPERIOD_NOT_FUTURE`; unchanged roster and no matching transaction were verified before the corrected request. These are historical records, not instructions to repeat the moves.
