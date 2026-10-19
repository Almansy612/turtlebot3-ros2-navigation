#!/usr/bin/env python3
"""
TurtleBot3 Burger — Full Control GUI
ROS2 Humble  |  nav2_simple_commander  |  tkinter

ONE terminal only:
  source /opt/ros/humble/setup.bash
  python3 burger_gui.py

The GUI opens immediately.
Use the buttons to launch bringup and Nav2 in separate windows.
Navigation unlocks automatically once Nav2 is detected as active.
"""

import tkinter as tk
import threading
import subprocess
from datetime import datetime

import rclpy
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from geometry_msgs.msg import PoseStamped

# ── Colours ───────────────────────────────────────────────────────────────────
BG      = "#0a0c10"
PANEL   = "#0f1117"
BORDER  = "#1e2330"
ACCENT  = "#00e5a0"
WARN    = "#ffb830"
DANGER  = "#ff4560"
TEXT    = "#c9d1e0"
DIM     = "#4a5568"
DARK    = "#080b10"
CUSTOM  = "#7090d0"
PURPLE  = "#b07aff"

# ── Map paths — edit if your filenames differ ─────────────────────────────────
# Defaults to the maps/ folder of this repo; override with env vars on the robot.
import os
_MAPS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "maps")
MAP_FULL    = os.environ.get("MAP_FULL",    os.path.normpath(os.path.join(_MAPS, "map2kareem.yaml")))
MAP_KEEPOUT = os.environ.get("MAP_KEEPOUT", os.path.normpath(os.path.join(_MAPS, "map3kareemkeepout.yaml")))

# ── Preset waypoints ──────────────────────────────────────────────────────────
WAYPOINTS = [
    {"name": "Waypoint 1", "x":  0.720, "y":  0.495,  "z": 0.0, "w": 1.0},
    {"name": "Waypoint 2", "x":  0.306, "y":  0.0567, "z": 0.0, "w": 1.0},
    {"name": "Waypoint 3", "x":  0.799, "y": -0.339,  "z": 0.0, "w": 1.0},
]

# ── Shell commands ────────────────────────────────────────────────────────────
SETUP       = "source /opt/ros/humble/setup.bash && export TURTLEBOT3_MODEL=burger"
CMD_BRINGUP = f"{SETUP} && ros2 launch turtlebot3_bringup robot.launch.py"

def cmd_nav2(map_path):
    return (
        f"{SETUP} && "
        f"ros2 launch turtlebot3_navigation2 navigation2.launch.py "
        f"map:={map_path} use_sim_time:=false"
    )

def launch_terminal(title, cmd):
    """Open a new gnome-terminal. Falls back to xterm."""
    try:
        subprocess.Popen([
            "gnome-terminal", f"--title={title}", "--", "bash", "-c",
            f"{cmd}; echo; echo '[ process ended ]'; exec bash"
        ])
        return True
    except FileNotFoundError:
        pass
    try:
        subprocess.Popen([
            "xterm", "-title", title, "-e",
            f"bash -c '{cmd}; echo; echo [done]; exec bash'"
        ])
        return True
    except FileNotFoundError:
        return False


def make_pose(nav, x, y, z=0.0, w=1.0):
    pose = PoseStamped()
    pose.header.frame_id    = "map"
    pose.header.stamp       = nav.get_clock().now().to_msg()
    pose.pose.position.x    = x
    pose.pose.position.y    = y
    pose.pose.orientation.z = z
    pose.pose.orientation.w = w
    return pose


