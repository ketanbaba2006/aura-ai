"""
AURA AI System Information Tool
Retrieves comprehensive system information.
"""

import platform
import sys
from datetime import datetime
from typing import Any
import psutil

from app.database.schemas import ToolResult
from app.tools.base import BaseTool


class SystemInfoTool(BaseTool):
    """Retrieves comprehensive system information."""

    @property
    def name(self) -> str:
        return "system_info"

    @property
    def description(self) -> str:
        return (
            "Get comprehensive system information including OS, CPU, memory, disk, "
            "network, GPU, battery, and running processes."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["all", "os", "cpu", "memory", "disk", "network", "gpu", "battery", "processes", "python"],
                    "description": "Category of info to retrieve (default: all)",
                },
                "limit_processes": {
                    "type": "integer",
                    "description": "Maximum number of processes to list (for 'processes' category, default: 20)",
                },
                "sort_processes": {
                    "type": "string",
                    "enum": ["cpu", "memory", "name"],
                    "description": "Sort processes by (default: cpu)",
                },
            },
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        category = kwargs.get("category", "all")
        limit_processes = kwargs.get("limit_processes", 20)
        sort_processes = kwargs.get("sort_processes", "cpu")

        try:
            sections = []

            if category in ["all", "os"]:
                sections.append(self._get_os_info())

            if category in ["all", "cpu"]:
                sections.append(self._get_cpu_info())

            if category in ["all", "memory"]:
                sections.append(self._get_memory_info())

            if category in ["all", "disk"]:
                sections.append(self._get_disk_info())

            if category in ["all", "network"]:
                sections.append(self._get_network_info())

            if category in ["all", "gpu"]:
                sections.append(self._get_gpu_info())

            if category in ["all", "battery"]:
                sections.append(self._get_battery_info())

            if category in ["all", "processes"]:
                sections.append(self._get_processes_info(limit_processes, sort_processes))

            if category in ["all", "python"]:
                sections.append(self._get_python_info())

            output = "\n\n".join(sections)
            return ToolResult(success=True, output=output)

        except Exception as e:
            return ToolResult(success=False, error=f"Error getting system info: {str(e)}")

    @staticmethod
    def _fmt_bytes(n: int) -> str:
        """Format bytes to human-readable string."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if abs(n) < 1024:
                return f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} PB"

    def _get_os_info(self) -> str:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)

        return (
            f"🖥️  Operating System\n"
            f"  System: {platform.system()} {platform.release()}\n"
            f"  Version: {platform.version()}\n"
            f"  Machine: {platform.machine()}\n"
            f"  Hostname: {platform.node()}\n"
            f"  Architecture: {platform.architecture()[0]}\n"
            f"  Uptime: {hours}h {minutes}m"
        )

    def _get_cpu_info(self) -> str:
        cpu_freq = psutil.cpu_freq()
        freq_str = f"{cpu_freq.current:.0f} MHz" if cpu_freq else "N/A"
        freq_max_str = f" (max: {cpu_freq.max:.0f} MHz)" if cpu_freq and cpu_freq.max else ""

        # Get per-core usage
        per_core = psutil.cpu_percent(percpu=True, interval=0.1)
        core_info = "\n".join([f"    Core {i+1}: {usage}%" for i, usage in enumerate(per_core)])

        return (
            f"⚡ CPU\n"
            f"  Cores (physical): {psutil.cpu_count(logical=False)}\n"
            f"  Cores (logical): {psutil.cpu_count(logical=True)}\n"
            f"  Frequency: {freq_str}{freq_max_str}\n"
            f"  Usage: {psutil.cpu_percent(interval=0.1)}%\n"
            f"  Per-core usage:\n{core_info}"
        )

    def _get_memory_info(self) -> str:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return (
            f"🧠 Memory\n"
            f"  Total: {self._fmt_bytes(mem.total)}\n"
            f"  Available: {self._fmt_bytes(mem.available)}\n"
            f"  Used: {self._fmt_bytes(mem.used)} ({mem.percent}%)\n"
            f"  Buffers: {self._fmt_bytes(mem.buffers) if hasattr(mem, 'buffers') else 'N/A'}\n"
            f"  Cached: {self._fmt_bytes(mem.cached) if hasattr(mem, 'cached') else 'N/A'}\n"
            f"  Swap Total: {self._fmt_bytes(swap.total)}\n"
            f"  Swap Used: {self._fmt_bytes(swap.used)} ({swap.percent}%)\n"
            f"  Swap Free: {self._fmt_bytes(swap.free)}"
        )

    def _get_disk_info(self) -> str:
        disk_lines = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disk_lines.append(
                    f"  Mount: {part.mountpoint}\n"
                    f"    Device: {part.device}\n"
                    f"    Fstype: {part.fstype}\n"
                    f"    Total: {self._fmt_bytes(usage.total)}\n"
                    f"    Used: {self._fmt_bytes(usage.used)} ({usage.percent}%)\n"
                    f"    Free: {self._fmt_bytes(usage.free)}"
                )
            except (PermissionError, FileNotFoundError):
                continue

        disk_io = psutil.disk_io_counters()
        io_info = ""
        if disk_io:
            io_info = (
                f"\n  I/O Stats:\n"
                f"    Read: {self._fmt_bytes(disk_io.read_bytes)}\n"
                f"    Write: {self._fmt_bytes(disk_io.write_bytes)}\n"
                f"    Read count: {disk_io.read_count}\n"
                f"    Write count: {disk_io.write_count}"
            )

        return "💾 Disk\n" + "\n\n".join(disk_lines) + io_info

    def _get_network_info(self) -> str:
        net_lines = []

        # Network interfaces
        if_addrs = psutil.net_if_addrs()
        net_lines.append("  Interfaces:")
        for iface, addrs in if_addrs.items():
            addrs_info = []
            for addr in addrs:
                if addr.family.name == "AF_INET":
                    addrs_info.append(f"IPv4: {addr.address}")
                elif addr.family.name == "AF_INET6":
                    addrs_info.append(f"IPv6: {addr.address}")
                elif addr.family.name == "AF_PACKET":
                    addrs_info.append(f"MAC: {addr.address}")
            if addrs_info:
                net_lines.append(f"    {iface}: {', '.join(addrs_info)}")

        # Network statistics
        net_io = psutil.net_io_counters()
        if net_io:
            net_lines.append(
                f"\n  I/O Stats:\n"
                f"    Sent: {self._fmt_bytes(net_io.bytes_sent)}\n"
                f"    Recv: {self._fmt_bytes(net_io.bytes_recv)}\n"
                f"    Sent packets: {net_io.packets_sent}\n"
                f"    Recv packets: {net_io.packets_recv}"
            )

        return "🌐 Network\n" + "\n".join(net_lines)

    def _get_gpu_info(self) -> str:
        gpu_lines = []

        # Try to get NVIDIA GPU info using nvidia-smi if available
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for i, line in enumerate(result.stdout.strip().split("\n")):
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 6:
                        gpu_lines.append(
                            f"  GPU {i+1}: {parts[0]}\n"
                            f"    Memory Total: {self._fmt_bytes(int(parts[1]) * 1024 * 1024)}\n"
                            f"    Memory Used: {self._fmt_bytes(int(parts[2]) * 1024 * 1024)}\n"
                            f"    Memory Free: {self._fmt_bytes(int(parts[3]) * 1024 * 1024)}\n"
                            f"    Temperature: {parts[4]}°C\n"
                            f"    Utilization: {parts[5]}%"
                        )
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass

        # If no NVIDIA GPUs found, try to get general GPU info
        if not gpu_lines:
            # On macOS, try to get GPU info from system profiler
            if platform.system() == "Darwin":
                try:
                    import subprocess
                    result = subprocess.run(
                        ["system_profiler", "SPDisplaysDataType"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        gpu_lines.append(f"  macOS GPU Info:\n    {result.stdout[:500]}...")
                except Exception:
                    pass

        if not gpu_lines:
            gpu_lines.append("  No GPU information available")

        return "🎮 GPU\n" + "\n\n".join(gpu_lines)

    def _get_battery_info(self) -> str:
        battery = psutil.sensors_battery()
        if battery:
            plug_str = "Charging" if battery.power_plugged else "Discharging"
            time_left = f"{battery.secsleft // 3600}h {(battery.secsleft % 3600) // 60}m" if battery.secsleft != psutil.POWER_TIME_UNLIMITED else "N/A"
            return (
                f"🔋 Battery\n"
                f"  Charge: {battery.percent}%\n"
                f"  Status: {plug_str}\n"
                f"  Time left: {time_left}"
            )
        else:
            return "🔋 Battery\n  No battery information available"

    def _get_processes_info(self, limit: int, sort_by: str) -> str:
        processes = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                proc_info = proc.info
                proc_info["memory_rss"] = proc_info["memory_info"].rss
                processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Sort processes
        if sort_by == "cpu":
            processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
        elif sort_by == "memory":
            processes.sort(key=lambda x: x["memory_rss"], reverse=True)
        elif sort_by == "name":
            processes.sort(key=lambda x: x["name"].lower())

        # Limit processes
        processes = processes[:limit]

        # Format output
        lines = [f"⚙️  Processes (top {limit} sorted by {sort_by}):"]
        lines.append(f"  {'PID':<8} {'Name':<20} {'CPU%':<8} {'Memory'}")
        lines.append("  " + "-" * 50)
        for proc in processes:
            lines.append(
                f"  {proc['pid']:<8} {proc['name'][:20]:<20} {proc['cpu_percent']:<8.1f} {self._fmt_bytes(proc['memory_rss'])}"
            )

        return "\n".join(lines)

    def _get_python_info(self) -> str:
        return (
            f"🐍 Python\n"
            f"  Version: {sys.version}\n"
            f"  Executable: {sys.executable}\n"
            f"  Platform: {sys.platform}\n"
            f"  Implementation: {platform.python_implementation()}"
        )
