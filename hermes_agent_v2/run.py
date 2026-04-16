from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from bootstrap import prepare

RUNTIME_STATUS = Path('/data/runtime/services.json')


def _write_status(payload: dict) -> None:
    RUNTIME_STATUS.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_STATUS.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding='utf-8')


def _dashboard_available() -> bool:
    try:
        result = subprocess.run(['hermes', 'dashboard', '--help'], capture_output=True, text=True, timeout=15)
        return result.returncode == 0
    except Exception:
        return False


class Supervisor:
    def __init__(self, settings: dict):
        self.settings = settings
        self.procs: dict[str, asyncio.subprocess.Process] = {}
        self.stopping = False

    async def start(self) -> None:
        env = os.environ.copy()
        env.update(self.settings['env'])
        await self._start_gateway(env)
        if self.settings['enable_dashboard'] and _dashboard_available():
            await self._start_dashboard(env)
        await self._start_ui(env)
        _write_status({'state': 'running', 'services': list(self.procs.keys())})

    async def _start_gateway(self, env: dict[str, str]) -> None:
        proc = await asyncio.create_subprocess_exec('hermes', 'gateway', 'run', env=env, stdout=sys.stdout, stderr=sys.stderr)
        self.procs['gateway'] = proc

    async def _start_dashboard(self, env: dict[str, str]) -> None:
        proc = await asyncio.create_subprocess_exec(
            'hermes', 'dashboard',
            '--host', self.settings['dashboard_host'],
            '--port', str(self.settings['dashboard_port']),
            '--no-open',
            env=env,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        self.procs['dashboard'] = proc

    async def _start_ui(self, env: dict[str, str]) -> None:
        proc = await asyncio.create_subprocess_exec(
            'python3', '-m', 'uvicorn', 'hermes_ui.server:app',
            '--host', '0.0.0.0', '--port', str(self.settings['ui_port']),
            env=env,
            cwd='/opt/hermes-ha-addon',
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        self.procs['ui'] = proc

    async def run(self) -> int:
        await self.start()
        while not self.stopping:
            tasks = [asyncio.create_task(proc.wait(), name=name) for name, proc in self.procs.items()]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            for task in done:
                name = task.get_name()
                code = task.result()
                if self.stopping:
                    return 0
                _write_status({'state': 'failed', 'service': name, 'exit_code': code})
                await self.stop()
                return code or 1
        return 0

    async def stop(self) -> None:
        if self.stopping:
            return
        self.stopping = True
        for proc in self.procs.values():
            if proc.returncode is None:
                proc.terminate()
        await asyncio.sleep(1)
        for proc in self.procs.values():
            if proc.returncode is None:
                proc.kill()
        _write_status({'state': 'stopped'})


async def amain() -> int:
    settings = prepare()
    supervisor = Supervisor(settings)
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_stop() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_stop)

    runner = asyncio.create_task(supervisor.run())
    waiter = asyncio.create_task(stop_event.wait())
    done, pending = await asyncio.wait({runner, waiter}, return_when=asyncio.FIRST_COMPLETED)
    if waiter in done:
        await supervisor.stop()
        await runner
        return 0
    for task in pending:
        task.cancel()
    return runner.result()


if __name__ == '__main__':
    raise SystemExit(asyncio.run(amain()))
