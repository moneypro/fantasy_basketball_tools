"""One authorized, date-bounded Reed-for-Portis watch; invoked by a local timer."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/espn-add-drop/scripts'))
from add_drop import ESPN, DEFAULT_ENV, Refused, preflight, execute, verify

START = datetime.fromisoformat('2026-10-25T00:00:00-07:00')
END = datetime.fromisoformat('2026-10-25T03:00:00-07:00')
STATE_DIR = ROOT / 'output/reed_waiver_watch_2026-10-25'
ADD, DROP, TEAM = 4278562, 3064482, 2


def save(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def tick(api, directory, now, preview=False):
    """GET polling is repeatable; the exclusive transaction journal gates POST."""
    journal = directory / 'transaction'
    state_file = directory / 'status.json'
    if state_file.exists() and not preview:
        previous = json.loads(state_file.read_text())
        if previous.get('terminal'):
            return previous
    if journal.exists() and not preview:
        # A process may have died after sending POST. Never submit again.
        plan_file = journal / 'plan.json'
        if not plan_file.exists():
            return {'state': 'needs_review', 'terminal': True}
        plan = json.loads(plan_file.read_text())
        submission_file = journal / 'submission.json'
        submission = json.loads(submission_file.read_text()) if submission_file.exists() else {}
        result = verify(api, plan, submission)
        save(journal / 'verification.json', result)
        return {'state': result['state'], 'terminal': result['state'] in
                ('verified_completed', 'rejected_unchanged') or now >= END,
                'postAlreadyAttempted': True}
    if now < START and not preview:
        return {'state': 'waiting_for_window', 'terminal': False}
    if now >= END and not preview:
        return {'state': 'expired_without_acquisition', 'terminal': True}
    league = api.get('?view=mSettings&view=mTeam')
    if league['id'] != 30695 or league['seasonId'] != 2027:
        return {'state': 'identity_mismatch', 'terminal': True}
    period = league['status']['transactionScoringPeriod']
    pool = api.players(period, [ADD, DROP])
    reed, portis = pool[ADD], pool[DROP]
    detail = {'reedStatus': reed['status'], 'reedOwner': reed['onTeamId'],
              'waiverProcessDate': reed.get('waiverProcessDate'), 'effectivePeriod': period}
    if reed['onTeamId'] != 0:
        return {'state': 'reed_already_owned', 'terminal': True, **detail}
    if portis['onTeamId'] != TEAM or portis['status'] != 'ONTEAM':
        return {'state': 'portis_no_longer_rostered', 'terminal': True, **detail}
    if reed['status'] != 'FREEAGENT':
        return {'state': 'waiting_for_free_agent', 'terminal': False, **detail}
    if preview:
        return {'state': 'preview_free_agent', 'terminal': False, **detail}
    # Rechecks ownership, locks, acquisition budget and session immediately before POST.
    plan = preflight(api, TEAM, ADD, DROP)
    if datetime.now(timezone.utc) >= END:
        return {'state': 'expired_without_acquisition', 'terminal': True}
    result = execute(api, plan, journal)
    return {'state': result['state'], 'terminal': result['state'] in
            ('verified_completed', 'rejected_unchanged'), 'postAlreadyAttempted': True,
            'effectivePeriod': plan['effectivePeriod'], 'newPlayerSlot': 'BE'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='store_true', help='GET only; do not persist job state')
    args = parser.parse_args()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with (STATE_DIR / 'watch.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        now = datetime.now(timezone.utc)
        try:
            result = tick(ESPN(2027, 30695, DEFAULT_ENV), STATE_DIR, now, args.preview)
        except (Refused, OSError, ValueError, KeyError, StopIteration) as exc:
            result = {'state': 'check_failed', 'terminal': now >= END,
                      'errorType': type(exc).__name__}
        result['checkedAt'] = now.isoformat()
        if not args.preview:
            save(STATE_DIR / 'status.json', result)
            with (STATE_DIR / 'checks.jsonl').open('a') as log:
                log.write(json.dumps(result) + '\n')
        print(json.dumps(result))


if __name__ == '__main__':
    main()
