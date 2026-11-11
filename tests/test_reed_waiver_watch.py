import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('watch', Path(__file__).resolve().parents[1] / 'tools/reed_waiver_watch.py')
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)


class WatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.api = Mock()
        self.api.get.return_value = {'id': 30695, 'seasonId': 2027, 'status': {'transactionScoringPeriod': 6}}
        self.pool = {watch.ADD: {'status': 'WAIVERS', 'onTeamId': 0},
                     watch.DROP: {'status': 'ONTEAM', 'onTeamId': 2}}
        self.api.players.return_value = self.pool

    def test_waivers_never_submit(self):
        with patch.object(watch, 'execute') as execute:
            self.assertEqual(watch.tick(self.api, self.directory, watch.START)['state'], 'waiting_for_free_agent')
            execute.assert_not_called()

    def test_owned_elsewhere_stops(self):
        self.pool[watch.ADD].update(status='ONTEAM', onTeamId=5)
        self.assertTrue(watch.tick(self.api, self.directory, watch.START)['terminal'])
        self.api.post.assert_not_called()

    def test_missing_drop_stops(self):
        self.pool[watch.DROP]['onTeamId'] = 0
        self.assertEqual(watch.tick(self.api, self.directory, watch.START)['state'], 'portis_no_longer_rostered')

    def test_expired_never_reads_or_submits(self):
        self.assertTrue(watch.tick(self.api, self.directory, watch.END)['terminal'])
        self.api.get.assert_not_called()

    def test_preview_free_agent_does_not_submit(self):
        self.pool[watch.ADD]['status'] = 'FREEAGENT'
        with patch.object(watch, 'execute') as execute:
            self.assertEqual(watch.tick(self.api, self.directory, watch.START, True)['state'], 'preview_free_agent')
            execute.assert_not_called()

    def test_free_agent_uses_fresh_preflight_and_one_paired_execution(self):
        self.pool[watch.ADD]['status'] = 'FREEAGENT'
        with patch.object(watch, 'datetime') as clock, \
             patch.object(watch, 'preflight', return_value={'effectivePeriod': 6}) as preflight, \
             patch.object(watch, 'execute', return_value={'state': 'verified_completed'}) as execute:
            clock.now.return_value = watch.START
            result = watch.tick(self.api, self.directory, watch.START)
            self.assertEqual(result['state'], 'verified_completed')
            preflight.assert_called_once_with(self.api, 2, 4278562, 3064482)
            execute.assert_called_once()

    def test_existing_attempt_only_reconciles(self):
        journal = self.directory / 'transaction'
        journal.mkdir()
        (journal / 'plan.json').write_text(json.dumps({'effectivePeriod': 6}))
        with patch.object(watch, 'verify', return_value={'state': 'unverified'}) as verify, \
             patch.object(watch, 'execute') as execute:
            result = watch.tick(self.api, self.directory, watch.START)
            self.assertEqual(result['state'], 'unverified')
            verify.assert_called_once()
            execute.assert_not_called()

    def test_completed_state_never_repeats(self):
        (self.directory / 'status.json').write_text(json.dumps({'terminal': True, 'state': 'verified_completed'}))
        self.assertEqual(watch.tick(self.api, self.directory, watch.START)['state'], 'verified_completed')
        self.api.get.assert_not_called()


if __name__ == '__main__':
    unittest.main()
