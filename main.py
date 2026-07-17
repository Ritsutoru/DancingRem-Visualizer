import tkinter as tk
from PIL import Image, ImageTk
import pyaudiowpatch as pyaudio
import numpy as np
import threading
import time
import os
import sys
import webbrowser

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Главные настройки \\ Main Settings

gifPath = resource_path(os.path.join('Resources', 'remDance.gif'))

gifWidth = 150
gifHeight = 270

aboutPath = resource_path(os.path.join('Resources', 'logo.jpg'))
aboutWidth = 140
aboutHeight = 140
aboutTitle = 'DancingRem!'

if not os.path.exists(gifPath):
    raise FileNotFoundError(f"GIF not found: {gifPath}")

if not os.path.exists(aboutPath):
    raise FileNotFoundError(f"Logo not found: {aboutPath}")

settingSize = (250, 100)
aboutSize = (300, 330)

audioThreshold = 0.003
idleTimeout = 10.0  # Время ожидания перед анимацией ожидания (да)
idleDanceDelay = 600  # Скорость анимации ожидания

# Главные настройки закончились :)

class SystemSoundPet:
    def __init__(self, root, gifPath):
        self.root = root
        self.frames = []
        self.current_frame = 0

        self.volume = 0.0
        self.smoothed_volume = 0.0
        self.is_dancing = False
        self.last_sound_time = time.time()

        self.speed_multiplier = 1.0
        self.settings_window = None
        self.about_window = None

        self.min_delay_base = 150
        self.max_delay_base = 350

        self.base_x = 300
        self.base_y = 300

        root.overrideredirect(True)
        root.attributes('-topmost', True)
        root.attributes('-transparentcolor', 'black')
        root.configure(bg='black')
        root.geometry(f'+{self.base_x}+{self.base_y}')

        self.load_gif(gifPath)

        self.label = tk.Label(root, image=self.frames[0], bg='black', bd=0)
        self.label.pack()

        self.label.bind('<Button-1>', self.start_drag)
        self.label.bind('<B1-Motion>', self.drag)

        self.create_context_menu()
        self.label.bind('<Button-3>', self.show_context_menu)

        threading.Thread(target=self.audio_loop, daemon=True).start()
        self.update_animation()

    def load_gif(self, path):
        gif = Image.open(path)
        temp_frames = []
        try:
            while True:
                frame = gif.copy().convert("RGBA").resize((gifWidth, gifHeight))
                temp_frames.append(ImageTk.PhotoImage(frame))
                gif.seek(gif.tell() + 1)
        except EOFError:
            pass

        if len(temp_frames) <= 2:
            self.frames = temp_frames
            return

        reversed_path = temp_frames[-2:0:-1]
        self.frames = temp_frames + list(reversed_path)

    def audio_loop(self):
        p = pyaudio.PyAudio()
        dev = p.get_default_wasapi_loopback()
        stream = p.open(format=pyaudio.paFloat32, channels=dev["maxInputChannels"],
                        rate=int(dev["defaultSampleRate"]), input=True,
                        input_device_index=dev["index"], frames_per_buffer=1024)
        while True:
            data = stream.read(1024, exception_on_overflow=False)
            samples = np.frombuffer(data, dtype=np.float32)
            rms = np.sqrt(np.mean(samples ** 2))
            self.smoothed_volume = self.smoothed_volume * 0.8 + rms * 0.2
            self.volume = self.smoothed_volume
            if self.volume > audioThreshold:
                self.last_sound_time = time.time()

    def get_delay(self):
        m = 0.05
        v = min(self.volume, m)
        t = (v - audioThreshold) / (m - audioThreshold) if v >= audioThreshold else 0
        current_delay = max(self.min_delay_base,
                            int(self.max_delay_base - (self.max_delay_base - self.min_delay_base) * t))
        return max(30, int(current_delay / self.speed_multiplier))

    def update_animation(self):
        time_since_last_sound = time.time() - self.last_sound_time

        if self.volume > audioThreshold:
            self.is_dancing = True
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.label.configure(image=self.frames[self.current_frame])
            self.root.after(self.get_delay(), self.update_animation)


        elif time_since_last_sound >= idleTimeout:
            self.is_dancing = True
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.label.configure(image=self.frames[self.current_frame])
            self.root.after(idleDanceDelay, self.update_animation)

        else:
            self.current_frame = 0
            self.label.configure(image=self.frames[0])
            self.is_dancing = False
            self.root.after(100, self.update_animation)

    def create_context_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Speed", command=self.open_settings_window)
        self.menu.add_separator()
        self.menu.add_command(label="About", command=self.show_about_info)
        self.menu.add_separator()
        self.menu.add_command(label="Close", command=lambda: os._exit(0))

    def show_context_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def open_settings_window(self):
        if self.settings_window is not None and tk.Toplevel.winfo_exists(self.settings_window):
            self.settings_window.lift()
            return
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Speed")
        self.settings_window.attributes("-topmost", True)
        self.settings_window.attributes("-toolwindow", True)
        self.settings_window.resizable(False, False)

        x_pos = self.base_x + (gifWidth // 2) - (settingSize[0] // 2)
        y_pos = self.base_y + 20
        self.settings_window.geometry(f"{settingSize[0]}x{settingSize[1]}+{x_pos}+{y_pos}")

        tk.Scale(self.settings_window, from_=0.5, to=2.5, resolution=0.1, orient=tk.HORIZONTAL,
                 command=lambda v: setattr(self, 'speed_multiplier', float(v))).set(self.speed_multiplier)
        self.settings_window.children['!scale'].pack(fill=tk.X, padx=20)

    def show_about_info(self):
        if self.about_window is not None and tk.Toplevel.winfo_exists(self.about_window):
            self.about_window.lift()
            return
        self.about_window = tk.Toplevel(self.root)
        self.about_window.title(aboutTitle)
        self.about_window.attributes("-topmost", True)
        self.about_window.attributes("-toolwindow", True)
        self.about_window.resizable(False, False)

        x_pos = self.base_x + (gifWidth // 2) - (aboutSize[0] // 2)
        y_pos = self.base_y + 20
        self.about_window.geometry(f"{aboutSize[0]}x{aboutSize[1]}+{x_pos}+{y_pos}")

        img = Image.open(aboutPath).resize((aboutWidth, aboutHeight))
        photo = ImageTk.PhotoImage(img)
        photo_label = tk.Label(self.about_window, image=photo)
        photo_label.image = photo
        photo_label.pack(pady=10)

        tk.Label(self.about_window, text=aboutTitle, font=("Arial", 14, "bold")).pack()

        tk.Label(self.about_window,
                 text="A desktop companion that makes listening \n to music more enjoyable\nThe animation speed can be adjusted using the slider\nV1.0").pack()


        link_text = "github.com/Ritsutoru"
        link_label = tk.Label(self.about_window, text=link_text, fg="blue", cursor="hand2",
                              font=("Arial", 10, "underline"))
        link_label.pack(pady=10)


        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/Ritsutoru"))

    def start_drag(self, event):
        self.drag_x, self.drag_y = event.x_root, event.y_root
        self.start_x, self.start_y = self.base_x, self.base_y

    def drag(self, event):
        self.base_x, self.base_y = self.start_x + (event.x_root - self.drag_x), self.start_y + (
                event.y_root - self.drag_y)
        self.root.geometry(f"+{self.base_x}+{self.base_y}")


if __name__ == "__main__":
    root = tk.Tk()
    SystemSoundPet(root, gifPath)
    root.mainloop()