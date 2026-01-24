"""
Schedule Manager Dialog
GUI for managing scheduled connection actions
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from datetime import time as dt_time

from logger import get_logger
from connection_scheduler import (
    get_connection_scheduler,
    Schedule,
    ScheduleAction,
    ScheduleFrequency
)


class ScheduleManagerDialog(Gtk.Dialog):
    """Dialog for managing connection schedules"""
    
    def __init__(self, parent_window):
        super().__init__(
            title="Schedule Manager",
            parent=parent_window,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
        )
        
        self.logger = get_logger()
        self.scheduler = get_connection_scheduler()
        
        self.set_default_size(700, 500)
        
        # Add buttons
        self.add_buttons(
            Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE
        )
        
        self._build_ui()
        self._load_schedules()
    
    def _build_ui(self):
        """Build the schedule manager UI"""
        content = self.get_content_area()
        content.set_spacing(10)
        content.set_border_width(10)
        
        # Info label
        info = Gtk.Label()
        info.set_markup(
            '<span size="large" weight="bold">Connection Schedules</span>\n'
            '<span size="small">Automatically connect/disconnect at scheduled times</span>'
        )
        content.pack_start(info, False, False, 0)
        
        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        new_btn = Gtk.Button(label="New Schedule")
        new_btn.connect("clicked", self._on_new_schedule)
        toolbar.pack_start(new_btn, False, False, 0)
        
        edit_btn = Gtk.Button(label="Edit")
        edit_btn.connect("clicked", self._on_edit_schedule)
        self.edit_btn = edit_btn
        toolbar.pack_start(edit_btn, False, False, 0)
        
        delete_btn = Gtk.Button(label="Delete")
        delete_btn.connect("clicked", self._on_delete_schedule)
        self.delete_btn = delete_btn
        toolbar.pack_start(delete_btn, False, False, 0)
        
        content.pack_start(toolbar, False, False, 0)
        
        # Schedules list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        self.schedule_store = Gtk.ListStore(bool, str, str, str, str, str)  # enabled, name, action, time, frequency, days
        self.schedule_tree = Gtk.TreeView(model=self.schedule_store)
        
        # Enabled checkbox column
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self._on_schedule_toggled)
        column = Gtk.TreeViewColumn("Enabled", renderer_toggle, active=0)
        self.schedule_tree.append_column(column)
        
        # Other columns
        columns = [
            ("Name", 1, 150),
            ("Action", 2, 120),
            ("Time", 3, 80),
            ("Frequency", 4, 100),
            ("Days", 5, 120)
        ]
        
        for title, col_id, width in columns:
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=col_id)
            column.set_fixed_width(width)
            column.set_resizable(True)
            self.schedule_tree.append_column(column)
        
        # Selection handling
        selection = self.schedule_tree.get_selection()
        selection.connect("changed", self._on_selection_changed)
        
        scroll.add(self.schedule_tree)
        content.pack_start(scroll, True, True, 0)
        
        content.show_all()
    
    def _load_schedules(self):
        """Load schedules into tree view"""
        self.schedule_store.clear()
        
        schedules = self.scheduler.get_all_schedules()
        for schedule in schedules:
            days_str = self._format_days(schedule)
            
            self.schedule_store.append([
                schedule.enabled,
                schedule.name,
                schedule.action.value.replace("_", " ").title(),
                schedule.time.strftime("%H:%M"),
                schedule.frequency.value.title(),
                days_str
            ])
    
    def _format_days(self, schedule: Schedule) -> str:
        """Format days list for display"""
        if schedule.frequency != ScheduleFrequency.WEEKLY:
            return "-"
        
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        return ", ".join(day_names[d] for d in sorted(schedule.days))
    
    def _on_selection_changed(self, selection):
        """Handle selection changes"""
        model, treeiter = selection.get_selected()
        has_selection = treeiter is not None
        
        self.edit_btn.set_sensitive(has_selection)
        self.delete_btn.set_sensitive(has_selection)
    
    def _on_schedule_toggled(self, widget, path):
        """Handle schedule enable/disable toggle"""
        self.schedule_store[path][0] = not self.schedule_store[path][0]
        
        # Update actual schedule
        schedule_name = self.schedule_store[path][1]
        schedule = self.scheduler.get_schedule(schedule_name)
        if schedule:
            schedule.enabled = self.schedule_store[path][0]
            self.scheduler.save_schedules()
            self.logger.info(f"Schedule '{schedule_name}' {'enabled' if schedule.enabled else 'disabled'}")
    
    def _on_new_schedule(self, button):
        """Create new schedule"""
        dialog = ScheduleEditDialog(self, None)
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            schedule = dialog.get_schedule()
            if schedule:
                self.scheduler.add_schedule(schedule)
                self._load_schedules()
        
        dialog.destroy()
    
    def _on_edit_schedule(self, button):
        """Edit selected schedule"""
        selection = self.schedule_tree.get_selection()
        model, treeiter = selection.get_selected()
        
        if not treeiter:
            return
        
        schedule_name = model[treeiter][1]
        schedule = self.scheduler.get_schedule(schedule_name)
        
        if not schedule:
            return
        
        dialog = ScheduleEditDialog(self, schedule)
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            updated_schedule = dialog.get_schedule()
            if updated_schedule:
                self.scheduler.update_schedule(schedule_name, updated_schedule)
                self._load_schedules()
        
        dialog.destroy()
    
    def _on_delete_schedule(self, button):
        """Delete selected schedule"""
        selection = self.schedule_tree.get_selection()
        model, treeiter = selection.get_selected()
        
        if not treeiter:
            return
        
        schedule_name = model[treeiter][1]
        
        # Confirm deletion
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Delete schedule '{schedule_name}'?"
        )
        
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            self.scheduler.remove_schedule(schedule_name)
            self._load_schedules()


class ScheduleEditDialog(Gtk.Dialog):
    """Dialog for creating/editing a schedule"""
    
    def __init__(self, parent, schedule: Schedule = None):
        title = "Edit Schedule" if schedule else "New Schedule"
        super().__init__(
            title=title,
            parent=parent,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
        )
        
        self.schedule = schedule
        
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        
        self._build_ui()
        
        if schedule:
            self._load_schedule_data()
    
    def _build_ui(self):
        """Build edit dialog UI"""
        content = self.get_content_area()
        content.set_spacing(10)
        content.set_border_width(10)
        
        # Name
        name_label = Gtk.Label(label="Schedule Name:")
        name_label.set_halign(Gtk.Align.START)
        content.pack_start(name_label, False, False, 0)
        
        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text("e.g., Morning Auto-Connect")
        content.pack_start(self.name_entry, False, False, 0)
        
        # Action
        action_label = Gtk.Label(label="Action:")
        action_label.set_halign(Gtk.Align.START)
        content.pack_start(action_label, False, False, 0)
        
        self.action_combo = Gtk.ComboBoxText()
        self.action_combo.append("connect", "Connect")
        self.action_combo.append("disconnect", "Disconnect")
        self.action_combo.append("enable_stealth", "Enable Stealth")
        self.action_combo.append("disable_stealth", "Disable Stealth")
        self.action_combo.set_active(0)
        content.pack_start(self.action_combo, False, False, 0)
        
        # Time
        time_label = Gtk.Label(label="Time:")
        time_label.set_halign(Gtk.Align.START)
        content.pack_start(time_label, False, False, 0)
        
        time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        self.hour_spin = Gtk.SpinButton.new_with_range(0, 23, 1)
        self.hour_spin.set_value(8)
        time_box.pack_start(self.hour_spin, False, False, 0)
        
        time_box.pack_start(Gtk.Label(label=":"), False, False, 0)
        
        self.minute_spin = Gtk.SpinButton.new_with_range(0, 59, 1)
        self.minute_spin.set_value(0)
        time_box.pack_start(self.minute_spin, False, False, 0)
        
        content.pack_start(time_box, False, False, 0)
        
        # Frequency
        freq_label = Gtk.Label(label="Frequency:")
        freq_label.set_halign(Gtk.Align.START)
        content.pack_start(freq_label, False, False, 0)
        
        self.frequency_combo = Gtk.ComboBoxText()
        self.frequency_combo.append("once", "Once")
        self.frequency_combo.append("daily", "Daily")
        self.frequency_combo.append("weekdays", "Weekdays")
        self.frequency_combo.append("weekends", "Weekends")
        self.frequency_combo.append("weekly", "Weekly (custom)")
        self.frequency_combo.set_active(1)
        self.frequency_combo.connect("changed", self._on_frequency_changed)
        content.pack_start(self.frequency_combo, False, False, 0)
        
        # Days (for weekly)
        self.days_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        self.day_checks = {}
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, name in enumerate(day_names):
            check = Gtk.CheckButton(label=name)
            self.day_checks[i] = check
            self.days_box.pack_start(check, False, False, 0)
        
        content.pack_start(self.days_box, False, False, 0)
        self.days_box.set_no_show_all(True)
        
        content.show_all()
    
    def _load_schedule_data(self):
        """Load existing schedule data into widgets"""
        self.name_entry.set_text(self.schedule.name)
        self.action_combo.set_active_id(self.schedule.action.value)
        self.hour_spin.set_value(self.schedule.time.hour)
        self.minute_spin.set_value(self.schedule.time.minute)
        self.frequency_combo.set_active_id(self.schedule.frequency.value)
        
        if self.schedule.frequency == ScheduleFrequency.WEEKLY:
            for day in self.schedule.days:
                self.day_checks[day].set_active(True)
    
    def _on_frequency_changed(self, combo):
        """Handle frequency selection change"""
        freq_id = combo.get_active_id()
        
        if freq_id == "weekly":
            self.days_box.show()
        else:
            self.days_box.hide()
    
    def get_schedule(self) -> Schedule:
        """Create Schedule object from dialog inputs"""
        name = self.name_entry.get_text().strip()
        if not name:
            return None
        
        action = ScheduleAction(self.action_combo.get_active_id())
        hour = int(self.hour_spin.get_value())
        minute = int(self.minute_spin.get_value())
        schedule_time = dt_time(hour, minute)
        frequency = ScheduleFrequency(self.frequency_combo.get_active_id())
        
        days = []
        if frequency == ScheduleFrequency.WEEKLY:
            days = [i for i, check in self.day_checks.items() if check.get_active()]
        
        return Schedule(
            name=name,
            action=action,
            time=schedule_time,
            frequency=frequency,
            days=days
        )
