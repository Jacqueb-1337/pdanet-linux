# PdaNet Linux - New Features Documentation

## Overview

This document describes the major enhancements and new features added to PdaNet Linux to improve functionality, user experience, and automation capabilities.

## Table of Contents

1. [Profile Management System](#profile-management-system)
2. [Desktop Notifications](#desktop-notifications)
3. [Data Usage Alerts](#data-usage-alerts)
4. [Advanced Network Monitor](#advanced-network-monitor)
5. [QoS Dashboard](#qos-dashboard)
6. [Connection Scheduler](#connection-scheduler)
7. [Integration Guide](#integration-guide)

---

## Profile Management System

### Overview
Complete connection profile management system for saving, loading, and organizing different network configurations.

### Features

#### Create/Edit Profiles
- **New Profile Dialog**: User-friendly interface for creating profiles
  - Profile name (e.g., "Home WiFi", "Office USB")
  - Connection mode: USB or WiFi
  - Optional SSID for WiFi hotspots
  - Inherits current settings (proxy, stealth level, auto-reconnect)

#### Profile Operations
- **Edit**: Modify existing profile settings
- **Delete**: Remove profiles with confirmation dialog
- **Import**: Load profiles from JSON files
- **Export**: Save profiles to JSON for backup/sharing

#### User Interface
- TreeView display with columns: Name, Mode, SSID
- Selection-based button enabling (edit/delete only when profile selected)
- Checkbox-based enable/disable for each profile

### Usage

```python
from config_manager import get_config

config = get_config()

# Create a profile
profile_settings = {
    'mode': 'wifi',
    'ssid': 'AndroidAP',
    'stealth_level': 3,
    'auto_reconnect': True
}
config.add_profile("My Home WiFi", profile_settings)

# Load a profile
settings = config.get_profile("My Home WiFi")

# List all profiles
profiles = config.get_all_profiles()
```

### File Location
Profiles are stored in `~/.config/pdanet-linux/profiles.json`

---

## Desktop Notifications

### Overview
System-wide desktop notifications for important connection events using libnotify.

### Notification Types

#### Connection State Changes
- **Connected**: Low urgency, green icon
- **Disconnected**: Low urgency, info icon
- **Error**: Critical urgency, red icon with error details

#### Data Usage Alerts
- Threshold warnings when approaching data limits
- Configurable via Settings → General → Data Warning Threshold

### Features
- Uses Notify library (libnotify) for native desktop integration
- Respects user preference (can be disabled in settings)
- Three urgency levels: low, normal, critical
- Network icon for all notifications

### Usage

```python
from pdanet_gui_v2 import PdaNetGUI

# Notifications are automatically triggered by state changes
# Manual notification:
gui.show_notification(
    "Custom Title",
    "Custom message",
    urgency="normal"  # or "low", "critical"
)
```

### Configuration
Settings → General → Enable Notifications

---

## Data Usage Alerts

### Overview
Real-time monitoring and alerting for data usage thresholds.

### Features

#### Threshold Configuration
- Configurable threshold in GB (default: 10 GB)
- Separate tracking for:
  - Session usage (current connection)
  - Daily usage
  - Monthly usage

#### Alert Behavior
- Desktop notification when threshold reached
- Visual warning in Data Usage Dashboard
- Respects "Enable Data Warnings" setting

#### Reset Functions
- Reset session counter
- Reset monthly counter with confirmation

### Usage

Via Settings Dialog:
1. Settings → General → Data Warning Threshold
2. Set threshold in GB
3. Enable/disable "Data Usage Warnings"

### Monitoring
- Updates every 5 seconds
- Persistent storage in `~/.config/pdanet-linux/usage_data.json`
- Visual meter shows percentage of threshold used

---

## Advanced Network Monitor

### Overview
Comprehensive network traffic analysis and visualization panel with three specialized tabs.

### Architecture

```
NetworkMonitorPanel
├── Active Flows Tab
│   ├── Protocol breakdown
│   ├── Connection statistics
│   └── Security event counter
├── Bandwidth Tab
│   ├── Application usage
│   ├── Upload/download tracking
│   └── Top bandwidth consumers
└── Security Tab
    ├── Security events log
    ├── Severity levels
    └── Event type classification
```

### Active Flows Tab

#### Features
- Real-time protocol breakdown (TCP, UDP, HTTP, HTTPS, etc.)
- Connection count and bytes transferred per protocol
- Total flow statistics
- Security events counter

#### Columns
- Protocol
- Source (IP:Port)
- Destination (IP:Port)
- Bytes
- Packets
- Duration

### Bandwidth Tab

#### Features
- Top 15 applications by bandwidth usage
- Upload/download breakdown per application
- Total bandwidth summary
- Sorted by total usage (descending)

#### Columns
- Application/Protocol name
- Upload (formatted bytes)
- Download (formatted bytes)
- Total (formatted bytes)

### Security Tab

#### Features
- Security event log with timestamps
- Color-coded severity levels
- Event type classification
- Source IP tracking
- Clear events button

#### Event Types
- Suspicious traffic
- Port scans
- DNS leaks
- Geographic anomalies

#### Severity Levels
- Low (informational)
- Medium (warning)
- High (important)
- Critical (urgent)

### Usage

```python
from widgets.network_monitor_panel import NetworkMonitorPanel

# Add to GUI
monitor_panel = NetworkMonitorPanel()
notebook.append_page(monitor_panel, Gtk.Label(label="Network Monitor"))

# Updates automatically every 2 seconds
```

### Integration
Uses `AdvancedNetworkMonitor` from `advanced_network_monitor.py` for data collection.

---

## QoS Dashboard

### Overview
Quality of Service (QoS) management dashboard for bandwidth control and traffic prioritization.

### Features

#### Priority Classes
Visual display of 5 priority levels:
- **CRITICAL**: Highest priority (VoIP, gaming)
- **HIGH**: Important traffic (video streaming)
- **NORMAL**: Standard web traffic
- **LOW**: Background downloads
- **BULK**: Bulk data transfers

#### Traffic Classes
- Real-time traffic class display
- Bandwidth allocation per class
- Packet counts
- Priority assignments

#### Bandwidth Limits
- Upload limit display (Mbps)
- Download limit display (Mbps)
- Interface status
- Configuration count

#### Controls
- Manual refresh button
- Real-time status indicator (Active/Inactive)

### Usage

```python
from widgets.qos_dashboard import QoSDashboard

# Add to GUI
qos_panel = QoSDashboard()
notebook.append_page(qos_panel, Gtk.Label(label="QoS"))

# Updates automatically every 3 seconds
```

### Integration
Uses `IntelligentBandwidthManager` from `intelligent_bandwidth_manager.py` for QoS operations.

---

## Connection Scheduler

### Overview
Automated time-based connection management with flexible scheduling options.

### Schedule Types

#### Once
- Execute action one time at specified time
- Useful for one-off automation

#### Daily
- Execute every day at specified time
- Most common schedule type

#### Weekdays
- Execute Monday-Friday only
- Useful for work-related automation

#### Weekends
- Execute Saturday-Sunday only
- Useful for leisure-time automation

#### Weekly (Custom)
- Select specific days of week
- Maximum flexibility

### Actions

#### Connect
- Automatically establish connection at scheduled time
- Uses configured connection profile

#### Disconnect
- Automatically disconnect at scheduled time
- Clean shutdown of connection

#### Enable Stealth
- Activate stealth mode at scheduled time
- Useful for time-based carrier bypass

#### Disable Stealth
- Deactivate stealth mode
- Reduce overhead when not needed

### Features

#### Schedule Management
- Enable/disable schedules via checkbox
- Edit existing schedules
- Delete schedules with confirmation
- Persistent storage in JSON

#### Execution
- Background thread checks every 30 seconds
- 1-minute tolerance for execution time
- Prevents duplicate execution on same day
- Callback system for action execution

#### User Interface
- ScheduleManagerDialog for visual management
- TreeView with sortable columns
- Color-coded status indicators
- Intuitive edit dialog with time picker

### Usage

#### Creating a Schedule

```python
from connection_scheduler import get_connection_scheduler, Schedule, ScheduleAction, ScheduleFrequency
from datetime import time as dt_time

scheduler = get_connection_scheduler()

# Create morning auto-connect
schedule = Schedule(
    name="Morning Connect",
    action=ScheduleAction.CONNECT,
    time=dt_time(8, 0),  # 8:00 AM
    frequency=ScheduleFrequency.WEEKDAYS,
    enabled=True
)

scheduler.add_schedule(schedule)
```

#### Starting the Scheduler

```python
# Register callbacks
scheduler.register_callback(
    ScheduleAction.CONNECT,
    connection_manager.connect
)

scheduler.register_callback(
    ScheduleAction.DISCONNECT,
    connection_manager.disconnect
)

# Start scheduler
scheduler.start()
```

#### Managing Schedules via GUI

```python
from dialogs.schedule_manager_dialog import ScheduleManagerDialog

# Open schedule manager
dialog = ScheduleManagerDialog(parent_window)
dialog.run()
dialog.destroy()
```

### File Location
Schedules are stored in `~/.config/pdanet-linux/schedules.json`

### Schedule Format

```json
{
  "name": "Morning Connect",
  "action": "connect",
  "time": "08:00",
  "frequency": "weekdays",
  "enabled": true,
  "days": [],
  "last_run": null
}
```

---

## Integration Guide

### Adding Features to Main GUI

#### 1. Import New Modules

```python
from widgets.network_monitor_panel import NetworkMonitorPanel
from widgets.qos_dashboard import QoSDashboard
from dialogs.schedule_manager_dialog import ScheduleManagerDialog
from connection_scheduler import get_connection_scheduler
```

#### 2. Initialize Scheduler

```python
def __init__(self):
    # ... existing code ...
    
    # Initialize scheduler
    self.scheduler = get_connection_scheduler()
    
    # Register callbacks
    self.scheduler.register_callback(
        ScheduleAction.CONNECT,
        self._on_scheduled_connect
    )
    self.scheduler.register_callback(
        ScheduleAction.DISCONNECT,
        self._on_scheduled_disconnect
    )
    
    # Start scheduler
    self.scheduler.start()
```

#### 3. Add Visualization Panels

```python
def _create_advanced_tabs(self):
    """Create advanced feature tabs"""
    notebook = Gtk.Notebook()
    
    # Network Monitor
    monitor_panel = NetworkMonitorPanel()
    notebook.append_page(monitor_panel, Gtk.Label(label="Network"))
    
    # QoS Dashboard
    qos_panel = QoSDashboard()
    notebook.append_page(qos_panel, Gtk.Label(label="QoS"))
    
    return notebook
```

#### 4. Add Menu Items

```python
def _create_menu(self):
    # ... existing menu items ...
    
    # Schedules menu item
    schedule_item = Gtk.MenuItem(label="Manage Schedules")
    schedule_item.connect("activate", self._on_manage_schedules)
    menu.append(schedule_item)
```

#### 5. Handle Schedule Dialog

```python
def _on_manage_schedules(self, widget):
    """Open schedule manager dialog"""
    dialog = ScheduleManagerDialog(self)
    dialog.run()
    dialog.destroy()
```

### Cleanup on Exit

```python
def on_destroy(self, widget):
    """Cleanup on application exit"""
    # Stop scheduler
    if hasattr(self, 'scheduler'):
        self.scheduler.stop()
    
    # ... existing cleanup ...
```

---

## Configuration Files

### Summary of New Files

| File | Purpose | Format |
|------|---------|--------|
| `profiles.json` | Connection profiles | JSON |
| `schedules.json` | Scheduled actions | JSON |
| `usage_data.json` | Data usage tracking | JSON |

### File Locations
All files stored in: `~/.config/pdanet-linux/`

---

## Feature Compatibility Matrix

| Feature | USB Mode | WiFi Mode | Stealth Compatible |
|---------|----------|-----------|-------------------|
| Profile Management | ✅ | ✅ | ✅ |
| Desktop Notifications | ✅ | ✅ | ✅ |
| Data Usage Alerts | ✅ | ✅ | ✅ |
| Network Monitor | ✅ | ✅ | ✅ |
| QoS Dashboard | ✅ | ✅ | ✅ |
| Connection Scheduler | ✅ | ✅ | ✅ |

---

## Performance Impact

### Resource Usage

| Feature | CPU Impact | Memory Impact | Disk I/O |
|---------|-----------|---------------|----------|
| Profile Management | Negligible | < 1 MB | Minimal |
| Notifications | Negligible | < 100 KB | None |
| Data Usage Alerts | < 1% | < 500 KB | Minimal |
| Network Monitor | 1-2% | 2-5 MB | Low |
| QoS Dashboard | < 1% | 1-2 MB | Low |
| Connection Scheduler | Negligible | < 500 KB | Minimal |

### Update Intervals
- Network Monitor: Every 2 seconds
- QoS Dashboard: Every 3 seconds
- Data Usage: Every 5 seconds
- Scheduler: Every 30 seconds

---

## Troubleshooting

### Desktop Notifications Not Working

**Symptoms**: No notifications appear on connect/disconnect

**Solutions**:
1. Check if libnotify is installed: `dpkg -l | grep libnotify`
2. Verify settings: Settings → General → Enable Notifications
3. Check logs: `~/.config/pdanet-linux/pdanet.log`

### Schedules Not Executing

**Symptoms**: Scheduled actions don't trigger at specified time

**Solutions**:
1. Verify scheduler is running: Check logs for "scheduler started"
2. Check schedule is enabled in Schedule Manager
3. Verify system time is correct
4. Check callbacks are registered properly

### Network Monitor Shows No Data

**Symptoms**: Network Monitor tabs are empty

**Solutions**:
1. Ensure Advanced Network Monitor is enabled in Settings
2. Check if connection is active
3. Verify monitoring started: Check logs
4. Ensure `ss` command is available: `which ss`

### QoS Dashboard Shows Inactive

**Symptoms**: QoS status shows as inactive

**Solutions**:
1. Enable QoS in Settings → Advanced → Intelligent QoS
2. Verify connection is active
3. Check interface configuration
4. Review QoS logs for errors

---

## Future Enhancements

### Planned Features
- Bandwidth usage graphs with historical data
- Export schedules to iCal format
- Profile templates for common setups
- Advanced filtering in Network Monitor
- Custom QoS rules editor
- Schedule conflict detection
- Multi-profile quick switching

### Community Requests
- Integration with system power management
- VPN profile integration
- Backup/restore all settings
- Cloud sync for profiles and schedules

---

## API Reference

### Profile Management API

```python
# Get config manager
from config_manager import get_config
config = get_config()

# Profile operations
config.add_profile(name: str, settings: dict)
config.get_profile(name: str) -> dict
config.get_all_profiles() -> dict
config.delete_profile(name: str) -> bool
config.list_profiles() -> list
```

### Scheduler API

```python
# Get scheduler
from connection_scheduler import get_connection_scheduler
scheduler = get_connection_scheduler()

# Schedule operations
scheduler.add_schedule(schedule: Schedule)
scheduler.remove_schedule(name: str) -> bool
scheduler.update_schedule(name: str, schedule: Schedule) -> bool
scheduler.get_schedule(name: str) -> Schedule
scheduler.get_all_schedules() -> list

# Lifecycle
scheduler.start()
scheduler.stop()

# Callbacks
scheduler.register_callback(action: ScheduleAction, callback: Callable)
```

### Notification API

```python
# Show notification
gui.show_notification(
    title: str,
    message: str,
    urgency: str = "normal"  # "low", "normal", "critical"
)
```

---

## Testing

### Unit Tests

```bash
# Test profile management
pytest tests/test_config_manager.py -v

# Test all features
pytest tests/ -v
```

### Manual Testing Checklist

#### Profile Management
- [ ] Create new profile
- [ ] Edit existing profile
- [ ] Delete profile
- [ ] Import profile from JSON
- [ ] Export profile to JSON

#### Notifications
- [ ] Connect notification appears
- [ ] Disconnect notification appears
- [ ] Error notification appears
- [ ] Data threshold notification appears

#### Scheduler
- [ ] Create daily schedule
- [ ] Create weekly schedule
- [ ] Enable/disable schedule
- [ ] Edit schedule
- [ ] Delete schedule
- [ ] Verify schedule executes

#### Monitoring
- [ ] Network Monitor displays flows
- [ ] Bandwidth tab shows data
- [ ] Security events appear
- [ ] QoS Dashboard shows status
- [ ] All tabs update in real-time

---

## Conclusion

These enhancements significantly improve PdaNet Linux's functionality, providing:

- **Better User Experience**: Profile management and notifications
- **Advanced Monitoring**: Network visualization and QoS management
- **Automation**: Time-based scheduling for hands-free operation
- **Data Management**: Usage tracking and alerts

All features are designed with the cyberpunk theme and professional interface in mind, maintaining consistency with the existing application design.

For questions or issues, please check the logs at `~/.config/pdanet-linux/pdanet.log`
