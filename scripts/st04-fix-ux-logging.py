"""Add the stdout logger required by the frozen A image in the UX stack."""
from pathlib import Path
import argparse


def main(root: Path) -> None:
    root = root.resolve(strict=True)
    if root.name != 'zj-market-ux':
        raise RuntimeError('Refusing non-UX target')
    compose = root / 'deploy/b06/compose.yml'
    source = compose.read_text(encoding='utf-8')
    a_begin = source.index('  marketing-a:')
    a_end = source.index('  market-b:', a_begin)
    a = source[a_begin:a_end]
    command = '    - --spring.config.location=file:/etc/b06/application.properties,file:/run/secrets/a.properties\n'
    assert a.count(command) == 1
    a = a.replace(command, command + '    - --logging.config=file:/etc/b06/logback-ux.xml\n')
    mount = ('    - type: bind\n'
             f'      source: {root.as_posix()}/.local/b06/runtime/logback-ux.xml\n'
             '      target: /etc/b06/logback-ux.xml\n'
             '      read_only: true\n'
             '      bind:\n'
             '        create_host_path: false\n')
    assert a.count('    healthcheck:\n') == 1
    a = a.replace('    healthcheck:\n', mount + '    healthcheck:\n')
    compose.write_text(source[:a_begin] + a + source[a_end:], encoding='utf-8')
    logger = root / '.local/b06/runtime/logback-ux.xml'
    if logger.exists():
        raise RuntimeError('UX logger already exists')
    logger.write_text('''<configuration>
  <appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">
    <encoder><pattern>%d %-5level %logger{32} - %msg%n</pattern></encoder>
  </appender>
  <root level="INFO"><appender-ref ref="STDOUT"/></root>
</configuration>
''', encoding='utf-8')
    print('Configured UX A stdout logging.')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    main(p.parse_args().root)
