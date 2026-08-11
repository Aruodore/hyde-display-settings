from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
from datetime import date

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from controls import stepped_value
from settings import APP_ID, Settings, apply_settings, run_quiet
from styles import APP_CSS
from tracker import DB_PATH

def install_styles() -> None:
    display = Gdk.Display.get_default()
    if display is None:
        return
    provider = Gtk.CssProvider()
    provider.load_from_data(APP_CSS.encode())
    Gtk.StyleContext.add_provider_for_display(
        display,
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


def duration(seconds: int) -> str:
    hours, remainder = divmod(max(0, seconds), 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours} hr {minutes} min"
    if minutes:
        return f"{minutes} min"
    return "Less than a minute"


class DisplaySettingsWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title="Display Settings")
        self.set_default_size(760, 720)
        self.set_size_request(390, 520)
        self.settings = Settings.load()
        self.usage_rows: list[Gtk.Widget] = []
        self.toast_overlay = Adw.ToastOverlay()
        self.stack = Adw.ViewStack()
        self._build_window()
        GLib.timeout_add_seconds(30, self._refresh_usage)

    def _build_window(self) -> None:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        switcher = Adw.ViewSwitcher()
        switcher.add_css_class("display-tabs")
        switcher.set_stack(self.stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(switcher)

        self.apply_button = Gtk.Button(label="Save & Apply")
        self.apply_button.add_css_class("suggested-action")
        self.apply_button.set_tooltip_text("Save settings and reload the idle and night-light services")
        self.apply_button.connect("clicked", self._apply)
        header.pack_end(self.apply_button)

        toolbar.add_top_bar(header)
        toolbar.set_content(self.stack)
        self.toast_overlay.set_child(toolbar)
        self.set_content(self.toast_overlay)

        self.stack.add_titled_with_icon(self._display_page(), "display", "Display", "video-display-symbolic")
        self.stack.add_titled_with_icon(self._idle_page(), "idle", "Idle", "preferences-system-time-symbolic")
        self.stack.add_titled_with_icon(self._screen_time_page(), "usage", "Screen Time", "view-statistics-symbolic")

    def _display_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage()

        monitors = Adw.PreferencesGroup(title="Displays", description="Resolution, refresh rate, scale, position, and rotation")
        monitor_row = Adw.ActionRow(title="Monitor layout", subtitle=self._monitor_summary())
        monitor_row.set_activatable(True)
        monitor_row.add_prefix(Gtk.Image.new_from_icon_name("video-display-symbolic"))
        arrow = Gtk.Image.new_from_icon_name("go-next-symbolic")
        monitor_row.add_suffix(arrow)
        monitor_row.connect("activated", self._open_monitor_layout)
        monitors.add(monitor_row)
        page.add(monitors)

        light = Adw.PreferencesGroup(title="Light")
        self.brightness_row = Adw.ActionRow(title="Brightness")
        self.brightness_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 100, 1)
        self.brightness_scale.set_size_request(230, -1)
        self.brightness_scale.set_valign(Gtk.Align.CENTER)
        self.brightness_scale.set_value(self._current_brightness())
        self.brightness_scale.set_tooltip_text("Adjust display brightness")
        self.brightness_scale.connect("value-changed", self._brightness_changed)
        self.brightness_row.add_suffix(self.brightness_scale)
        light.add(self.brightness_row)

        self.night_enabled = Adw.SwitchRow(title="Night light", subtitle="Reduce blue light on a daily schedule")
        self.night_enabled.set_active(self.settings.night_light_enabled)
        light.add(self.night_enabled)

        self.temperature = Adw.SpinRow.new_with_range(2500, 6500, 100)
        self.temperature.set_title("Night temperature")
        self.temperature.set_subtitle("Lower values appear warmer")
        self.temperature.set_value(self.settings.night_temperature)
        light.add(self.temperature)

        self.night_start = Adw.EntryRow(title="Starts at")
        self.night_start.set_text(self.settings.night_start)
        light.add(self.night_start)

        self.night_end = Adw.EntryRow(title="Ends at")
        self.night_end.set_text(self.settings.night_end)
        light.add(self.night_end)
        page.add(light)
        return page

    def _idle_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage()
        intro = Adw.PreferencesGroup(
            title="When inactive",
            description="Choose times, then use Save and Apply. Closing without applying discards these changes.",
        )
        self.dim_switch, self.dim_value, self.dim_row = self._timeout_row("Dim display", "Lower brightness without locking", self.settings.dim_enabled, self.settings.dim_minutes)
        self.lock_switch, self.lock_value, self.lock_row = self._timeout_row("Lock screen", "Require your password to return", self.settings.lock_enabled, self.settings.lock_minutes)
        self.off_switch, self.off_value, self.off_row = self._timeout_row("Turn display off", "Blank displays while apps and background work keep running", self.settings.display_off_enabled, self.settings.display_off_minutes)
        self.suspend_switch, self.suspend_value, self.suspend_row = self._timeout_row("Suspend computer", "Pause the computer and its running processes", self.settings.suspend_enabled, self.settings.suspend_minutes)
        for row in (self.dim_row, self.lock_row, self.off_row, self.suspend_row):
            intro.add(row)
        page.add(intro)

        safety = Adw.PreferencesGroup(title="Order and safety")
        note = Adw.ActionRow(
            title="Lock before display-off and suspend",
            subtitle="Use increasing times so the session is secured before the screen powers down.",
        )
        note.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
        safety.add(note)
        page.add(safety)
        return page

    def _timeout_row(self, title: str, subtitle: str, enabled: bool, minutes: int) -> tuple[Gtk.Switch, Gtk.Adjustment, Adw.ActionRow]:
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        switch = Gtk.Switch(active=enabled, valign=Gtk.Align.CENTER)
        switch.set_tooltip_text(f"Enable {title.lower()}")
        row.add_prefix(switch)

        adjustment = Gtk.Adjustment(value=minutes, lower=1, upper=240, step_increment=1)
        value_label = Gtk.Label(label=f"{minutes} min", width_chars=7, xalign=0.5)
        value_label.add_css_class("numeric")

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        controls.set_valign(Gtk.Align.CENTER)
        controls.add_css_class("linked")
        decrease = Gtk.Button(label="−")
        decrease.set_tooltip_text(f"Reduce {title.lower()} time")
        decrease.update_property([Gtk.AccessibleProperty.LABEL], [f"Reduce {title.lower()} time"])
        increase = Gtk.Button(label="+")
        increase.set_tooltip_text(f"Increase {title.lower()} time")
        increase.update_property([Gtk.AccessibleProperty.LABEL], [f"Increase {title.lower()} time"])

        def change(_button: Gtk.Button, delta: int) -> None:
            value = stepped_value(round(adjustment.get_value()), delta)
            adjustment.set_value(value)
            value_label.set_label(f"{value} min")

        decrease.connect("clicked", change, -1)
        increase.connect("clicked", change, 1)
        controls.append(decrease)
        controls.append(value_label)
        controls.append(increase)
        row.add_suffix(controls)
        return switch, adjustment, row

    def _screen_time_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage()
        controls = Adw.PreferencesGroup(title="Privacy")
        self.tracking = Adw.SwitchRow(
            title="Track screen time",
            subtitle="Store only app identity and active duration on this computer",
        )
        self.tracking.set_active(self.settings.tracking_enabled)
        self.tracking.connect("notify::active", self._tracking_changed)
        controls.add(self.tracking)

        erase = Adw.ActionRow(title="Erase screen-time history", subtitle="Permanently remove all recorded app durations")
        erase.add_prefix(Gtk.Image.new_from_icon_name("user-trash-symbolic"))
        erase.set_activatable(True)
        erase.connect("activated", self._confirm_erase)
        controls.add(erase)
        page.add(controls)

        self.usage_group = Adw.PreferencesGroup(title="Today")
        page.add(self.usage_group)
        self._populate_usage()
        return page

    def _populate_usage(self) -> None:
        for child in self.usage_rows:
            self.usage_group.remove(child)
        self.usage_rows.clear()
        records: list[tuple[str, int]] = []
        if DB_PATH.exists():
            try:
                with sqlite3.connect(DB_PATH) as connection:
                    records = connection.execute(
                        "SELECT app, seconds FROM usage WHERE day = ? ORDER BY seconds DESC LIMIT 8",
                        (date.today().isoformat(),),
                    ).fetchall()
            except sqlite3.Error:
                records = []
        total = 0
        if DB_PATH.exists():
            try:
                with sqlite3.connect(DB_PATH) as connection:
                    total = connection.execute(
                        "SELECT COALESCE(SUM(seconds), 0) FROM usage WHERE day = ?",
                        (date.today().isoformat(),),
                    ).fetchone()[0]
            except sqlite3.Error:
                total = sum(seconds for _app, seconds in records)
        summary = Adw.ActionRow(title="Total active time", subtitle=duration(total))
        summary.add_prefix(Gtk.Image.new_from_icon_name("preferences-system-time-symbolic"))
        self.usage_group.add(summary)
        self.usage_rows.append(summary)
        if not records:
            empty = Adw.ActionRow(title="No activity yet", subtitle="Activity will appear after the tracker has run for a few minutes.")
            self.usage_group.add(empty)
            self.usage_rows.append(empty)
            return
        for app, seconds in records:
            row = Adw.ActionRow(title=app, subtitle=duration(seconds))
            row.add_prefix(Gtk.Image.new_from_icon_name("application-x-executable-symbolic"))
            self.usage_group.add(row)
            self.usage_rows.append(row)

    def _refresh_usage(self) -> bool:
        self._populate_usage()
        return GLib.SOURCE_CONTINUE

    def _monitor_summary(self) -> str:
        result = run_quiet("hyprctl", "monitors", "-j")
        if result.returncode == 0:
            try:
                import json

                monitors = json.loads(result.stdout)
                if monitors:
                    return f"{len(monitors)} connected. Open the visual layout editor."
            except (ValueError, TypeError):
                pass
        return "Open the visual layout editor"

    def _current_brightness(self) -> int:
        result = run_quiet("brightnessctl", "-m")
        if result.returncode == 0:
            try:
                return int(result.stdout.strip().split(",")[3].rstrip("%"))
            except (IndexError, ValueError):
                pass
        return 50

    def _brightness_changed(self, scale: Gtk.Scale) -> None:
        value = round(scale.get_value())
        result = run_quiet("brightnessctl", "set", f"{value}%")
        if result.returncode != 0:
            self._toast("Brightness control is unavailable")

    def _open_monitor_layout(self, _row: Adw.ActionRow) -> None:
        if not shutil.which("nwg-displays"):
            self._toast("Install nwg-displays to edit monitor layout")
            return
        subprocess.Popen(["nwg-displays"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @staticmethod
    def _valid_time(value: str) -> bool:
        try:
            hours, minutes = map(int, value.split(":"))
            return 0 <= hours <= 23 and 0 <= minutes <= 59 and len(value) == 5
        except (ValueError, TypeError):
            return False

    def _apply(self, _button: Gtk.Button) -> None:
        start, end = self.night_start.get_text().strip(), self.night_end.get_text().strip()
        if not self._valid_time(start) or not self._valid_time(end):
            self._toast("Use 24-hour times such as 21:00")
            return
        values = [
            (self.dim_switch, self.dim_value, "dim"),
            (self.lock_switch, self.lock_value, "lock"),
            (self.off_switch, self.off_value, "display-off"),
            (self.suspend_switch, self.suspend_value, "suspend"),
        ]
        enabled_times = [(round(row.get_value()), name) for switch, row, name in values if switch.get_active()]
        if enabled_times != sorted(enabled_times):
            self._toast("Idle actions must be ordered from shortest to longest")
            return
        self.settings.dim_enabled = self.dim_switch.get_active()
        self.settings.lock_enabled = self.lock_switch.get_active()
        self.settings.display_off_enabled = self.off_switch.get_active()
        self.settings.suspend_enabled = self.suspend_switch.get_active()
        self.settings.dim_minutes = round(self.dim_value.get_value())
        self.settings.lock_minutes = round(self.lock_value.get_value())
        self.settings.display_off_minutes = round(self.off_value.get_value())
        self.settings.suspend_minutes = round(self.suspend_value.get_value())
        self.settings.night_light_enabled = self.night_enabled.get_active()
        self.settings.night_temperature = round(self.temperature.get_value())
        self.settings.night_start = start
        self.settings.night_end = end
        self.settings.tracking_enabled = self.tracking.get_active()
        try:
            apply_settings(self.settings)
            self._toast("Display and idle settings applied")
        except OSError as error:
            self._toast(f"Could not apply settings: {error.strerror or error}")

    def _tracking_changed(self, row: Adw.SwitchRow, _param: object) -> None:
        self.settings.tracking_enabled = row.get_active()
        self.settings.save()

    def _confirm_erase(self, _row: Adw.ActionRow) -> None:
        dialog = Adw.AlertDialog(
            heading="Erase screen-time history?",
            body="All recorded app durations will be permanently removed. This cannot be undone.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("erase", "Erase")
        dialog.set_response_appearance("erase", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._erase_response)
        dialog.present(self)

    def _erase_response(self, _dialog: Adw.AlertDialog, response: str) -> None:
        if response != "erase":
            return
        if DB_PATH.exists():
            try:
                with sqlite3.connect(DB_PATH) as connection:
                    connection.execute("DELETE FROM usage")
                    connection.commit()
            except sqlite3.Error:
                self._toast("Could not erase screen-time history")
                return
        self._populate_usage()
        self._toast("Screen-time history erased")

    def _toast(self, message: str) -> None:
        self.toast_overlay.add_toast(Adw.Toast(title=message, timeout=3))


class DisplaySettingsApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        install_styles()
        self.connect("activate", self._activate)

    def _activate(self, _app: Adw.Application) -> None:
        window = self.props.active_window
        if not window:
            window = DisplaySettingsWindow(self)
        window.present()


def main() -> int:
    return DisplaySettingsApp().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
