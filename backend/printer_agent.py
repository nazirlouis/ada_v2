"""
PrinterAgent - Handles 3D printer discovery, slicing, and print job submission.

Supported Printer Types:
- OctoPrint (REST API)
- Moonraker/Klipper (REST API)
- PrusaLink (REST API)
"""

import asyncio
import os
import subprocess
import json
import platform
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

import aiohttp
from zeroconf import Zeroconf, ServiceBrowser, ServiceListener


class PrinterType(Enum):
    OCTOPRINT = "octoprint"
    MOONRAKER = "moonraker"
    PRUSALINK = "prusalink"
    UNKNOWN = "unknown"


@dataclass
class Printer:
    """Represents a discovered 3D printer."""
    name: str
    host: str
    port: int
    printer_type: PrinterType
    api_key: Optional[str] = None
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d["printer_type"] = self.printer_type.value
        return d


@dataclass
class PrintStatus:
    """Current status of a print job."""
    printer: str
    state: str  # "printing", "idle", "paused", "error"
    progress_percent: float
    time_remaining: Optional[str]
    time_elapsed: Optional[str]
    filename: Optional[str]
    temperatures: Optional[Dict[str, Dict[str, float]]] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


class PrinterDiscoveryListener(ServiceListener):
    """mDNS listener for printer discovery."""
    
    def __init__(self):
        self.printers: List[Printer] = []
    
    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            host = info.parsed_addresses()[0] if info.parsed_addresses() else None
            if host:
                # Determine printer type from service type
                if "_octoprint._tcp" in type_:
                    printer_type = PrinterType.OCTOPRINT
                elif "_moonraker._tcp" in type_:
                    printer_type = PrinterType.MOONRAKER
                else:
                    printer_type = PrinterType.UNKNOWN
                
                printer = Printer(
                    name=name.replace(f".{type_}", ""),
                    host=host,
                    port=info.port or 80,
                    printer_type=printer_type
                )
                self.printers.append(printer)
                print(f"[PRINTER] Discovered: {printer.name} at {printer.host}:{printer.port}")
    
    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass
    
    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass


