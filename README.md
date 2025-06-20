




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
from tkinter import messagebox
import threading
import mss
import cv2
import numpy as np
import keyboard
import os
import time
import sys
import subprocess

recording = False
playing = False
video_filename = "screen_record.avi"
repeat_setting = 1    # default 1 (set via GUI)

def record_screen():
    global recording, video_filename
    with mss.mss() as sct:
        mon = sct.monitors[1]
        width, height = mon["width"], mon["height"]
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter(video_filename, fourcc, 20.0, (width, height))
        print("Recording started. Press F9 to stop.")
        while recording:
            img = np.array(sct.grab(mon))
            frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            out.write(frame)
            cv2.waitKey(1)
        out.release()
    print("Recording stopped. File saved as:", video_filename)

def get_video_length(filepath):
    cap = cv2.VideoCapture(filepath)
    fps = cap.get(cv2.CAP_PROP_FPS) or 20
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    duration = frame_count / fps
    return duration

def playback_video(repeat):
    global playing, video_filename
    print(f"Playback started! Repeat: {'infinite' if repeat==0 else repeat} (Press F10 to stop).")
    count = 0
    while playing and (repeat == 0 or count < repeat):
        try:
            os.startfile(video_filename)
        except AttributeError:
            subprocess.run(['open', video_filename])
        except Exception as ex:
            print("Failed to start playback:", ex)
            break
        wait_time = get_video_length(video_filename)
        t0 = time.time()
        while playing and (time.time() - t0 < wait_time):
            time.sleep(0.2)
        count += 1
    print("Playback stopped.")

def hotkey_listener():
    global recording, playing, repeat_setting
    rec_thread = None
    play_thread = None
    while True:
        if keyboard.is_pressed('F9'):
            if not recording and not playing:
                recording = True
                rec_thread = threading.Thread(target=record_screen, daemon=True)
                rec_thread.start()
                show_message("Recording started! Press F9 again to stop.")
                while keyboard.is_pressed('F9'):
                    time.sleep(0.1)
            elif recording:
                recording = False
                if rec_thread:
                    rec_thread.join()
                show_message("Recording stopped!")
                while keyboard.is_pressed('F9'):
                    time.sleep(0.1)
        if keyboard.is_pressed('F10'):
            if not playing and os.path.exists(video_filename) and not recording:
                playing = True
                play_thread = threading.Thread(target=playback_video, args=(repeat_setting,), daemon=True)
                play_thread.start()
                show_message("Playback started! Press F10 to stop.")
                while keyboard.is_pressed('F10'):
                    time.sleep(0.1)
            elif playing:
                playing = False
                if play_thread:
                    play_thread.join()
                show_message("Playback stopped!")
                while keyboard.is_pressed('F10'):
                    time.sleep(0.1)
        time.sleep(0.15)

def show_message(msg):
    try:
        # Thread-safe popup
        root.after(0, lambda: messagebox.showinfo("Info", msg))
    except Exception:
        pass

def on_apply():
    global repeat_setting
    val = entry_repeat.get()
    try:
        rc = int(val)
        if rc < 0: raise ValueError()
        repeat_setting = rc
        show_message(
            "Settings applied!\n\n"
            "F9: Start/stop recording\n"
            "F10: Start/stop playing\n"
            "Minimize or close this window and use hotkeys."
        )
        root.iconify()
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid repeat count (0 = infinite, or higher).")

def on_exit():
    root.destroy()
    sys.exit(0)

# --- GUI Setup ---
root = tk.Tk()
root.title("Screen Recorder Settings")
root.resizable(False, False)
tk.Label(root, text="Screen Recorder Settings (minimize and use hotkeys)").pack(padx=10, pady=(10,2))
frame_row = tk.Frame(root)
frame_row.pack(pady=(0,5))

tk.Label(frame_row, text="Repeat count for playback:").pack(side='left', padx=(0,5))
entry_repeat = tk.Entry(frame_row, width=6)
entry_repeat.insert(0, str(repeat_setting))
entry_repeat.pack(side='left')
tk.Label(frame_row, text="(0 = infinite)").pack(side='left', padx=(5,2))
btn_apply = tk.Button(root, text="Apply & Minimize", command=on_apply)
btn_exit = tk.Button(root, text="Exit", command=on_exit)
btn_apply.pack(side='left', padx=(20,5), pady=10)
btn_exit.pack(side='right', padx=(5,20), pady=10)

# --- Start hotkey listener ---
listener_thread = threading.Thread(target=hotkey_listener, daemon=True)
listener_thread.start()

# ---- Run the main window ----
root.mainloop()
