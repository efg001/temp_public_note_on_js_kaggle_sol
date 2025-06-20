




# Download and Install latest Python 3 (64-bit/Intel) + dependencies for screen recorder

function Get-LatestPythonVersion {
    $index = Invoke-WebRequest "https://www.python.org/ftp/python/" -UseBasicParsing
    $versions = ($index.Links | Where-Object href -match "^\d+\.\d+\.\d+/$").href |
        ForEach-Object { $_.TrimEnd('/') } |
        Where-Object { $_ -match "^\d+\.\d+\.\d+$" } |
        Sort-Object { [version]$_ } -Descending
    return $versions[0]
}

# Main
$ErrorActionPreference = "Stop"
Write-Host "Locating latest Python 3 (64-bit) release..."
$latest = Get-LatestPythonVersion
Write-Host "Latest version found: $latest"

$exe = "python-$latest-amd64.exe"
$url = "https://www.python.org/ftp/python/$latest/$exe"
$outfile = "$env:TEMP\$exe"

Write-Host "Downloading: $url"
Invoke-WebRequest -Uri $url -OutFile $outfile

Write-Host "Running Python installer silently (per-user, add to PATH)..."
Start-Process -FilePath $outfile -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0" -Wait

Remove-Item $outfile

# Find python path for user install
$pythonDir = "$env:LOCALAPPDATA\Programs\Python"
$pyExe = Get-ChildItem -Path $pythonDir -Recurse -Include "python.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $pyExe) {
    Write-Error "Python was not installed. Exiting."
    exit 1
}
$pythonPath = $pyExe.FullName

# Optionally reload environment
$env:PATH += ";$($pyExe.DirectoryName);$($pyExe.DirectoryName)\Scripts"

Write-Host "Upgrading pip (package installer)..."
& $pythonPath -m pip install --upgrade pip

Write-Host "Installing dependencies: mss, opencv-python, keyboard, numpy"
& $pythonPath -m pip install mss opencv-python keyboard numpy

Write-Host "`nSetup complete! You may now run your Python screen recorder script."



import tkinter as tk
import threading
import mss
import cv2
import numpy as np
import keyboard
import pyautogui
import time
import queue
from pynput import mouse, keyboard as pynkeyboard

class AutoClickerRecorder:
    def __init__(self, repeat_count, hotkey_record, hotkey_replay):
        self.repeat_count = repeat_count
        self.hotkey_record = hotkey_record
        self.hotkey_replay = hotkey_replay

        self.actions = []
        self.recording = False
        self.replaying = False
        self.recorder_thread = None
        self.replay_thread = None
        self.start_time = None

    def start_recording(self):
        if self.recording:
            return
        print("[AutoClicker] Start recording actions")
        self.recording = True
        self.actions = []
        self.start_time = time.time()

        mouse_listener = mouse.Listener(on_click=self.on_click)
        keyboard_listener = pynkeyboard.Listener(on_press=self.on_key)

        self.mouse_listener = mouse_listener
        self.keyboard_listener = keyboard_listener

        mouse_listener.start()
        keyboard_listener.start()
        self.recording_threads = [mouse_listener, keyboard_listener]

    def stop_recording(self):
        if not self.recording:
            return
        print("[AutoClicker] Stopped recording actions")
        self.recording = False
        for listener in self.recording_threads:
            listener.stop()

    def on_click(self, x, y, button, pressed):
        if not self.recording: return
        if pressed:
            event_time = time.time() - self.start_time
            self.actions.append(('mouse', event_time, x, y, button.name))

    def on_key(self, key):
        if not self.recording: return
        event_time = time.time() - self.start_time
        try:
            k = key.char
        except AttributeError:
            k = str(key)
        self.actions.append(('key', event_time, k))

    def start_replay(self):
        if self.replaying or not self.actions:
            return
        print("[AutoClicker] Start replaying actions")
        self.replaying = True
        self.replay_thread = threading.Thread(target=self.replay)
        self.replay_thread.start()

    def stop_replay(self):
        print("[AutoClicker] Stopped replaying actions")
        self.replaying = False

    def replay(self):
        times = self.repeat_count if self.repeat_count > 0 else float('inf')
        for _ in range(int(times)):
            if not self.replaying:
                break
            t0 = time.time()
            for event in self.actions:
                if not self.replaying:
                    break
                if event[0] == 'mouse':
                    _, event_time, x, y, button = event
                    to_wait = event_time - (time.time() - t0)
                    if to_wait > 0:
                        time.sleep(to_wait)
                    pyautogui.click(x, y, button=button)
                elif event[0] == 'key':
                    _, event_time, k = event
                    to_wait = event_time - (time.time() - t0)
                    if to_wait > 0:
                        time.sleep(to_wait)
                    pyautogui.press(k)

