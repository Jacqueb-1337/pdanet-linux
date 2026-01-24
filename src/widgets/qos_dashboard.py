"""
Intelligent QoS (Quality of Service) Dashboard
Displays active QoS rules and traffic shaping metrics
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
from typing import Dict, List

from logger import get_logger
from intelligent_bandwidth_manager import (
    get_intelligent_bandwidth_manager,
    QoSPriority,
    TrafficClass
)
from theme import Colors, Format


class QoSDashboard(Gtk.Box):
    """
    Quality of Service dashboard showing active rules and metrics
    """
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        self.logger = get_logger()
        self.qos_manager = get_intelligent_bandwidth_manager()
        
        # Build UI
        self._build_ui()
        
        # Start update timer
        GLib.timeout_add_seconds(3, self._update_display)
    
    def _build_ui(self):
        """Build QoS dashboard UI"""
        self.set_border_width(10)
        
        # Header
        header = Gtk.Label()
        header.set_markup('<span size="large" weight="bold">QoS MANAGER</span>')
        header.set_halign(Gtk.Align.START)
        self.pack_start(header, False, False, 0)
        
        # Status indicator
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        status_label = Gtk.Label(label="Status:")
        status_box.pack_start(status_label, False, False, 0)
        
        self.status_indicator = Gtk.Label()
        status_box.pack_start(self.status_indicator, False, False, 0)
        
        self.pack_start(status_box, False, False, 0)
        
        # Priority Classes Section
        priority_frame = Gtk.Frame(label="Priority Classes")
        priority_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        priority_box.set_border_width(10)
        
        # Priority classes grid
        self.priority_labels = {}
        for priority in [QoSPriority.CRITICAL, QoSPriority.HIGH, QoSPriority.NORMAL, QoSPriority.LOW, QoSPriority.BULK]:
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            
            # Priority name
            name_label = Gtk.Label()
            name_label.set_markup(f'<span weight="bold">{priority.name}</span>')
            name_label.set_halign(Gtk.Align.START)
            name_label.set_size_request(100, -1)
            hbox.pack_start(name_label, False, False, 0)
            
            # Stats label
            stats_label = Gtk.Label()
            stats_label.set_halign(Gtk.Align.START)
            self.priority_labels[priority] = stats_label
            hbox.pack_start(stats_label, True, True, 0)
            
            priority_box.pack_start(hbox, False, False, 0)
        
        priority_frame.add(priority_box)
        self.pack_start(priority_frame, False, False, 0)
        
        # Traffic Classes Section
        traffic_frame = Gtk.Frame(label="Traffic Classes")
        traffic_scroll = Gtk.ScrolledWindow()
        traffic_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        traffic_scroll.set_min_content_height(150)
        
        # TreeView for traffic classes
        self.traffic_store = Gtk.ListStore(str, str, str, str)  # class, bandwidth, packets, priority
        self.traffic_tree = Gtk.TreeView(model=self.traffic_store)
        
        columns = [
            ("Traffic Class", 0, 150),
            ("Bandwidth", 1, 120),
            ("Packets", 2, 100),
            ("Priority", 3, 100)
        ]
        
        for title, col_id, width in columns:
            renderer = Gtk.CellRendererText()
            renderer.set_property("font", "monospace 9")
            column = Gtk.TreeViewColumn(title, renderer, text=col_id)
            column.set_fixed_width(width)
            column.set_resizable(True)
            self.traffic_tree.append_column(column)
        
        traffic_scroll.add(self.traffic_tree)
        traffic_frame.add(traffic_scroll)
        self.pack_start(traffic_frame, True, True, 0)
        
        # Bandwidth Limits Section
        limits_frame = Gtk.Frame(label="Bandwidth Limits")
        limits_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        limits_box.set_border_width(10)
        
        self.upload_limit_label = Gtk.Label()
        self.upload_limit_label.set_halign(Gtk.Align.START)
        limits_box.pack_start(self.upload_limit_label, False, False, 0)
        
        self.download_limit_label = Gtk.Label()
        self.download_limit_label.set_halign(Gtk.Align.START)
        limits_box.pack_start(self.download_limit_label, False, False, 0)
        
        limits_frame.add(limits_box)
        self.pack_start(limits_frame, False, False, 0)
        
        # Control buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.connect("clicked", lambda b: self._update_display())
        button_box.pack_start(refresh_btn, True, True, 0)
        
        self.pack_start(button_box, False, False, 0)
    
    def _update_display(self) -> bool:
        """Update QoS dashboard display"""
        try:
            # Check if QoS is active
            status = self.qos_manager.get_qos_status()
            is_active = status.get("enabled", False)
            
            if is_active:
                self.status_indicator.set_markup(
                    f'<span foreground="{Colors.GREEN}">● ACTIVE</span>'
                )
            else:
                self.status_indicator.set_markup(
                    f'<span foreground="{Colors.RED}">● INACTIVE</span>'
                )
            
            # Get traffic classification report
            report = self.qos_manager.get_traffic_classification_report()
            
            # Update priority class stats (simplified)
            for priority, label in self.priority_labels.items():
                # Show placeholder since detailed stats aren't exposed
                label.set_markup(
                    f'<span foreground="{Colors.DIM_TEXT}">Ready</span>'
                )
            
            # Update traffic classes
            self.traffic_store.clear()
            
            # Show configured limits instead of per-class stats
            limits = self.qos_manager.bandwidth_limits
            for name, limit in list(limits.items())[:10]:
                download = Format.bytes(limit.download_kbps * 1024) + "/s"
                upload = Format.bytes(limit.upload_kbps * 1024) + "/s"
                priority_str = limit.priority.name if hasattr(limit, 'priority') else "NORMAL"
                
                self.traffic_store.append([
                    name,
                    f"↓{download} ↑{upload}",
                    "-",
                    priority_str
                ])
            
            # Update bandwidth limits from status
            interface = status.get("interface", "N/A")
            
            self.upload_limit_label.set_markup(
                f'<span foreground="{Colors.DIM_TEXT}">Interface: '
                f'<span foreground="{Colors.GREEN}">{interface}</span></span>'
            )
            
            self.download_limit_label.set_markup(
                f'<span foreground="{Colors.DIM_TEXT}">Bandwidth Limits: '
                f'<span foreground="{Colors.GREEN}">{len(limits)} configured</span></span>'
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update QoS dashboard: {e}")
        
        return True  # Continue timer
