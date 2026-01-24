"""
Advanced Network Monitor Visualization Panel
Displays real-time network traffic analysis and security events
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango
from datetime import datetime
from typing import Dict, List, Optional

from logger import get_logger
from advanced_network_monitor import (
    get_advanced_network_monitor,
    NetworkFlow,
    NetworkSecurityEvent,
    ProtocolType
)
from theme import Colors, Format


class NetworkMonitorPanel(Gtk.Box):
    """
    Advanced network monitoring visualization panel
    Shows active flows, bandwidth by protocol, and security events
    """
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        self.logger = get_logger()
        self.monitor = get_advanced_network_monitor()
        
        # Build UI
        self._build_ui()
        
        # Start update timer (update every 2 seconds)
        GLib.timeout_add_seconds(2, self._update_display)
    
    def _build_ui(self):
        """Build the monitoring panel UI"""
        self.set_border_width(10)
        
        # Header
        header = Gtk.Label()
        header.set_markup('<span size="large" weight="bold">NETWORK MONITOR</span>')
        header.set_halign(Gtk.Align.START)
        self.pack_start(header, False, False, 0)
        
        # Create notebook for tabs
        notebook = Gtk.Notebook()
        notebook.set_tab_pos(Gtk.PositionType.TOP)
        
        # Tab 1: Active Flows
        flows_tab = self._create_flows_tab()
        flows_label = Gtk.Label(label="Active Flows")
        notebook.append_page(flows_tab, flows_label)
        
        # Tab 2: Bandwidth by Protocol
        bandwidth_tab = self._create_bandwidth_tab()
        bandwidth_label = Gtk.Label(label="Bandwidth")
        notebook.append_page(bandwidth_tab, bandwidth_label)
        
        # Tab 3: Security Events
        security_tab = self._create_security_tab()
        security_label = Gtk.Label(label="Security")
        notebook.append_page(security_tab, security_label)
        
        self.pack_start(notebook, True, True, 0)
    
    def _create_flows_tab(self) -> Gtk.Widget:
        """Create active flows display tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        # Info label
        info = Gtk.Label()
        info.set_markup(
            f'<span foreground="{Colors.DIM_TEXT}">Real-time network connections</span>'
        )
        info.set_halign(Gtk.Align.START)
        box.pack_start(info, False, False, 0)
        
        # Create scrolled window for flows list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(200)
        
        # TreeView for flows
        self.flows_store = Gtk.ListStore(str, str, str, str, str, str)  # protocol, src, dst, bytes, packets, duration
        self.flows_tree = Gtk.TreeView(model=self.flows_store)
        
        # Add columns
        columns = [
            ("Protocol", 0, 80),
            ("Source", 1, 150),
            ("Destination", 2, 150),
            ("Bytes", 3, 100),
            ("Packets", 4, 80),
            ("Duration", 5, 100)
        ]
        
        for title, col_id, width in columns:
            renderer = Gtk.CellRendererText()
            renderer.set_property("font", "monospace 9")
            column = Gtk.TreeViewColumn(title, renderer, text=col_id)
            column.set_fixed_width(width)
            column.set_resizable(True)
            self.flows_tree.append_column(column)
        
        scroll.add(self.flows_tree)
        box.pack_start(scroll, True, True, 0)
        
        # Stats label
        self.flows_stats_label = Gtk.Label()
        self.flows_stats_label.set_halign(Gtk.Align.START)
        box.pack_start(self.flows_stats_label, False, False, 0)
        
        return box
    
    def _create_bandwidth_tab(self) -> Gtk.Widget:
        """Create bandwidth by protocol tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        # Info label
        info = Gtk.Label()
        info.set_markup(
            f'<span foreground="{Colors.DIM_TEXT}">Bandwidth usage by protocol</span>'
        )
        info.set_halign(Gtk.Align.START)
        box.pack_start(info, False, False, 0)
        
        # Create scrolled window
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(200)
        
        # TreeView for bandwidth
        self.bandwidth_store = Gtk.ListStore(str, str, str, str)  # protocol, upload, download, total
        self.bandwidth_tree = Gtk.TreeView(model=self.bandwidth_store)
        
        # Add columns
        columns = [
            ("Protocol", 0, 120),
            ("Upload", 1, 120),
            ("Download", 2, 120),
            ("Total", 3, 120)
        ]
        
        for title, col_id, width in columns:
            renderer = Gtk.CellRendererText()
            renderer.set_property("font", "monospace 9")
            column = Gtk.TreeViewColumn(title, renderer, text=col_id)
            column.set_fixed_width(width)
            column.set_resizable(True)
            self.bandwidth_tree.append_column(column)
        
        scroll.add(self.bandwidth_tree)
        box.pack_start(scroll, True, True, 0)
        
        # Summary
        self.bandwidth_summary_label = Gtk.Label()
        self.bandwidth_summary_label.set_halign(Gtk.Align.START)
        box.pack_start(self.bandwidth_summary_label, False, False, 0)
        
        return box
    
    def _create_security_tab(self) -> Gtk.Widget:
        """Create security events tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        # Info label
        info = Gtk.Label()
        info.set_markup(
            f'<span foreground="{Colors.DIM_TEXT}">Security events and anomalies</span>'
        )
        info.set_halign(Gtk.Align.START)
        box.pack_start(info, False, False, 0)
        
        # Create scrolled window
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(200)
        
        # TreeView for security events
        self.security_store = Gtk.ListStore(str, str, str, str, str)  # time, severity, type, source, description
        self.security_tree = Gtk.TreeView(model=self.security_store)
        
        # Add columns
        columns = [
            ("Time", 0, 100),
            ("Severity", 1, 80),
            ("Type", 2, 120),
            ("Source", 3, 120),
            ("Description", 4, 250)
        ]
        
        for title, col_id, width in columns:
            renderer = Gtk.CellRendererText()
            renderer.set_property("font", "monospace 9")
            column = Gtk.TreeViewColumn(title, renderer, text=col_id)
            column.set_fixed_width(width)
            column.set_resizable(True)
            self.security_tree.append_column(column)
        
        scroll.add(self.security_tree)
        box.pack_start(scroll, True, True, 0)
        
        # Clear button
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        clear_btn = Gtk.Button(label="Clear Events")
        clear_btn.connect("clicked", self._on_clear_security_events)
        button_box.pack_start(clear_btn, False, False, 0)
        box.pack_start(button_box, False, False, 0)
        
        return box
    
    def _update_display(self) -> bool:
        """Update display with latest network data"""
        try:
            self._update_flows()
            self._update_bandwidth()
            self._update_security()
        except Exception as e:
            self.logger.error(f"Failed to update network monitor display: {e}")
        
        return True  # Continue timer
    
    def _update_flows(self):
        """Update active flows display"""
        self.flows_store.clear()
        
        try:
            analysis = self.monitor.get_traffic_analysis()
            
            if analysis.get("status") == "no_data":
                self.flows_stats_label.set_markup(
                    f'<span foreground="{Colors.DIM_TEXT}">No active flows</span>'
                )
                return
            
            # Display protocol breakdown
            protocol_breakdown = analysis.get("protocol_breakdown", {})
            for protocol, stats in sorted(protocol_breakdown.items(), key=lambda x: x[1]["bytes"], reverse=True):
                protocol_name = protocol.upper()
                connections = str(stats["connections"])
                bytes_total = Format.bytes(stats["bytes"])
                
                self.flows_store.append([protocol_name, "-", "-", bytes_total, connections, "-"])
            
            # Update stats
            total_flows = analysis.get("total_flows", 0)
            total_bytes = sum(stats["bytes"] for stats in protocol_breakdown.values())
            security_events = analysis.get("security_events", 0)
            
            self.flows_stats_label.set_markup(
                f'<span foreground="{Colors.DIM_TEXT}">'
                f'Active: {total_flows} flows | Total: {Format.bytes(total_bytes)} | '
                f'Security Events: {security_events}'
                f'</span>'
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update flows: {e}")
    
    def _update_bandwidth(self):
        """Update bandwidth by protocol display"""
        self.bandwidth_store.clear()
        
        try:
            report = self.monitor.get_bandwidth_report()
            
            total_up = report.get("total_upload_bytes", 0)
            total_down = report.get("total_download_bytes", 0)
            
            # Group by protocol from application usage
            app_usage = report.get("application_usage", [])
            for usage in app_usage[:15]:  # Top 15 applications
                app_name = usage.get("application", "Unknown")
                upload = Format.bytes(usage.get("bytes_up", 0))
                download = Format.bytes(usage.get("bytes_down", 0))
                total = Format.bytes(usage.get("bytes_up", 0) + usage.get("bytes_down", 0))
                
                self.bandwidth_store.append([app_name, upload, download, total])
            
            # Update summary
            self.bandwidth_summary_label.set_markup(
                f'<span foreground="{Colors.DIM_TEXT}">'
                f'Total Upload: {Format.bytes(total_up)} | '
                f'Download: {Format.bytes(total_down)}'
                f'</span>'
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update bandwidth: {e}")
    
    def _update_security(self):
        """Update security events display"""
        try:
            report = self.monitor.get_security_report()
            
            if report.get("status") == "no_events":
                return
            
            # Get latest events from report
            latest_events = report.get("latest_events", [])
            
            # Only add new events not already in store
            current_count = len(self.security_store)
            if len(latest_events) > current_count or current_count == 0:
                self.security_store.clear()
                
                for event in latest_events:
                    timestamp = event.get("timestamp", 0)
                    time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
                    severity = event.get("severity", "unknown").upper()
                    event_type = event.get("event_type", "unknown")
                    source_ip = event.get("source_ip", "unknown")
                    description = event.get("description", "No description")
                    
                    self.security_store.append([
                        time_str,
                        severity,
                        event_type,
                        source_ip,
                        description
                    ])
            
        except Exception as e:
            self.logger.error(f"Failed to update security events: {e}")
    
    def _on_clear_security_events(self, button):
        """Clear security events list"""
        self.security_store.clear()
        # Note: The monitor doesn't expose a clear method, so we just clear the display
        self.logger.info("Cleared security events display")