# ══════════════════════════════════════════════════════════════════════════════
class BurgerGUI:

    def __init__(self, root, navigator: BasicNavigator):
        self.root      = root
        self.navigator = navigator
        self._busy     = False
        self._nav2_ready = False
        self._map_var  = tk.StringVar(value="full")

        self.root.title("TB3 Burger  ·  ROS2 Humble  ·  Nav2")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self._build_ui()

        # Nav buttons start locked — unlocked once Nav2 is active
        self._lock_nav(reason="Launch Nav2 first to enable navigation")

        self._log("GUI opened — no terminals needed from here", "ok")
        self._log("Step 1 → Bringup   Step 2 → Launch Nav2   Step 3 → Navigate", "info")

        # Start background thread waiting for Nav2 to become active
        threading.Thread(target=self._wait_for_nav2, daemon=True).start()

    # =========================================================================
    # Wait for Nav2 in background — unlocks GUI when ready
    # =========================================================================
    def _wait_for_nav2(self):
        """Blocking call runs in background. GUI stays responsive."""
        try:
            self.navigator.waitUntilNav2Active()
            self._nav2_ready = True
            self.root.after(0, self._on_nav2_ready)
        except Exception as e:
            self.root.after(0, self._log, f"Nav2 error: {e}", "err")

    def _on_nav2_ready(self):
        self._unlock_nav()
        self._log("Nav2 is active ✓  Ready to navigate!", "ok")
        self.banner.config(text="Nav2 Active — Select a destination", fg=ACCENT)
        self.status_dot.config(text="●  NAV2 ACTIVE", fg=ACCENT)
        # Mark nav2 button as done
        self.nav2_btn.config(text="ACTIVE ✓", fg=DIM, state=tk.DISABLED)

    # =========================================================================
    # UI build
    # =========================================================================
    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=PANEL, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="TB3 ", font=("Courier", 16, "bold"),
                 fg=ACCENT, bg=PANEL).pack(side="left", padx=(20, 0), pady=10)
        tk.Label(hdr, text="BURGER  ·  ROS2 HUMBLE  ·  NAV2",
                 font=("Courier", 10), fg=DIM, bg=PANEL).pack(side="left")

        self.status_dot = tk.Label(hdr, text="●  WAITING FOR NAV2",
                                   font=("Courier", 10, "bold"),
                                   fg=WARN, bg=PANEL)
        self.status_dot.pack(side="right", padx=20)

        # ── Body ──────────────────────────────────────────────────────────────
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=14)

        # Status banner
        self.banner = tk.Label(body,
                               text="Launch bringup and Nav2 below, then navigate",
                               font=("Courier", 12),
                               fg=WARN, bg=PANEL,
                               pady=12, relief="flat",
                               highlightthickness=1,
                               highlightbackground=BORDER)
        self.banner.pack(fill="x", pady=(0, 14))

        # ── STEP 1 — Bringup ─────────────────────────────────────────────────
        self._section(body, "STEP 1  ·  ROBOT BRINGUP")

        c1 = self._card(body, ACCENT)
        i1 = tk.Frame(c1, bg=PANEL); i1.pack(fill="x", padx=14, pady=12)

        lf = tk.Frame(i1, bg=PANEL); lf.pack(side="left", fill="x", expand=True)
        tk.Label(lf, text="BRINGUP",
                 font=("Courier", 12, "bold"), fg=ACCENT, bg=PANEL).pack(anchor="w")
        tk.Label(lf, text="ros2 launch turtlebot3_bringup robot.launch.py",
                 font=("Courier", 8), fg=DIM, bg=PANEL).pack(anchor="w", pady=(2, 0))

        self.bringup_btn = tk.Button(i1, text="LAUNCH  ▶",
                                     font=("Courier", 11, "bold"),
                                     fg=ACCENT, bg=DARK,
                                     activeforeground=ACCENT, activebackground=PANEL,
                                     relief="flat", highlightthickness=1,
                                     highlightbackground=ACCENT,
                                     padx=14, pady=6, cursor="hand2",
                                     command=self._launch_bringup)
        self.bringup_btn.pack(side="right")

        # ── STEP 2 — Nav2 ────────────────────────────────────────────────────
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(12, 10))
        self._section(body, "STEP 2  ·  LAUNCH NAV2")

        c2 = self._card(body, PURPLE)
        i2 = tk.Frame(c2, bg=PANEL); i2.pack(fill="x", padx=14, pady=12)

        lf2 = tk.Frame(i2, bg=PANEL); lf2.pack(side="left", fill="x", expand=True)
        tk.Label(lf2, text="SELECT MAP",
                 font=("Courier", 12, "bold"), fg=PURPLE, bg=PANEL).pack(anchor="w")

        radio_row = tk.Frame(lf2, bg=PANEL); radio_row.pack(anchor="w", pady=(6, 0))
        rstyle = dict(font=("Courier", 10), bg=PANEL,
                      activebackground=PANEL, cursor="hand2", selectcolor=DARK)

        tk.Radiobutton(radio_row, text="Full Map",
                       variable=self._map_var, value="full",
                       fg=TEXT, **rstyle).pack(side="left", padx=(0, 16))
        tk.Radiobutton(radio_row, text="Keepout Zones",
                       variable=self._map_var, value="keepout",
                       fg=WARN, **rstyle).pack(side="left")

        self.map_path_lbl = tk.Label(lf2, text=f"  {MAP_FULL}",
                                     font=("Courier", 8), fg=DIM, bg=PANEL)
        self.map_path_lbl.pack(anchor="w", pady=(4, 0))
        self._map_var.trace_add("write", self._update_map_label)

        self.nav2_btn = tk.Button(i2, text="LAUNCH  ▶",
                                  font=("Courier", 11, "bold"),
                                  fg=PURPLE, bg=DARK,
                                  activeforeground=PURPLE, activebackground=PANEL,
                                  relief="flat", highlightthickness=1,
                                  highlightbackground=PURPLE,
                                  padx=14, pady=6, cursor="hand2",
                                  command=self._launch_nav2)
        self.nav2_btn.pack(side="right")

        # ── STEP 3 — Preset waypoints ─────────────────────────────────────────
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(12, 10))
        self._section(body, "STEP 3  ·  NAVIGATE TO PRESET WAYPOINT")

        self._wp_buttons = []
        for i, wp in enumerate(WAYPOINTS):
            self._wp_buttons.append(self._make_wp_btn(body, wp, i))

        # ── Custom coordinates ────────────────────────────────────────────────
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(12, 10))
        self._section(body, "CUSTOM COORDINATES")

        c3 = self._card(body, CUSTOM)
        i3 = tk.Frame(c3, bg=PANEL); i3.pack(fill="x", padx=14, pady=12)

        tk.Label(i3, text="X", font=("Courier", 11, "bold"),
                 fg=TEXT, bg=PANEL, width=2).pack(side="left")
        self.custom_x = tk.Entry(i3, font=("Courier", 11),
                                 bg=DARK, fg=TEXT, insertbackground=CUSTOM,
                                 relief="flat", highlightthickness=1,
                                 highlightbackground=BORDER, highlightcolor=CUSTOM,
                                 width=10)
        self.custom_x.pack(side="left", padx=(4, 18), ipady=6)

        tk.Label(i3, text="Y", font=("Courier", 11, "bold"),
                 fg=TEXT, bg=PANEL, width=2).pack(side="left")
        self.custom_y = tk.Entry(i3, font=("Courier", 11),
                                 bg=DARK, fg=TEXT, insertbackground=CUSTOM,
                                 relief="flat", highlightthickness=1,
                                 highlightbackground=BORDER, highlightcolor=CUSTOM,
                                 width=10)
        self.custom_y.pack(side="left", padx=(4, 18), ipady=6)

        self.custom_go_btn = tk.Button(i3, text="GO  ▶",
                                       font=("Courier", 11, "bold"),
                                       fg=CUSTOM, bg=DARK,
                                       activeforeground=CUSTOM, activebackground=PANEL,
                                       relief="flat", highlightthickness=1,
                                       highlightbackground="#2a3a5e",
                                       padx=16, pady=6, cursor="hand2",
                                       command=self._navigate_custom)
        self.custom_go_btn.pack(side="left")

        self.custom_x.bind("<Return>", lambda e: self.custom_y.focus())
        self.custom_y.bind("<Return>", lambda e: self._navigate_custom())
        self._custom_widgets = [self.custom_x, self.custom_y, self.custom_go_btn]

        # ── Log ───────────────────────────────────────────────────────────────
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(12, 8))
        tk.Label(body, text="SYSTEM LOG",
                 font=("Courier", 9), fg=DIM, bg=BG).pack(anchor="w")

        lf = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        lf.pack(fill="both", expand=True, pady=(4, 0))

        self.log_text = tk.Text(lf, font=("Courier", 9), bg=PANEL, fg=TEXT,
                                relief="flat", state="disabled", wrap="word",
                                height=6, padx=12, pady=8)
        self.log_text.pack(fill="both", expand=True)

        for tag, col in [("ok", ACCENT), ("warn", WARN), ("err", DANGER),
                         ("info", DIM), ("dim", DIM)]:
            self.log_text.tag_config(tag, foreground=col)

    # ── Widget helpers ────────────────────────────────────────────────────────
    def _section(self, parent, text):
        tk.Label(parent, text=text,
                 font=("Courier", 9), fg=DIM, bg=BG).pack(anchor="w", pady=(0, 4))

    def _card(self, parent, col):
        f = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=col)
        f.pack(fill="x", pady=(0, 4))
        return f

    def _make_wp_btn(self, parent, wp, idx):
        colors = [ACCENT, WARN, "#00b4ff"]
        col    = colors[idx % len(colors)]

        outer = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=col)
        outer.pack(fill="x", pady=3)
        inner = tk.Frame(outer, bg=PANEL); inner.pack(fill="x", padx=14, pady=10)

        lf = tk.Frame(inner, bg=PANEL); lf.pack(side="left", fill="x", expand=True)
        tk.Label(lf, text=wp["name"].upper(),
                 font=("Courier", 12, "bold"), fg=col, bg=PANEL).pack(anchor="w")
        tk.Label(lf, text=f"x = {wp['x']}   y = {wp['y']}",
                 font=("Courier", 9), fg=DIM, bg=PANEL).pack(anchor="w", pady=(2, 0))

        btn = tk.Button(inner, text="GO  ▶",
                        font=("Courier", 11, "bold"),
                        fg=col, bg=DARK,
                        activeforeground=col, activebackground=PANEL,
                        relief="flat", highlightthickness=1,
                        highlightbackground=col,
                        padx=16, pady=6, cursor="hand2",
                        command=lambda w=wp: self._navigate(w))
        btn.pack(side="right")
        return btn

    # =========================================================================
    # Lock / unlock nav section
    # =========================================================================
    def _lock_nav(self, reason=""):
        for btn in getattr(self, "_wp_buttons", []):
            btn.config(state=tk.DISABLED, fg=DIM)
        for w in getattr(self, "_custom_widgets", []):
            w.config(state=tk.DISABLED)
        if reason:
            self._log(reason, "warn")

    def _unlock_nav(self):
        colors = [ACCENT, WARN, "#00b4ff"]
        for i, btn in enumerate(self._wp_buttons):
            btn.config(state=tk.NORMAL, fg=colors[i % len(colors)])
        for w in self._custom_widgets:
            w.config(state=tk.NORMAL)

    # =========================================================================
    # Launchers
    # =========================================================================
    def _update_map_label(self, *_):
        path = MAP_FULL if self._map_var.get() == "full" else MAP_KEEPOUT
        self.map_path_lbl.config(text=f"  {path}")

    def _launch_bringup(self):
        self._log("Opening bringup terminal…", "info")
        if launch_terminal("TB3 Bringup", CMD_BRINGUP):
            self._log("Bringup terminal opened ✓", "ok")
            self.bringup_btn.config(text="LAUNCHED ✓", state=tk.DISABLED, fg=DIM)
        else:
            self._log("ERROR: gnome-terminal / xterm not found", "err")

    def _launch_nav2(self):
        choice   = self._map_var.get()
        path     = MAP_FULL if choice == "full" else MAP_KEEPOUT
        label    = "Full Map" if choice == "full" else "Keepout Map"

        self._log(f"Opening Nav2 terminal ({label})…", "info")
        self._log(f"  {path}", "dim")

        if launch_terminal(f"TB3 Nav2 — {label}", cmd_nav2(path)):
            self._log("Nav2 terminal opened ✓", "ok")
            self._log("Waiting for Nav2 to become active — nav buttons will unlock automatically…", "info")
            self.nav2_btn.config(text="WAITING…", state=tk.DISABLED, fg=WARN)
            self.status_dot.config(text="●  WAITING FOR NAV2", fg=WARN)
        else:
            self._log("ERROR: gnome-terminal / xterm not found", "err")

    # =========================================================================
    # Navigation
    # =========================================================================
    def _navigate(self, wp):
        if self._busy:
            self._log("Already navigating — please wait", "warn"); return
        self._set_busy(True, label=wp["name"])
        threading.Thread(target=self._nav_thread,
                         args=(wp["x"], wp["y"], wp["z"], wp["w"], wp["name"]),
                         daemon=True).start()

    def _navigate_custom(self):
        if self._busy:
            self._log("Already navigating — please wait", "warn"); return
        try:
            x = float(self.custom_x.get().strip())
            y = float(self.custom_y.get().strip())
        except ValueError:
            self._log("Invalid coordinates — numbers only", "err")
            self.custom_x.config(highlightbackground=DANGER)
            self.custom_y.config(highlightbackground=DANGER)
            self.root.after(1500, lambda: (
                self.custom_x.config(highlightbackground=BORDER),
                self.custom_y.config(highlightbackground=BORDER)))
            return

        name = f"Custom ({x:.3f}, {y:.3f})"
        self._set_busy(True, label=name)
        threading.Thread(target=self._nav_thread,
                         args=(x, y, 0.0, 1.0, name),
                         daemon=True).start()

    def _nav_thread(self, x, y, z, w, name):
        self.root.after(0, self._log, f"Navigating → {name}  ({x}, {y})", "info")
        pose = make_pose(self.navigator, x, y, z, w)
        self.navigator.goToPose(pose)

        while not self.navigator.isTaskComplete():
            pass

        result = self.navigator.getResult()
        if result == TaskResult.SUCCEEDED:
            msg, tag, text = f"Reached {name} ✓", "ok", f"Arrived at {name}"
        else:
            msg, tag, text = f"Failed to reach {name}", "err", "Navigation failed"

        self.root.after(0, self._log, msg, tag)
        self.root.after(0, self._set_busy, False, None, text)

    # =========================================================================
    # State helpers
    # =========================================================================
    def _set_busy(self, busy, label=None, done_text=None):
        self._busy = busy
        if busy:
            self.banner.config(text=f"Navigating to {label}…", fg=WARN)
            self.status_dot.config(text="●  NAVIGATING", fg=WARN)
            for btn in self._wp_buttons:
                btn.config(state=tk.DISABLED)
            for w in self._custom_widgets:
                w.config(state=tk.DISABLED)
        else:
            self.banner.config(text=done_text or "Select a destination", fg=ACCENT)
            self.status_dot.config(text="●  NAV2 ACTIVE", fg=ACCENT)
            for btn in self._wp_buttons:
                btn.config(state=tk.NORMAL)
            for w in self._custom_widgets:
                w.config(state=tk.NORMAL)

    def _log(self, msg, tag="info"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"{ts}  ", "dim")
        self.log_text.insert("end", msg + "\n", tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")


# ══════════════════════════════════════════════════════════════════════════════
def main():
    # Init ROS2 — fast, non-blocking
    rclpy.init()
    navigator = BasicNavigator()

    # Spin executor in background
    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(navigator)
    threading.Thread(target=executor.spin, daemon=True).start()

    # Open GUI immediately — no waiting here
    root = tk.Tk()
    BurgerGUI(root, navigator)

    try:
        root.mainloop()
    finally:
        executor.shutdown()
        navigator.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
