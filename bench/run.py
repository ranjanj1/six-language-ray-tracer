#!/usr/bin/env python3
"""Sequential validated benchmark. See bench/README.md for commands and warm protocol."""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import time
import threading
from compare import compare, ROOT, TOLERANCE

# No shell interpolation; flags intentionally avoid native tuning and fast math.
PROFILES = {
 'python': ([], ['python3', 'main.py'], [['python3', '--version']]),
 'javascript': ([], ['node', 'main.js'], [['node', '--version']]),
 'go': (['go', 'build', '-o', 'program', 'main.go'], ['./program'], [['go', 'version']]),
 'java': (['javac', '-d', '.', 'Main.java'], ['java', '-cp', '.', 'Main'], [['javac', '-version'], ['java', '-version']]),
 'cpp': (['c++', '-std=c++17', '-O3', '-ffp-contract=off', 'main.cpp', '-o', 'program'], ['./program'], [['c++', '--version']]),
 'rust': (['rustc', '-O', '-C', 'codegen-units=1', 'main.rs', '-o', 'program'], ['./program'], [['rustc', '--version']]),
}

def invoke(command, cwd, timeout):
    # Child logs go to a file, not an unbounded in-memory pipe. No terminal rendering.
    with (cwd/'bench-process.log').open('wb') as log:
        timed_out = threading.Event()
        def expire():
            timed_out.set()
            process.kill()
        start = time.perf_counter_ns()
        process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT)
        watchdog = threading.Timer(timeout, expire)
        watchdog.daemon = True
        watchdog.start()
        try:
            code = process.wait()  # Blocking wait avoids timeout polling quantization.
            elapsed = (time.perf_counter_ns()-start)/1e9
        finally:
            watchdog.cancel()
            watchdog.join()
        if timed_out.is_set():
            raise subprocess.TimeoutExpired(command, timeout)
        if code:
            raise subprocess.CalledProcessError(code, command)
        return elapsed

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def summary(values):
    return dict(median_seconds=statistics.median(values), min_seconds=min(values),
                max_seconds=max(values), spread_seconds=max(values)-min(values))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('languages', nargs='+', help='python=folder javascript=folder go=folder java=folder cpp=folder rust=folder')
    p.add_argument('-n', '--runs', type=int, default=5)
    p.add_argument('--mode', choices=['cold', 'warm'], default='cold')
    p.add_argument('--timeout', type=float, default=600)
    args = p.parse_args()
    if args.runs < 5 or args.timeout <= 0 or not math.isfinite(args.timeout):
        p.error('at least 5 runs and a finite positive timeout are required')
    jobs = []
    names = set()
    for item in args.languages:
        name, sep, location = item.partition('=')
        if not sep or name not in PROFILES or name in names:
            p.error('use unique language=folder entries; see --help')
        names.add(name)
        folder = Path(location).resolve()
        if not folder.is_dir() or not folder.is_relative_to(ROOT):
            p.error('language folders must exist inside this project')
        build, run, versions = PROFILES[name]
        manifest = folder/'bench.json'
        config = json.loads(manifest.read_text()) if manifest.exists() else {}
        if set(config) - {'warm_command', 'warmup_iterations'}:
            p.error('bench.json supports only warm_command and warmup_iterations; cold commands are fixed')
        if args.mode == 'warm':
            cmd = config.get('warm_command')
            count = config.get('warmup_iterations', 3)
            if (name not in ('java', 'javascript') or not isinstance(cmd, list)
                or not cmd or not all(isinstance(s, str) and s for s in cmd)
                or type(count) is not int or count < 1):
                p.error('warm mode requires Java/JavaScript warm_command and positive warmup_iterations')
        jobs.append(dict(name=name, folder=folder, build=build, command=run,
                         version_commands=versions, config=config))
    # Lock covers builds, timing, comparisons, and writes. Stale locks require manual removal.
    lock = ROOT/'bench/.run.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise RuntimeError('another bench run is active, or stale bench/.run.lock exists')
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        reference_hash = digest(ROOT/'reference.ppm')
        for job in jobs:
            versions = []
            for cmd in job['version_commands']:
                completed = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
                versions.append(dict(command=cmd, executable=shutil.which(cmd[0]),
                                     output=(completed.stdout+completed.stderr).strip()))
            if job['build']:
                invoke(job['build'], job['folder'], args.timeout)
            job['result'] = dict(language=job['name'], mode=args.mode,
                timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                platform=platform.platform(), machine=platform.machine(),
                build_command=job['build'], run_command=job['command'], versions=versions,
                reference_sha256=reference_hash, tolerance=TOLERANCE,
                source_sha256={f.name:digest(f) for f in job['folder'].iterdir()
                               if f.suffix in ('.py','.js','.go','.java','.cpp','.rs')},
                warm='not measured' if args.mode == 'cold' else job['config'], runs=[])
        order = []
        for round_index in range(args.runs):
            round_jobs = jobs if round_index % 2 == 0 else list(reversed(jobs))
            for job in round_jobs:
                folder = job['folder']
                order.append(job['name'])
                if args.mode == 'cold':
                    output = folder/'out.ppm'
                    output.unlink(missing_ok=True)
                    elapsed = invoke(job['command'], folder, args.timeout)
                    check = compare(output)
                    if not check['match']:
                        raise RuntimeError(f"{job['name']}: image mismatch: {check}")
                    sample = dict(round=round_index+1, wall_seconds=elapsed,
                                  comparison=check, output_sha256=digest(output))
                else:
                    # One fresh runtime per round, with warmup and a measured render inside it.
                    report = folder/'warm-result.json'
                    report.unlink(missing_ok=True)
                    output = folder/'out.ppm'
                    output.unlink(missing_ok=True)
                    cmd = [s.replace('{warmups}', str(job['config'].get('warmup_iterations',3)))
                           for s in job['config']['warm_command']]
                    process_seconds = invoke(cmd, folder, args.timeout)
                    data = json.loads(report.read_text())
                    elapsed = data.get('render_wall_seconds')
                    if (data.get('warmup_iterations') != job['config'].get('warmup_iterations',3)
                        or isinstance(elapsed, bool) or not isinstance(elapsed, (int,float))
                        or not math.isfinite(elapsed) or elapsed <= 0 or elapsed > process_seconds):
                        raise RuntimeError('invalid warm-result.json timing report')
                    check = compare(output)
                    if not check['match']:
                        raise RuntimeError(f"{job['name']}: warm image mismatch: {check}")
                    sample = dict(round=round_index+1, wall_seconds=elapsed,
                                  fresh_process_wall_seconds=process_seconds,
                                  comparison=check, output_sha256=digest(output))
                job['result']['runs'].append(sample)
        if digest(ROOT/'reference.ppm') != reference_hash:
            raise RuntimeError('reference changed during benchmark')
        # No timing result is written unless every requested run passed validation.
        for job in jobs:
            result = job['result']
            result['schedule'] = order
            result['summary'] = summary([s['wall_seconds'] for s in result['runs']])
            dest = ROOT/'results'/f"{job['name']}.json"
            previous = json.loads(dest.read_text()) if dest.exists() else {}
            combined = {k: v for k,v in previous.items() if k in ('cold','warm')}
            combined[args.mode] = result
            temp = dest.with_suffix('.json.tmp')
            temp.write_text(json.dumps(combined, indent=2)+'\n')
            temp.replace(dest)
            print(f"{job['name']}: {args.runs} validated {args.mode} runs saved to {dest.relative_to(ROOT)}")
    finally:
        lock.unlink(missing_ok=True)

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'bench refused to record: {error}', file=sys.stderr)
        raise SystemExit(1)
