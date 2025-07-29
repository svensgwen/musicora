import os
import json
import pygame
import customtkinter as ctk
from PyQt6.QtWidgets import QApplication, QFileDialog as QtFileDialog
from tkinter import simpledialog
from PIL import Image, ImageTk
from mutagen.mp3 import MP3
import threading
import time

# Constants
FILES_DIR = 'files'
MUSIC_DIR = 'assets/music'
LIBRARY_FILE = os.path.join(FILES_DIR, 'music_library.json')
ALBUM_ART_DIR = os.path.join(FILES_DIR, 'album_arts')

os.makedirs(FILES_DIR, exist_ok=True)
os.makedirs(ALBUM_ART_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)

# Init Pygame Mixer
pygame.mixer.init()

# Load music library
if not os.path.exists(LIBRARY_FILE):
    with open(LIBRARY_FILE, 'w') as f:
        json.dump({'All Songs': []}, f)

with open(LIBRARY_FILE, 'r') as f:
    music_library = json.load(f)

# Load songs from folder
def load_songs():
    all_songs = []
    for file in os.listdir(MUSIC_DIR):
        if file.endswith('.mp3'):
            song_path = os.path.join(MUSIC_DIR, file)
            song_name = os.path.splitext(file)[0]
            all_songs.append({'name': song_name, 'path': song_path})
    music_library['All Songs'] = all_songs
    with open(LIBRARY_FILE, 'w') as f:
        json.dump(music_library, f)

load_songs()

