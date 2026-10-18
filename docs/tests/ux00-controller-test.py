"""UX-00 lifecycle preflight tests; never connect to Docker or alter the live gate."""
import importlib.util
from pathlib import Path
from unittest.mock import Mock

path = Path('D:/Java/zj-market-ux/scripts/b06-deployment.py')
spec = importlib.util.spec_from_file_location('ux_deployment', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def deployment(mode='open', phase='READY', image_matches=True, actual_mode='open'):
    obj = module.Deployment.__new__(module.Deployment)
    obj.state = Mock(return_value={'project': 'zj-market-ux', 'mode': mode, 'phase': phase})
    obj.ready = Mock(return_value={'mode': mode, 'phase': phase})
    obj.web_image_matches_release = Mock(return_value=image_matches)
    obj.gateway_mode = Mock(return_value=actual_mode)
    obj.configuration = Mock(side_effect=AssertionError('preflight changed configuration'))
    return obj


duplicate = deployment()
duplicate.start('open', 'open')
duplicate.configuration.assert_not_called()
duplicate.ready.assert_called_once()

for phase, mode, action in [('READY', 'maintenance', 'start'), ('GATED', 'open', 'open'),
                            ('STOPPING', 'open', 'open')]:
    case = deployment(phase=phase)
    try:
        case.start(mode, action)
    except RuntimeError:
        pass
    else:
        raise AssertionError(f'{phase}/{action} should reject before mutation')
    case.configuration.assert_not_called()

drift = deployment(actual_mode='maintenance')
try:
    drift.start('open', 'open')
except RuntimeError:
    pass
else:
    raise AssertionError('Saved/open gate drift should reject before mutation')
drift.configuration.assert_not_called()

upgrade = deployment(image_matches=False)
assert upgrade.preflight_start(upgrade.state(), 'open', 'open') is False
upgrade.configuration.assert_not_called()

capacity = deployment(image_matches=False)
capacity.capacity = Mock(side_effect=RuntimeError('host below threshold'))
try:
    capacity.start('open', 'open')
except RuntimeError:
    pass
else:
    raise AssertionError('Low memory must reject the UX transition')
capacity.configuration.assert_not_called()
print('UX00_CONTROLLER_PREFLIGHT_PASS duplicate/start/unsupported/drift/upgrade/capacity')
