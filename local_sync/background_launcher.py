"""Start the existing DPAPI runner without creating a Windows console."""
from datetime import datetime
from pathlib import Path
import argparse
import os
import subprocess

ROOT=Path(__file__).resolve().parent
CREATE_NO_WINDOW=0x08000000


def run(root=ROOT,manual=False,execute=subprocess.run):
    try:
        powershell=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
        command=[str(powershell),'-NoProfile','-NonInteractive','-ExecutionPolicy','RemoteSigned','-File',str(root/'run_daily.ps1')]
        if manual:command.append('-Manual')
        result=execute(command,cwd=str(root),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,creationflags=CREATE_NO_WINDOW,check=False)
        return result.returncode
    except Exception:
        # No exception contents: these may contain secrets or local file paths.
        state=root/'daily-state';state.mkdir(exist_ok=True)
        with (state/'launcher.log').open('a',encoding='utf-8') as f:
            f.write(datetime.now().isoformat(timespec='seconds')+' Background launcher failed: PROCESS_START\n')
        return 1


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--manual',action='store_true')
    raise SystemExit(run(manual=parser.parse_args().manual))
