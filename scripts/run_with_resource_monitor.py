import argparse
import ctypes
import json
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None


def rss_bytes_windows(pid: int) -> int | None:
    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_VM_READ = 0x0010
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        return None
    try:
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(ProcessMemoryCounters)
        ok = psapi.GetProcessMemoryInfo(
            handle,
            ctypes.byref(counters),
            counters.cb,
        )
        if not ok:
            return None
        return int(counters.WorkingSetSize)
    finally:
        kernel32.CloseHandle(handle)


def rss_bytes_procfs(pid: int) -> int | None:
    status_path = Path(f"/proc/{pid}/status")
    if not status_path.exists():
        return None
    for line in status_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("VmRSS:"):
            parts = line.split()
            return int(parts[1]) * 1024
    return None


def rss_bytes(pid: int) -> int | None:
    if psutil is not None:
        try:
            process = psutil.Process(pid)
            processes = [process] + process.children(recursive=True)
            return sum(child.memory_info().rss for child in processes if child.is_running())
        except psutil.Error:
            return None
    if os.name == "nt":
        return rss_bytes_windows(pid)
    return rss_bytes_procfs(pid)


def parse_args():
    parser = argparse.ArgumentParser(description="Run a command and record peak RSS.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.command:
        raise SystemExit("Missing command after --")
    command = args.command
    if command[0] == "--":
        command = command[1:]
    started_at = time.time()
    process = subprocess.Popen(command)
    samples = []
    peak_rss = 0
    while True:
        current = rss_bytes(process.pid)
        elapsed = time.time() - started_at
        if current is not None:
            peak_rss = max(peak_rss, current)
            samples.append({"elapsed_seconds": round(elapsed, 3), "rss_bytes": current})
        exit_code = process.poll()
        if exit_code is not None:
            break
        time.sleep(args.interval)
    elapsed = time.time() - started_at
    result = {
        "command": command,
        "exit_code": process.returncode,
        "elapsed_seconds": round(elapsed, 3),
        "peak_rss_bytes": peak_rss,
        "peak_rss_mib": round(peak_rss / (1024 * 1024), 3),
        "monitor_backend": "psutil" if psutil is not None else ("windows_ctypes" if os.name == "nt" else "procfs"),
        "sample_count": len(samples),
        "samples_tail": samples[-20:],
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if process.returncode:
        raise SystemExit(process.returncode)


if __name__ == "__main__":
    main()