# --------- SCREEN RECORDER ---------
class ScreenRecorder:
    def __init__(self):
        self.recording = False
        self.thread = None

    def start_recording(self, filename="recording.mp4"):
        if self.recording:
            return
        self.recording = True
        self.filename = filename
        self.thread = threading.Thread(target=self.record_screen)
        self.thread.start()

    def stop_recording(self):
        self.recording = False

    def record_screen(self):
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            width, height = monitor['width'], monitor['height']
            out = cv2.VideoWriter(self.filename, fourcc, 20, (width, height))
            while self.recording:
                img = np.array(sct.grab(monitor))
                frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                out.write(frame)
                time.sleep(1 / 20)
            out.release()

# ------- GUI PART -----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Auto Clicker & Screen Recorder")
        self.geometry("350x250")

        self.data = {
            "repeat_count": tk.StringVar(value="1"),
            "hotkey_record": tk.StringVar(value="F9"),
            "hotkey_replay": tk.StringVar(value="F8"),
        }

        self._build_gui()
        self.recorder = ScreenRecorder()
        self.clicker = AutoClickerRecorder(repeat_count=1, hotkey_record='F9', hotkey_replay='F8')

        self._bind_hotkeys()

    def _build_gui(self):
        # Repeat Setting
        tk.Label(self, text="Repeat Count: (0 = Forever)").pack(pady=5)
        tk.Entry(self, textvariable=self.data['repeat_count']).pack()

        # Hotkey for Recording
        tk.Label(self, text="Hotkey: Start/Stop Action Recording").pack(pady=5)
        tk.Entry(self, textvariable=self.data['hotkey_record']).pack()

        # Hotkey for Replay
        tk.Label(self, text="Hotkey: Start/Stop Replay Actions").pack(pady=5)
        tk.Entry(self, textvariable=self.data['hotkey_replay']).pack()

        tk.Button(self, text="Apply Settings", command=self.apply_settings).pack(pady=10)

        # Buttons to Start/Stop only for screen record
        tk.Button(self, text="Start Screen Recording", command=self.start_screen_recording).pack(pady=2)
        tk.Button(self, text="Stop Screen Recording", command=self.stop_screen_recording).pack(pady=2)

    def apply_settings(self):
        repeat = self.data["repeat_count"].get()
        try:
            repeat = int(repeat)
        except:
            repeat = 1
        hotkey_record = self.data["hotkey_record"].get()
        hotkey_replay = self.data["hotkey_replay"].get()
        self.clicker.repeat_count = repeat
        self.clicker.hotkey_record = hotkey_record
        self.clicker.hotkey_replay = hotkey_replay
        self._unregister_hotkeys()
        self._bind_hotkeys()
        print("[GUI] Settings applied")

    def _unregister_hotkeys(self):
        keyboard.unhook_all_hotkeys()

    def _bind_hotkeys(self):
        # Action Record hotkey
        keyboard.add_hotkey(self.data['hotkey_record'].get(), self.toggle_action_record)
        # Action Replay hotkey
        keyboard.add_hotkey(self.data['hotkey_replay'].get(), self.toggle_replay)

    def toggle_action_record(self):
        if self.clicker.recording:
            self.clicker.stop_recording()
        else:
            self.clicker.start_recording()

    def toggle_replay(self):
        if self.clicker.replaying:
            self.clicker.stop_replay()
        else:
            self.clicker.start_replay()

    def start_screen_recording(self):
        self.recorder.start_recording()

    def stop_screen_recording(self):
        self.recorder.stop_recording()

if __name__ == "__main__":
    app = App()
    app.mainloop()
