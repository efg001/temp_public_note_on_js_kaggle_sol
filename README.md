import tkinter as tk
import threading
import mss
import cv2
import numpy as np
import keyboard as kb
import pyautogui
import time
from pynput import mouse, keyboard as pynkeyboard

# ------------------ AUTO CLICKER RECORDER ------------------
class AutoClickerRecorder:
    def __init__(self, repeat_count, hotkey_record, hotkey_replay):
        self.repeat_count = repeat_count
        self.hotkey_record = hotkey_record
        self.hotkey_replay = hotkey_replay

        self.actions = []
        self.recording = False
        self.replaying = False
        self.mouse_listener = None
        self.keyboard_listener = None
        self.stop_record_flag = threading.Event()
        self.stop_replay_flag = threading.Event()

    def start_recording(self):
        if self.recording: return
        print("[AutoClicker] Start recording actions")
        self.recording = True
        self.actions = []
        self.start_time = time.time()
        self.stop_record_flag.clear()

        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        self.keyboard_listener = pynkeyboard.Listener(on_press=self.on_press)

        self.mouse_listener.start()
        self.keyboard_listener.start()

    def stop_recording(self):
        if not self.recording: return
        print("[AutoClicker] Stop recording actions")
        self.recording = False
        self.stop_record_flag.set()

        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None

    def on_click(self, x, y, button, pressed):
        if not self.recording or not pressed:
            return
        event_time = time.time() - self.start_time
        self.actions.append(('mouse', event_time, x, y, button.name))

    def on_press(self, key):
        if not self.recording:
            return
        event_time = time.time() - self.start_time
        try:
            k = key.char
        except AttributeError:
            k = str(key)
        self.actions.append(('key', event_time, k))

    def start_replay(self):
        if self.replaying or not self.actions:
            return
        print("[AutoClicker] Start replay actions")
        self.replaying = True
        self.stop_replay_flag.clear()
        t = threading.Thread(target=self._replay)
        t.start()

    def stop_replay(self):
        if not self.replaying:
            return
        print("[AutoClicker] Stop replay actions")
        self.replaying = False
        self.stop_replay_flag.set()

    def _replay(self):
        count = 0
        max_times = self.repeat_count if self.repeat_count > 0 else float('inf')
        while self.replaying and count < max_times and not self.stop_replay_flag.is_set():
            t0 = time.time()
            for event in self.actions:
                if not self.replaying or self.stop_replay_flag.is_set():
                    break
                if event[0] == 'mouse':
                    _, event_time, x, y, button = event
                    delay = event_time - (time.time() - t0)
                    if delay > 0: time.sleep(delay)
                    pyautogui.click(x, y, button=button)
                elif event[0] == 'key':
                    _, event_time, k = event
                    delay = event_time - (time.time() - t0)
                    if delay > 0: time.sleep(delay)
                    # For special keys, check if single-letter or not
                    if len(str(k)) == 1:
                        pyautogui.press(k)
            count += 1

# ------------------ SCREEN RECORDER ------------------
class ScreenRecorder:
    def __init__(self):
        self.recording = False
        self.thread = None

    def start_recording(self, filename="recording.mp4"):
        if self.recording:
            return
        self.recording = True
        self.filename = filename
        self.thread = threading.Thread(target=self.record_screen, daemon=True)
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

# ------------------ MAIN TKINTER APP ------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Auto Clicker & Screen Recorder")
        self.geometry("350x260")

        # Hold settings data as tk.StringVars
        self.data = {
            "repeat_count": tk.StringVar(value="1"),
            "hotkey_record": tk.StringVar(value="F9"),
            "hotkey_replay": tk.StringVar(value="F8"),
            "screen_hotkey_record": tk.StringVar(value="F11"),
            "screen_hotkey_stop": tk.StringVar(value="F12"),
        }

        self._build_gui()
        self.recorder = ScreenRecorder()
        self.clicker = AutoClickerRecorder(repeat_count=1, hotkey_record="F9", hotkey_replay="F8")
        self.hotkey_refs = []
        self.after(10, self._bind_hotkeys) # allow UI to init first

    def _build_gui(self):
        # Repeat Setting
        tk.Label(self, text="Repeat count (0 = Forever):").pack()
        tk.Entry(self, textvariable=self.data['repeat_count']).pack()

        # Hotkeys for auto clicker
        tk.Label(self, text="Hotkey: Start/Stop Action Recording").pack()
        tk.Entry(self, textvariable=self.data['hotkey_record']).pack()
        tk.Label(self, text="Hotkey: Start/Stop Replay Actions").pack()
        tk.Entry(self, textvariable=self.data['hotkey_replay']).pack()
        # Hotkeys for screen recording
        tk.Label(self, text="Hotkey: Start Screen Recording").pack()
        tk.Entry(self, textvariable=self.data['screen_hotkey_record']).pack()
        tk.Label(self, text="Hotkey: Stop Screen Recording").pack()
        tk.Entry(self, textvariable=self.data['screen_hotkey_stop']).pack()

        tk.Button(self, text="Apply Settings", command=self.apply_settings).pack(pady=9)

        tk.Label(self, text="Or click manually below:").pack()
        tk.Button(self, text="Start Screen Recording", command=self.start_screen_recording).pack()
        tk.Button(self, text="Stop Screen Recording", command=self.stop_screen_recording).pack()

    def apply_settings(self):
        try:
            repeat = int(self.data["repeat_count"].get())
        except:
            repeat = 1
        self.clicker.repeat_count = repeat
        self.clicker.hotkey_record = self.data["hotkey_record"].get()
        self.clicker.hotkey_replay = self.data["hotkey_replay"].get()

        self._unbind_hotkeys()
        self._bind_hotkeys()
        print("Settings applied")

    def _unbind_hotkeys(self):
        for ref in self.hotkey_refs:
            kb.remove_hotkey(ref)
        self.hotkey_refs = []

    def _bind_hotkeys(self):
        # Action record hotkey:
        record_hotkey = self.data['hotkey_record'].get()
        replay_hotkey = self.data['hotkey_replay'].get()
        screen_start = self.data['screen_hotkey_record'].get()
        screen_stop = self.data['screen_hotkey_stop'].get()

        # Safe: can add handler multiple times, will overwrite (if not, that's why we keep `hotkey_refs`)
        self.hotkey_refs.append(kb.add_hotkey(record_hotkey, self._cb_toggle_action_record))
        self.hotkey_refs.append(kb.add_hotkey(replay_hotkey, self._cb_toggle_replay))
        self.hotkey_refs.append(kb.add_hotkey(screen_start, self.start_screen_recording))
        self.hotkey_refs.append(kb.add_hotkey(screen_stop, self.stop_screen_recording))
        print("Hotkeys applied")

    # --- Auto Clicker handlers ---
    def _cb_toggle_action_record(self):
        if self.clicker.recording:
            self.clicker.stop_recording()
        else:
            self.clicker.start_recording()

    def _cb_toggle_replay(self):
        if self.clicker.replaying:
            self.clicker.stop_replay()
        else:
            self.clicker.start_replay()

    # --- Screen record handlers ---
    def start_screen_recording(self):
        if not self.recorder.recording:
            self.recorder.start_recording()

    def stop_screen_recording(self):
        if self.recorder.recording:
            self.recorder.stop_recording()

if __name__ == "__main__":
    app = App()
    app.mainloop()