class PrinterAgent:
    """
    Handles 3D printer discovery, profile management, slicing, and print job submission.
    """
    
    def __init__(self, profiles_dir: str = "printer_profiles"):
        self.printers: Dict[str, Printer] = {}  # host -> Printer
        self.profiles_dir = profiles_dir
        self._zeroconf: Optional[Zeroconf] = None
        
        # Detect PrusaSlicer path
        self.slicer_path = self._detect_slicer_path()
        
        # Ensure profiles directory exists
        os.makedirs(profiles_dir, exist_ok=True)
    
    def _detect_slicer_path(self) -> Optional[str]:
        """Detect PrusaSlicer installation path."""
        system = platform.system()
        
        if system == "Darwin":  # macOS
            paths = [
                "/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer",
                "/Applications/Original Prusa Drivers/PrusaSlicer.app/Contents/MacOS/PrusaSlicer"
            ]
        elif system == "Windows":
            paths = [
                r"C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer-console.exe",
                r"C:\Program Files (x86)\Prusa3D\PrusaSlicer\prusa-slicer-console.exe"
            ]
        else:  # Linux
            paths = [
                "/usr/bin/prusa-slicer",
                "/usr/local/bin/prusa-slicer",
                os.path.expanduser("~/.local/bin/prusa-slicer")
            ]
        
        for path in paths:
            if os.path.exists(path):
                print(f"[PRINTER] Found PrusaSlicer at: {path}")
                return path
        
        # Try to find via which/where
        try:
            result = subprocess.run(
                ["which", "prusa-slicer"] if system != "Windows" else ["where", "prusa-slicer-console"],
                capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                path = result.stdout.strip().split('\n')[0]
                print(f"[PRINTER] Found PrusaSlicer via PATH: {path}")
                return path
        except Exception:
            pass
        
        print("[PRINTER] Warning: PrusaSlicer not found. Slicing will fail.")
        return None
    
    async def discover_printers(self, timeout: float = 5.0) -> List[Dict]:
        """
        Discovers 3D printers on the local network via mDNS.
        Returns list of discovered printers.
        """
        print(f"[PRINTER] Starting printer discovery (timeout: {timeout}s)...")
        
        self._zeroconf = Zeroconf()
        listener = PrinterDiscoveryListener()
        
        # Browse for common 3D printer services
        services = [
            "_octoprint._tcp.local.",
            "_moonraker._tcp.local.",
            "_http._tcp.local."  # Generic HTTP - may catch PrusaLink
        ]
        
        browsers = []
        for service in services:
            browser = ServiceBrowser(self._zeroconf, service, listener)
            browsers.append(browser)
        
        # Wait for discovery
        await asyncio.sleep(timeout)
        
        # Cleanup
        self._zeroconf.close()
        
        # Store discovered printers
        for printer in listener.printers:
            self.printers[printer.host] = printer
        
        print(f"[PRINTER] Discovery complete. Found {len(listener.printers)} printers.")
        return [p.to_dict() for p in listener.printers]
    
    def add_printer_manually(self, name: str, host: str, port: int = 80, 
                             printer_type: str = "octoprint", api_key: Optional[str] = None) -> Printer:
        """Manually add a printer (useful when mDNS discovery fails)."""
        ptype = PrinterType(printer_type) if printer_type in [e.value for e in PrinterType] else PrinterType.UNKNOWN
        printer = Printer(name=name, host=host, port=port, printer_type=ptype, api_key=api_key)
        self.printers[host] = printer
        print(f"[PRINTER] Manually added: {name} at {host}:{port}")
        return printer
    
    def _resolve_printer(self, target: str) -> Optional[Printer]:
        """Resolve printer by name or host."""
        # Check by host/IP
        if target in self.printers:
            return self.printers[target]
        
        # Check by name
        for printer in self.printers.values():
            if printer.name.lower() == target.lower():
                return printer
        
        return None
    
    async def slice_stl(self, stl_path: str, output_path: Optional[str] = None,
                        profile_path: Optional[str] = None) -> Optional[str]:
        """
        Slice an STL file to G-code using PrusaSlicer CLI.
        
        Args:
            stl_path: Path to input STL file
            output_path: Optional output G-code path (default: same dir as STL)
            profile_path: Optional path to .ini profile file
        
        Returns:
            Path to generated G-code file, or None on failure
        """
        if not self.slicer_path:
            print("[PRINTER] Error: PrusaSlicer not found")
            return None
        
        if not os.path.exists(stl_path):
            print(f"[PRINTER] Error: STL file not found: {stl_path}")
            return None
        
        # Default output path
        if not output_path:
            output_path = stl_path.rsplit('.', 1)[0] + ".gcode"
        
        # Build command
        cmd = [
            self.slicer_path,
            "--export-gcode",
            "--output", output_path,
            stl_path
        ]
        
        # Add profile if specified
        if profile_path and os.path.exists(profile_path):
            cmd.insert(1, "--load")
            cmd.insert(2, profile_path)
        
        print(f"[PRINTER] Slicing: {stl_path}")
        print(f"[PRINTER] Command: {' '.join(cmd)}")
        
        try:
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True, timeout=300
            )
            
            if result.returncode == 0:
                print(f"[PRINTER] Slicing complete: {output_path}")
                return output_path
            else:
                print(f"[PRINTER] Slicing failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print("[PRINTER] Slicing timeout (5 min exceeded)")
            return None
        except Exception as e:
            print(f"[PRINTER] Slicing error: {e}")
            return None
    
    async def upload_gcode(self, target: str, gcode_path: str, 
                           start_print: bool = False) -> bool:
        """
        Upload G-code to printer and optionally start print.
        
        Args:
            target: Printer name or host
            gcode_path: Path to G-code file
            start_print: Whether to start printing immediately
        
        Returns:
            True on success, False on failure
        """
        printer = self._resolve_printer(target)
        if not printer:
            print(f"[PRINTER] Error: Printer not found: {target}")
            return False
        
        if not os.path.exists(gcode_path):
            print(f"[PRINTER] Error: G-code file not found: {gcode_path}")
            return False
        
        if printer.printer_type == PrinterType.OCTOPRINT:
            return await self._upload_octoprint(printer, gcode_path, start_print)
        elif printer.printer_type == PrinterType.MOONRAKER:
            return await self._upload_moonraker(printer, gcode_path, start_print)
        else:
            print(f"[PRINTER] Error: Unsupported printer type: {printer.printer_type}")
            return False
    
    async def _upload_octoprint(self, printer: Printer, gcode_path: str, 
                                 start_print: bool) -> bool:
        """Upload to OctoPrint."""
        url = f"http://{printer.host}:{printer.port}/api/files/local"
        headers = {}
        if printer.api_key:
            headers["X-Api-Key"] = printer.api_key
        
        filename = os.path.basename(gcode_path)
        
        try:
            async with aiohttp.ClientSession() as session:
                with open(gcode_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=filename)
                    if start_print:
                        data.add_field('print', 'true')
                    
                    async with session.post(url, headers=headers, data=data) as resp:
                        if resp.status in (200, 201):
                            print(f"[PRINTER] Uploaded to OctoPrint: {filename}")
                            return True
                        else:
                            error = await resp.text()
                            print(f"[PRINTER] OctoPrint upload failed ({resp.status}): {error}")
                            return False
        except Exception as e:
            print(f"[PRINTER] OctoPrint upload error: {e}")
            return False
    
    async def _upload_moonraker(self, printer: Printer, gcode_path: str,
                                 start_print: bool) -> bool:
        """Upload to Moonraker."""
        url = f"http://{printer.host}:{printer.port}/server/files/upload"
        filename = os.path.basename(gcode_path)
        
        try:
            async with aiohttp.ClientSession() as session:
                with open(gcode_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=filename)
                    if start_print:
                        data.add_field('print', 'true')
                    
                    async with session.post(url, data=data) as resp:
                        if resp.status in (200, 201):
                            print(f"[PRINTER] Uploaded to Moonraker: {filename}")
                            return True
                        else:
                            error = await resp.text()
                            print(f"[PRINTER] Moonraker upload failed ({resp.status}): {error}")
                            return False
        except Exception as e:
            print(f"[PRINTER] Moonraker upload error: {e}")
            return False
    
    async def get_print_status(self, target: str) -> Optional[PrintStatus]:
        """
        Get current print status from printer.
        
        Returns:
            PrintStatus object, or None on error
        """
        printer = self._resolve_printer(target)
        if not printer:
            print(f"[PRINTER] Error: Printer not found: {target}")
            return None
        
        if printer.printer_type == PrinterType.OCTOPRINT:
            return await self._status_octoprint(printer)
        elif printer.printer_type == PrinterType.MOONRAKER:
            return await self._status_moonraker(printer)
        else:
            print(f"[PRINTER] Error: Unsupported printer type: {printer.printer_type}")
            return None
    
    def _format_time(self, seconds: Optional[float]) -> Optional[str]:
        """Format seconds to human-readable time."""
        if seconds is None or seconds < 0:
            return None
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    
    async def _status_octoprint(self, printer: Printer) -> Optional[PrintStatus]:
        """Get status from OctoPrint."""
        url = f"http://{printer.host}:{printer.port}/api/job"
        headers = {}
        if printer.api_key:
            headers["X-Api-Key"] = printer.api_key
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        progress = data.get("progress", {})
                        job = data.get("job", {})
                        
                        return PrintStatus(
                            printer=printer.name,
                            state=data.get("state", "unknown").lower(),
                            progress_percent=progress.get("completion") or 0,
                            time_remaining=self._format_time(progress.get("printTimeLeft")),
                            time_elapsed=self._format_time(progress.get("printTime")),
                            filename=job.get("file", {}).get("name")
                        )
                    else:
                        print(f"[PRINTER] OctoPrint status failed ({resp.status})")
                        return None
        except Exception as e:
            print(f"[PRINTER] OctoPrint status error: {e}")
            return None
    
    async def _status_moonraker(self, printer: Printer) -> Optional[PrintStatus]:
        """Get status from Moonraker."""
        url = f"http://{printer.host}:{printer.port}/printer/objects/query?print_stats&display_status&heater_bed&extruder"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        status = data.get("result", {}).get("status", {})
                        stats = status.get("print_stats", {})
                        display = status.get("display_status", {})
                        extruder = status.get("extruder", {})
                        bed = status.get("heater_bed", {})
                        
                        return PrintStatus(
                            printer=printer.name,
                            state=stats.get("state", "unknown"),
                            progress_percent=(display.get("progress") or 0) * 100,
                            time_remaining=None,  # Moonraker doesn't provide this directly
                            time_elapsed=self._format_time(stats.get("print_duration")),
                            filename=stats.get("filename"),
                            temperatures={
                                "hotend": {
                                    "current": extruder.get("temperature", 0),
                                    "target": extruder.get("target", 0)
                                },
                                "bed": {
                                    "current": bed.get("temperature", 0),
                                    "target": bed.get("target", 0)
                                }
                            }
                        )
                    else:
                        print(f"[PRINTER] Moonraker status failed ({resp.status})")
                        return None
        except Exception as e:
            print(f"[PRINTER] Moonraker status error: {e}")
            return None
    
    async def print_stl(self, stl_path: str, target: str, 
                        profile: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete workflow: Slice STL and send to printer.
        
        Args:
            stl_path: Path to STL file (or 'current' for most recent)
            target: Printer name or host
            profile: Optional slicer profile name
        
        Returns:
            Dict with success status and message
        """
        # Resolve 'current' to actual path if needed
        if stl_path.lower() == "current":
            # Look for output.stl in common locations
            possible_paths = [
                "output.stl",
                "backend/output.stl",
                "../output.stl"
            ]
            stl_path = None
            for p in possible_paths:
                if os.path.exists(p):
                    stl_path = p
                    break
            if not stl_path:
                return {"success": False, "message": "No current STL file found"}
        
        # Resolve profile path
        profile_path = None
        if profile:
            profile_path = os.path.join(self.profiles_dir, f"{profile}.ini")
            if not os.path.exists(profile_path):
                print(f"[PRINTER] Warning: Profile not found: {profile_path}")
                profile_path = None
        
        # Step 1: Slice
        gcode_path = await self.slice_stl(stl_path, profile_path=profile_path)
        if not gcode_path:
            return {"success": False, "message": "Slicing failed"}
        
        # Step 2: Upload and start print
        success = await self.upload_gcode(target, gcode_path, start_print=True)
        if success:
            return {
                "success": True, 
                "message": f"Print started on {target}",
                "gcode_file": gcode_path
            }
        else:
            return {"success": False, "message": f"Failed to upload to {target}"}


# Standalone test
if __name__ == "__main__":
    async def main():
        agent = PrinterAgent()
        
        print("\n=== Testing Printer Discovery ===")
        printers = await agent.discover_printers(timeout=3)
        print(f"Found: {printers}")
        
        if printers:
            printer = printers[0]
            print(f"\n=== Testing Status for {printer['name']} ===")
            status = await agent.get_print_status(printer['host'])
            if status:
                print(f"Status: {status.to_dict()}")
    
    asyncio.run(main())
