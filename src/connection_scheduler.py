"""
Connection Scheduler
Enables time-based automatic connection and disconnection
"""

import json
import threading
import time
from datetime import datetime, time as dt_time
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable

from logger import get_logger


class ScheduleAction(Enum):
    """Schedule action types"""
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    ENABLE_STEALTH = "enable_stealth"
    DISABLE_STEALTH = "disable_stealth"


class ScheduleFrequency(Enum):
    """Schedule frequency types"""
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    WEEKDAYS = "weekdays"
    WEEKENDS = "weekends"


class Schedule:
    """Represents a scheduled action"""
    
    def __init__(
        self,
        name: str,
        action: ScheduleAction,
        time: dt_time,
        frequency: ScheduleFrequency,
        enabled: bool = True,
        days: Optional[List[int]] = None
    ):
        self.name = name
        self.action = action
        self.time = time
        self.frequency = frequency
        self.enabled = enabled
        self.days = days or []  # 0=Monday, 6=Sunday for weekly schedules
        self.last_run = None
    
    def should_run_now(self) -> bool:
        """Check if schedule should run at current time"""
        if not self.enabled:
            return False
        
        now = datetime.now()
        current_time = now.time()
        current_day = now.weekday()
        
        # Check if time matches (within 1 minute tolerance)
        time_diff = abs(
            (current_time.hour * 60 + current_time.minute) -
            (self.time.hour * 60 + self.time.minute)
        )
        if time_diff > 1:
            return False
        
        # Check if already run today
        if self.last_run:
            last_run_date = datetime.fromtimestamp(self.last_run).date()
            if last_run_date == now.date():
                return False
        
        # Check frequency
        if self.frequency == ScheduleFrequency.ONCE:
            return self.last_run is None
        
        elif self.frequency == ScheduleFrequency.DAILY:
            return True
        
        elif self.frequency == ScheduleFrequency.WEEKDAYS:
            return current_day < 5  # Monday-Friday
        
        elif self.frequency == ScheduleFrequency.WEEKENDS:
            return current_day >= 5  # Saturday-Sunday
        
        elif self.frequency == ScheduleFrequency.WEEKLY:
            return current_day in self.days
        
        return False
    
    def to_dict(self) -> Dict:
        """Convert schedule to dictionary"""
        return {
            "name": self.name,
            "action": self.action.value,
            "time": self.time.strftime("%H:%M"),
            "frequency": self.frequency.value,
            "enabled": self.enabled,
            "days": self.days,
            "last_run": self.last_run
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Schedule":
        """Create schedule from dictionary"""
        time_parts = data["time"].split(":")
        schedule_time = dt_time(int(time_parts[0]), int(time_parts[1]))
        
        schedule = cls(
            name=data["name"],
            action=ScheduleAction(data["action"]),
            time=schedule_time,
            frequency=ScheduleFrequency(data["frequency"]),
            enabled=data.get("enabled", True),
            days=data.get("days", [])
        )
        schedule.last_run = data.get("last_run")
        return schedule


class ConnectionScheduler:
    """Manages scheduled connection actions"""
    
    def __init__(self):
        self.logger = get_logger()
        self.config_dir = Path.home() / ".config" / "pdanet-linux"
        self.schedules_file = self.config_dir / "schedules.json"
        
        self.schedules: List[Schedule] = []
        self.callbacks: Dict[ScheduleAction, Callable] = {}
        
        self.running = False
        self.scheduler_thread = None
        
        self.load_schedules()
    
    def load_schedules(self):
        """Load schedules from file"""
        if not self.schedules_file.exists():
            return
        
        try:
            with open(self.schedules_file, "r") as f:
                data = json.load(f)
            
            self.schedules = [Schedule.from_dict(s) for s in data]
            self.logger.info(f"Loaded {len(self.schedules)} schedules")
            
        except Exception as e:
            self.logger.error(f"Failed to load schedules: {e}")
    
    def save_schedules(self):
        """Save schedules to file"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            data = [s.to_dict() for s in self.schedules]
            
            with open(self.schedules_file, "w") as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Saved {len(self.schedules)} schedules")
            
        except Exception as e:
            self.logger.error(f"Failed to save schedules: {e}")
    
    def add_schedule(self, schedule: Schedule):
        """Add a new schedule"""
        self.schedules.append(schedule)
        self.save_schedules()
        self.logger.info(f"Added schedule: {schedule.name}")
    
    def remove_schedule(self, name: str) -> bool:
        """Remove a schedule by name"""
        for i, schedule in enumerate(self.schedules):
            if schedule.name == name:
                del self.schedules[i]
                self.save_schedules()
                self.logger.info(f"Removed schedule: {name}")
                return True
        return False
    
    def update_schedule(self, name: str, updated_schedule: Schedule) -> bool:
        """Update an existing schedule"""
        for i, schedule in enumerate(self.schedules):
            if schedule.name == name:
                self.schedules[i] = updated_schedule
                self.save_schedules()
                self.logger.info(f"Updated schedule: {name}")
                return True
        return False
    
    def get_schedule(self, name: str) -> Optional[Schedule]:
        """Get a schedule by name"""
        for schedule in self.schedules:
            if schedule.name == name:
                return schedule
        return None
    
    def get_all_schedules(self) -> List[Schedule]:
        """Get all schedules"""
        return self.schedules.copy()
    
    def register_callback(self, action: ScheduleAction, callback: Callable):
        """Register a callback for an action type"""
        self.callbacks[action] = callback
        self.logger.info(f"Registered callback for {action.value}")
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            self.logger.warning("Scheduler already running")
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        self.logger.info("Connection scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        self.logger.info("Connection scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                self._check_schedules()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                time.sleep(60)
    
    def _check_schedules(self):
        """Check and execute due schedules"""
        for schedule in self.schedules:
            if schedule.should_run_now():
                self._execute_schedule(schedule)
    
    def _execute_schedule(self, schedule: Schedule):
        """Execute a scheduled action"""
        try:
            self.logger.info(f"Executing schedule: {schedule.name} ({schedule.action.value})")
            
            # Call registered callback
            callback = self.callbacks.get(schedule.action)
            if callback:
                callback()
            else:
                self.logger.warning(f"No callback registered for {schedule.action.value}")
            
            # Update last run time
            schedule.last_run = time.time()
            self.save_schedules()
            
        except Exception as e:
            self.logger.error(f"Failed to execute schedule {schedule.name}: {e}")


# Singleton instance
_scheduler_instance = None


def get_connection_scheduler() -> ConnectionScheduler:
    """Get singleton scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ConnectionScheduler()
    return _scheduler_instance
