"""Isolated lifecycle tests: no Docker or browser process is invoked."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).with_name('stable-controller.py')
spec = importlib.util.spec_from_file_location('stable_controller', SOURCE)
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


class LifecycleTest(unittest.TestCase):
    def setUp(self):
        workspace = Path(__file__).resolve().parents[2]
        temporary_root = workspace / 'target/stable-isolation/st02-tests'
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=temporary_root)
        if not Path(self.temporary.name).resolve().is_relative_to(temporary_root.resolve()):
            raise RuntimeError('Temporary test path escaped workspace')
        self.addCleanup(self.temporary.cleanup)
        self.subject = object.__new__(controller.Controller)
        self.subject.root = Path(self.temporary.name)
        self.subject.state_dir = self.subject.root / 'state'
        self.subject.release_dir = self.subject.root / 'releases' / controller.RELEASE
        self.subject.release = {'nodeExecutable': 'node', 'edgeExecutable': 'edge'}
        self.calls = []
        self.mode = 'OPEN'
        self.rows = {}
        self.ready_result = {'status': 'READY'}
        self.subject.armed = lambda: self.calls.append('armed')
        self.subject.preflight = lambda: self.calls.append('preflight')
        self.subject.inspect = lambda: self.rows
        self.subject.running_healthy = lambda rows: bool(rows) and all(rows.values())
        self.subject.adopted = lambda rows: True
        self.subject.gateway_mode = lambda: self.mode
        self.subject.schema = lambda: self.calls.append('schema')
        self.subject.ready = lambda: self.ready_result
        self.subject.record = lambda value: self.calls.append('record:' + value)
        self.subject.close_after_failure = lambda: self.calls.append('close-gateway')
        self.subject.run = lambda label, command, **_kwargs: self.calls.append(label)
        def compose(mode, *args):
            label = mode + ':' + ' '.join(args)
            self.calls.append(label)
            if mode == 'maintenance' and 'up' in args and 'web' in args:
                self.mode = 'MAINTENANCE'
            if mode == 'on' and 'web' in args:
                self.mode = 'OPEN'
        self.subject.compose = compose

    def test_repeated_start_is_read_only(self):
        self.rows = {name: True for name in controller.SERVICES}
        self.assertEqual(self.subject.start()['status'], 'READY')
        self.assertEqual(self.calls, ['armed', 'preflight'])

    def test_precondition_failure_does_not_change_gateway(self):
        for failure in ('missing image', 'missing volume', 'config drift'):
            with self.subTest(failure=failure):
                self.calls.clear()
                self.subject.preflight = lambda: (_ for _ in ()).throw(RuntimeError(failure))
                with self.assertRaisesRegex(RuntimeError, failure):
                    self.subject.start()
                self.assertEqual(self.calls, ['armed'])
                self.assertEqual(self.mode, 'OPEN')

    def test_stopped_start_orders_services_then_opens(self):
        self.mode = 'MAINTENANCE'
        self.assertEqual(self.subject.start()['status'], 'READY')
        middleware = next(i for i, item in enumerate(self.calls) if item.startswith('maintenance:up') and 'mysql' in item)
        schema = self.calls.index('schema')
        app = next(i for i, item in enumerate(self.calls) if item.startswith('maintenance:up') and 'marketing-a' in item)
        open_web = next(i for i, item in enumerate(self.calls) if item.startswith('on:up') and 'web' in item)
        self.assertLess(middleware, schema)
        self.assertLess(schema, app)
        self.assertLess(app, open_web)
        self.assertEqual(self.calls[-1], 'record:READY')

    def test_failure_after_start_attempt_closes_gateway(self):
        self.mode = 'MAINTENANCE'
        self.subject.schema = lambda: (_ for _ in ()).throw(RuntimeError('schema drift'))
        with self.assertRaisesRegex(RuntimeError, 'schema drift'):
            self.subject.start()
        self.assertEqual(self.calls[-2:], ['close-gateway', 'record:FAILED_GATE_CLOSED'])

    def test_failed_post_open_probe_closes_gateway(self):
        self.mode = 'MAINTENANCE'
        self.subject.ready = lambda: (_ for _ in ()).throw(RuntimeError('probe failed'))
        with self.assertRaisesRegex(RuntimeError, 'probe failed'):
            self.subject.start()
        self.assertEqual(self.calls[-2:], ['close-gateway', 'record:FAILED_GATE_CLOSED'])

    def test_stop_failure_keeps_gateway_closed(self):
        self.rows = {name: True for name in controller.SERVICES}
        def compose(mode, *args):
            self.calls.append(mode + ':' + ' '.join(args))
            if 'up' in args:
                self.mode = 'MAINTENANCE'
            if 'stop' in args:
                raise RuntimeError('stop failed')
        self.subject.compose = compose
        with self.assertRaisesRegex(RuntimeError, 'stop failed'):
            self.subject.stop()
        self.assertEqual(self.calls[-2:], ['close-gateway', 'record:FAILED_GATE_CLOSED'])

    def test_stop_closes_gateway_before_services(self):
        self.rows = {name: True for name in controller.SERVICES}
        self.assertEqual(self.subject.stop()['status'], 'STOPPED')
        web = next(i for i, item in enumerate(self.calls) if item.startswith('maintenance:up') and 'web' in item)
        stopping = self.calls.index('record:STOPPING')
        services = next(i for i, item in enumerate(self.calls) if item.startswith('maintenance:stop'))
        self.assertLess(web, stopping)
        self.assertLess(stopping, services)
        self.assertEqual(self.calls[-1], 'record:STOPPED')

    def test_open_requires_ready_then_launches_browser(self):
        self.subject.ready = lambda: self.calls.append('ready')
        self.assertEqual(self.subject.open()['status'], 'BROWSER_OPENED')
        self.assertEqual(self.calls, ['ready', 'open stable browser'])

    def test_image_and_volume_identity_fail_closed(self):
        self.subject.docker = ['fake-docker']
        self.subject.release = {'images': {'web': 'sha256:expected'}, 'volumes': ['v'],
                                'networks': ['n'], 'volumeIdentity': {'v': 'original'},
                                'networkIdentity': {'n': 'network-id'}}
        def missing_image(_label, args, **_kwargs):
            if 'image' in args:
                return json.dumps([{'Id': 'sha256:other'}])
            return '[]'
        self.subject.run = missing_image
        with self.assertRaisesRegex(RuntimeError, 'Image ID changed'):
            self.subject.docker_inventory()
        def missing_volume(_label, args, **_kwargs):
            if 'image' in args:
                return json.dumps([{'Id': 'sha256:expected'}])
            return '[]'
        self.subject.run = missing_volume
        with self.assertRaisesRegex(RuntimeError, 'Existing five volumes missing'):
            self.subject.docker_inventory()

    def test_cross_process_style_lock_rejects_second_owner(self):
        with self.subject.lock():
            with self.assertRaises(OSError):
                with self.subject.lock():
                    pass


if __name__ == '__main__':
    unittest.main()
