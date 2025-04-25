import customtkinter as ctk
import yt_dlp
import os
import threading
import sys
import subprocess
from tkinter import filedialog
from urllib.parse import urlparse, parse_qs

class VideoDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Downloader")
        self.root.geometry("600x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Xác định thư mục gốc của chương trình (hỗ trợ .py và .exe)
        if getattr(sys, 'frozen', False):
            self.program_dir = os.path.dirname(sys.executable)
        else:
            self.program_dir = os.path.dirname(os.path.abspath(__file__))

        # Thư mục tải xuống mặc định: <root_program>/downloads
        self.download_path = os.path.join(self.program_dir, "downloads")
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

        self.progress = 0
        self.is_finished = False
        self.create_widgets()

    def create_widgets(self):
        # Nhãn và ô nhập URL
        self.url_label = ctk.CTkLabel(self.root, text="Nhập URL video:")
        self.url_label.pack(pady=10)
        self.url_entry = ctk.CTkEntry(self.root, width=400, placeholder_text="https://www.youtube.com/watch?v=...")
        self.url_entry.pack()

        # Frame để chứa độ phân giải và định dạng trên cùng một dòng
        self.options_frame = ctk.CTkFrame(self.root)
        self.options_frame.pack(pady=10)

        # Độ phân giải
        self.resolution_label = ctk.CTkLabel(self.options_frame, text="Độ phân giải:")
        self.resolution_label.pack(side="left", padx=5)
        self.resolution_var = ctk.StringVar(value="best")
        resolutions = ["best", "2160p", "1440p", "1080p", "720p", "360p"]
        self.resolution_menu = ctk.CTkOptionMenu(self.options_frame, values=resolutions, variable=self.resolution_var, width=150)
        self.resolution_menu.pack(side="left", padx=10)

        # Định dạng
        self.format_label = ctk.CTkLabel(self.options_frame, text="Định dạng:")
        self.format_label.pack(side="left", padx=5)
        self.format_var = ctk.StringVar(value="mp4")
        formats = ["mp4", "webm", "mp3", "wav"]
        self.format_menu = ctk.CTkOptionMenu(self.options_frame, values=formats, variable=self.format_var, width=150)
        self.format_menu.pack(side="left", padx=10)

        # Thư mục lưu
        self.path_label = ctk.CTkLabel(self.root, text=f"Thư mục lưu: {self.download_path}")
        self.path_label.pack(pady=10)
        self.path_button = ctk.CTkButton(self.root, text="Chọn thư mục", command=self.choose_path)
        self.path_button.pack()

        # Nút tải
        self.download_button = ctk.CTkButton(self.root, text="Tải xuống", command=self.start_download)
        self.download_button.pack(pady=20)

        # Thanh tiến độ
        self.progress_bar = ctk.CTkProgressBar(self.root, width=400)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

        # Nhãn trạng thái
        self.status_label = ctk.CTkLabel(self.root, text="Sẵn sàng")
        self.status_label.pack(pady=10)

        # Nút mở thư vacant mục đầu ra
        self.open_folder_button = ctk.CTkButton(self.root, text="Open Output Folder", command=self.open_output_folder, state="disabled")
        self.open_folder_button.pack(pady=10)

        # Log textbox
        self.log_text = ctk.CTkTextbox(self.root, width=400, height=150)
        self.log_text.pack(pady=10)

    def choose_path(self):
        path = filedialog.askdirectory(initialdir=self.download_path)
        if path:
            self.download_path = path
            self.path_label.configure(text=f"Thư mục lưu: {self.download_path}")

    def open_output_folder(self):
        """Mở thư mục đầu ra trong file explorer."""
        try:
            if sys.platform == "win32":
                os.startfile(self.download_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", self.download_path])
            else:
                subprocess.run(["xdg-open", self.download_path])
        except Exception as e:
            self.log_text.insert("end", f"Lỗi mở thư mục: {str(e)}\n")
            self.log_text.see("end")

    def clean_youtube_url(self, url):
        """Chuẩn hóa URL YouTube để tránh tải playlist hoặc tham số thừa."""
        parsed = urlparse(url)
        if "youtube.com" in parsed.netloc or "youtu.be" in parsed.netloc:
            query = parse_qs(parsed.query)
            video_id = query.get("v", [None])[0]
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"
            elif parsed.netloc == "youtu.be":
                video_id = parsed.path.lstrip("/")
                return f"https://www.youtube.com/watch?v={video_id}"
        return url

    def update_progress(self, d):
        if d['status'] == 'downloading':
            if 'downloaded_bytes' in d and 'total_bytes' in d:
                progress = d['downloaded_bytes'] / d['total_bytes']
                self.progress_bar.set(progress)
                self.status_label.configure(text=f"Đang tải: {progress*100:.1f}%", text_color="white")
                self.log_text.insert("end", f"Đang tải: {progress*100:.1f}%\n")
        elif d['status'] == 'finished' and not self.is_finished:
            self.is_finished = True
            self.progress_bar.set(1)
            self.status_label.configure(text="Tải xuống hoàn tất!", text_color="yellow")
            self.log_text.insert("end", "Tải xuống hoàn tất!\n")
            self.open_folder_button.configure(state="normal")
        self.log_text.see("end")

    def download_video(self, url):
        self.is_finished = False
        self.open_folder_button.configure(state="disabled")
        url = self.clean_youtube_url(url)
        resolution = self.resolution_var.get()
        file_format = self.format_var.get()

        # Cấu hình yt-dlp
        ydl_opts = {
            'outtmpl': f'{self.download_path}/%(title)s.%(ext)s',
            'progress_hooks': [self.update_progress],
            'noplaylist': True,
            'no_warnings': True,
            'merge_output_format': 'mp4',
            'format_sort': ['+res', '+vcodec:h264'],
            'logger': self,
        }

        # Xử lý độ phân giải
        if resolution != "best":
            ydl_opts['format'] = f'bestvideo[height<={resolution[:-1]}][vcodec~="^h264$"][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
        else:
            ydl_opts['format'] = 'bestvideo[vcodec~="^h264$"][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'

        # Xử lý định dạng âm thanh
        if file_format in ['mp3', 'wav']:
            ydl_opts['format'] = 'bestaudio'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': file_format,
            }]
            ydl_opts.pop('merge_output_format', None)
        elif file_format == 'webm':
            ydl_opts['format'] = 'bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]'
            ydl_opts['merge_output_format'] = 'webm'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.log_text.insert("end", f"Bắt đầu tải: {url}\n")
                ydl.download([url])
        except Exception as e:
            self.status_label.configure(text="Lỗi tải xuống", text_color="red")
            self.log_text.insert("end", f"Lỗi: {str(e)}\n")
            self.open_folder_button.configure(state="normal")
            self.log_text.see("end")

    def debug(self, msg):
        self.log_text.insert("end", f"DEBUG: {msg}\n")
        self.log_text.see("end")

    def warning(self, msg):
        self.log_text.insert("end", f"WARNING: {msg}\n")
        self.log_text.see("end")

    def error(self, msg):
        self.log_text.insert("end", f"ERROR: {msg}\n")
        self.log_text.see("end")

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            self.status_label.configure(text="Vui lòng nhập URL!", text_color="red")
            return

        self.download_button.configure(state="disabled")
        self.status_label.configure(text="Đang tải...", text_color="white")
        self.progress_bar.set(0)
        self.log_text.delete("1.0", "end")

        thread = threading.Thread(target=self.download_video, args=(url,))
        thread.start()

        self.root.after(1000, self.check_thread, thread)

    def check_thread(self, thread):
        if thread.is_alive():
            self.root.after(1000, self.check_thread, thread)
        else:
            self.download_button.configure(state="normal")
            if self.status_label.cget("text") != "Tải xuống hoàn tất!":
                self.status_label.configure(text="Sẵn sàng", text_color="white")

if __name__ == "__main__":
    root = ctk.CTk()
    app = VideoDownloaderApp(root)
    root.mainloop()