# App Window
class MusicPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Musicora")
        self.geometry("1600x900")

        self.current_playlist = 'All Songs'
        self.playing_index = 0
        self.is_playing = False
        self.song_length = 0
        self.song_widgets = []
        self.play_all_active = False
        self.seeking = False
        self.play_start_time = 0
        self.elapsed_time_at_pause = 0


        self.create_sidebar()
        self.create_main_frame()
        self.create_album_art_frame()
        self.load_playlist('All Songs')

        self.update_timeline()  # <--- NEW call to safe updater
        self.monitor_song_end()


    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200)
        self.sidebar.pack(side='left', fill='y')

        self.add_button = ctk.CTkButton(self.sidebar, text="Add Playlist", command=self.add_playlist)
        self.add_button.pack(pady=(10, 5), padx=5, anchor='w')

        self.add_song_button = ctk.CTkButton(self.sidebar, text="Add Song", command=self.add_song)
        self.add_song_button.pack(pady=(5, 10), padx=5, anchor='w')

        self.playlist_label = ctk.CTkLabel(self.sidebar, text="Playlists", font=("Arial", 16))
        self.playlist_label.pack(pady=5, anchor='w', padx=5)

        self.playlist_buttons = {}
        for playlist in music_library.keys():
            self.add_playlist_button(playlist)

    def add_playlist_button(self, playlist):
        btn = ctk.CTkButton(self.sidebar, text=playlist, command=lambda p=playlist: self.load_playlist(p))
        btn.pack(fill='x', padx=5, pady=2)
        self.playlist_buttons[playlist] = btn

    def add_playlist(self):
        name = simpledialog.askstring("Playlist Name", "Enter Playlist Name")
        if name and name not in music_library:
            music_library[name] = []
            self.add_playlist_button(name)
            with open(LIBRARY_FILE, 'w') as f:
                json.dump(music_library, f)

    def add_song(self):
        app = QApplication([])
        file_dialog = QtFileDialog()
        file_dialog.setFileMode(QtFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("MP3 files (*.mp3)")

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            file_path = selected_files[0] if selected_files else None
            if file_path:
                filename = os.path.basename(file_path)
                dest_path = os.path.join(MUSIC_DIR, filename)

                if not os.path.exists(dest_path):
                    with open(file_path, 'rb') as src, open(dest_path, 'wb') as dst:
                        dst.write(src.read())

                load_songs()
                self.load_playlist('All Songs')

    def create_main_frame(self):
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(side='left', fill='both', expand=True)

        self.search_frame = ctk.CTkFrame(self.main_frame)
        self.search_frame.pack(fill='x', pady=10, padx=10)

        self.search_var = ctk.StringVar()
        self.search_bar = ctk.CTkEntry(self.search_frame, textvariable=self.search_var, placeholder_text="Search songs")
        self.search_bar.pack(side='left', fill='x', expand=True)

        self.search_button = ctk.CTkButton(self.search_frame, text="Search", command=lambda: self.load_playlist(self.current_playlist))
        self.search_button.pack(side='left', padx=5)

        self.song_list_frame = ctk.CTkScrollableFrame(self.main_frame)
        self.song_list_frame.pack(fill='both', expand=True)

    def create_album_art_frame(self):
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.pack(side='right', fill='y')

        self.album_art = ctk.CTkLabel(self.right_frame, text="", width=300, height=300)
        self.album_art.pack(fill='x', padx=20, pady=(20, 10))

        self.create_controls_frame(parent=self.right_frame)

    def load_playlist(self, name):
        self.current_playlist = name
        songs = music_library.get(name, [])
        search_term = self.search_var.get().lower()

        for widget in self.song_list_frame.winfo_children():
            widget.destroy()

        self.song_widgets = []

        for i, song in enumerate(songs):
            if search_term in song['name'].lower():
                self.add_song_widget(song, i)

    def add_song_widget(self, song, index):
        frame = ctk.CTkFrame(self.song_list_frame)
        frame.pack(fill='x', pady=2, padx=5)

        label = ctk.CTkLabel(frame, text=song['name'])
        label.pack(side='left', padx=10)

        play_button = ctk.CTkButton(frame, text="Play", width=60, command=lambda i=index: self.toggle_play_song(i))
        play_button.pack(side='right', padx=5)

        remove_button = ctk.CTkButton(frame, text="X", width=30, command=lambda i=index: self.remove_song(i))
        remove_button.pack(side='right', padx=5)

        self.song_widgets.append({'play_button': play_button})

    def remove_song(self, index):
        if self.current_playlist in music_library:
            del music_library[self.current_playlist][index]
            with open(LIBRARY_FILE, 'w') as f:
                json.dump(music_library, f)
            self.load_playlist(self.current_playlist)

    def create_controls_frame(self, parent=None):
        self.controls = ctk.CTkFrame(parent if parent else self)
        self.controls.pack(fill='x', side='bottom', padx=10, pady=10)

        self.timeline_frame = ctk.CTkFrame(self.controls)
        self.timeline_frame.pack(fill='x', padx=20, pady=5)

        self.song_duration_label = ctk.CTkLabel(self.timeline_frame, text="00:00")
        self.song_duration_label.pack(side='left')

        self.timeline = ctk.CTkSlider(self.timeline_frame, from_=0, to=100, command=self.seek)
        self.timeline.pack(side='left', fill='x', expand=True, padx=10)

        self.timeline.bind("<Button-1>", lambda e: setattr(self, 'seeking', True))
        self.timeline.bind("<ButtonRelease-1>", lambda e: setattr(self, 'seeking', False))

        self.elapsed_label = ctk.CTkLabel(self.timeline_frame, text="00:00")
        self.elapsed_label.pack(side='right')

        btn_frame = ctk.CTkFrame(self.controls)
        btn_frame.pack(pady=5)

        self.prev_btn = ctk.CTkButton(btn_frame, text="Prev", command=self.prev_song)
        self.prev_btn.pack(side='left', padx=5)

        self.play_btn = ctk.CTkButton(btn_frame, text="Play", command=self.toggle_play)
        self.play_btn.pack(side='left', padx=5)

        self.stop_btn = ctk.CTkButton(btn_frame, text="Stop", command=self.stop_song)
        self.stop_btn.pack(side='left', padx=5)

        self.next_btn = ctk.CTkButton(btn_frame, text="Next", command=self.next_song)
        self.next_btn.pack(side='left', padx=5)

        self.play_all_btn = ctk.CTkButton(btn_frame, text="Play All", command=self.play_all_songs)
        self.play_all_btn.pack(side='left', padx=5)

    def toggle_play_song(self, index):
        self.play_all_active = False
        if self.is_playing and self.playing_index == index:
            self.toggle_play()
        else:
            self.play_song(index)

    def play_song(self, index):
        self.playing_index = index
        songs = music_library.get(self.current_playlist, [])
        if 0 <= index < len(songs):
            song = songs[index]
            pygame.mixer.music.load(song['path'])
            pygame.mixer.music.play()
            self.is_playing = True
            self.play_btn.configure(text="Pause")
            self.update_song_buttons()

            audio = MP3(song['path'])
            self.song_length = audio.info.length
            self.timeline.configure(to=self.song_length)
            self.song_duration_label.configure(text=self.format_time(self.song_length))

            self.play_start_time = time.time()
            self.elapsed_time_at_pause = 0

            self.load_album_art(song['name'])


    def update_song_buttons(self):
        for i, widget in enumerate(self.song_widgets):
            if i == self.playing_index and self.is_playing:
                widget['play_button'].configure(text="Pause")
            else:
                widget['play_button'].configure(text="Play")

    def toggle_play(self):
        if self.is_playing:
            pygame.mixer.music.pause()
            self.elapsed_time_at_pause = time.time() - self.play_start_time
            self.is_playing = False
            self.play_btn.configure(text="Play")
        else:
            pygame.mixer.music.unpause()
            self.play_start_time = time.time() - self.elapsed_time_at_pause
            self.is_playing = True
            self.play_btn.configure(text="Pause")
        self.update_song_buttons()


    def stop_song(self):
        pygame.mixer.music.stop()
        self.is_playing = False
        self.play_btn.configure(text="Play")
        self.update_song_buttons()
        self.play_all_active = False

    def next_song(self):
        self.play_song(self.playing_index + 1)

    def prev_song(self):
        if self.playing_index > 0:
            self.play_song(self.playing_index - 1)

    def seek(self, val):
        try:
            pos = float(val)
            if 0 <= pos <= self.song_length:
                pygame.mixer.music.play(start=pos)
                self.play_start_time = time.time() - pos
                self.elapsed_time_at_pause = 0
                self.timeline.set(pos)
                self.elapsed_label.configure(text=self.format_time(pos))
                self.is_playing = True
                self.play_btn.configure(text="Pause")
        except Exception as e:
            print(f"Seek error: {e}")


    def format_time(self, seconds):
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{mins:02}:{secs:02}"

    def update_timeline(self):
        if self.is_playing and not self.seeking:
            elapsed = time.time() - self.play_start_time
            if 0 <= elapsed <= self.song_length:
                self.timeline.set(elapsed)
                self.elapsed_label.configure(text=self.format_time(elapsed))
        self.after(500, self.update_timeline)


    def monitor_song_end(self):
        def monitor():
            while True:
                if self.is_playing and not pygame.mixer.music.get_busy():
                    if self.play_all_active:
                        self.next_song()
                    else:
                        self.is_playing = False
                        self.update_song_buttons()
                time.sleep(1)
        threading.Thread(target=monitor, daemon=True).start()

        def create_volume_frame(self):
            self.volume_frame = ctk.CTkFrame(self, width=60)
            self.volume_frame.pack(side='right', fill='y')

            self.volume_label = ctk.CTkLabel(self.volume_frame, text="Vol", font=("Arial", 14))
            self.volume_label.pack(pady=(10, 5))

            self.volume_slider = ctk.CTkSlider(
                self.volume_frame,
                from_=0,
                to=100,
                orientation="vertical",
                command=self.set_volume,
                number_of_steps=100,
                height=600
            )
            self.volume_slider.set(70)
            pygame.mixer.music.set_volume(0.7)
            self.volume_slider.pack(expand=True, fill='y', pady=20, padx=10)
        create_volume_frame(self)

    def set_volume(self, value):
        volume = float(value) / 100
        pygame.mixer.music.set_volume(volume)


    def play_all_songs(self):
        self.play_all_active = True
        self.play_song(0)

    def load_album_art(self, song_name):
        art_path = os.path.join(ALBUM_ART_DIR, f"{song_name}.jpg")
        if os.path.exists(art_path):
            img = Image.open(art_path).resize((400, 400))
            photo = ImageTk.PhotoImage(img)
            self.album_art.configure(image=photo)
            self.album_art.image = photo
        else:
            self.album_art.configure(image=None, text="")

if __name__ == '__main__':
    app = MusicPlayer()
    app.mainloop()

