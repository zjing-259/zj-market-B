"""Candidate control must reject cross-project resources and fail closed on start."""
import copy
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('td06_environment', ROOT / 'scripts/td06-environment.py')
environment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(environment)


class Td06EnvironmentTest(unittest.TestCase):
    def setUp(self):
        self.config = environment.load(environment.WORK / 'compose.json')
        self.release = environment.load(environment.ROOT / 'docs/team-discovery-td05-release.json')

    def test_owned_configuration_and_cross_project_rejection(self):
        environment.validate_candidate_config(self.config, self.release)
        changes = [
            lambda c: c.update(name='zj-market-b06'),
            lambda c: c['services']['web']['ports'][0].update(published='443'),
            lambda c: c['volumes']['mysql-data'].update(name='zj-market-b06_mysql-data'),
            lambda c: c['services']['market-b'].update(image='sha256:wrong'),
            lambda c: c['services']['web']['volumes'][0].update(read_only=False),
        ]
        for change in changes:
            with self.subTest(change=change):
                wrong = copy.deepcopy(self.config)
                change(wrong)
                with self.assertRaises(RuntimeError):
                    environment.validate_candidate_config(wrong, self.release)

    def test_start_closes_web_before_schema_gate(self):
        commands = []
        def fake_run(args, sql=None):
            commands.append(args)
            if args[-2:] == ['--format', '{{.Names}}']:
                return '\n'.join(environment.PROJECT + '-' + service + '-1' for service in environment.SERVICES)
            return ''
        with patch.object(environment, 'run', side_effect=fake_run), \
             patch.object(environment, 'candidate_volumes'), \
             patch.object(environment, 'containers'), \
             patch.object(environment, 'ddl_state', return_value=('wrong-schema', 'wrong-history')):
            with self.assertRaisesRegex(RuntimeError, 'schema/history gate'):
                environment.candidate('start')
        stop_web = next(i for i, command in enumerate(commands) if command[-2:] == ['stop', 'web'])
        start_middleware = next(i for i, command in enumerate(commands) if command[-4:] == ['mysql', 'redis', 'namesrv', 'broker'])
        self.assertLess(stop_web, start_middleware)
        self.assertFalse(any(command[-3:] == ['marketing-a', 'market-b', 'web'] for command in commands))


if __name__ == '__main__':
    unittest.main()
