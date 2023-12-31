import os
import re
import eyed3
import musicbrainzngs
from tkinter import Tk, filedialog, messagebox
from tkinter.ttk import Progressbar
from tkinter import Label, Frame
from threading import Thread

# 设置你的MusicBrainz API用户名和密码
musicbrainzngs.set_useragent("0", "0", "0")
musicbrainzngs.auth("SeanDictionary", "qd7amjoExjCPTjvpgoYsN-rYfAyTiJtZ")

class MetadataUpdater:
    def __init__(self):
        self.root = Tk()
        self.root.title("MP3 元数据更新")

        # Dictionary to store file status
        self.file_status = {}

        # Progress bar
        self.progress_label = Label(self.root, text="等待中...")
        self.progress_label.pack()

        self.progress_bar = Progressbar(self.root, orient="horizontal", mode="determinate", length=300)
        self.progress_bar.pack()

        # Start button
        self.start_button = Label(self.root, text="开始更新", padx=10, pady=5, relief="groove", cursor="hand2")
        self.start_button.bind("<Button-1>", self.start_update)
        self.start_button.pack()

        # Thread for updating metadata
        self.update_thread = None

        # Update status file path
        self.status_file_path = os.path.join(os.path.expanduser("~"), "Desktop", "mp3_update_log.txt")

    def start_update(self, event):
        self.progress_label.config(text="进行中...")
        self.start_button.config(text="更新中", state="disabled")

        # Get a list of selected files
        files = filedialog.askopenfilenames(
            title="选择 MP3 文件",
            filetypes=[("MP3 文件", "*.mp3")]
        )

        if not files:
            messagebox.showinfo("提示", "没有选择文件")
            return

        # Initialize file status
        self.file_status = {file: "等待" for file in files}

        # Start a thread to update metadata
        self.update_thread = Thread(target=self.update_metadata, args=(files,))
        self.update_thread.start()

        # Start a thread to monitor progress
        self.root.after(100, self.monitor_progress)

    def update_metadata(self, files):
        for file_path in files:
            try:
                # Extract artist and title information from filename
                filename = os.path.basename(file_path)
                match = re.search(r'^(.+?) - (.+?)\.mp3$', filename)
                if match:
                    artists = match.group(1).split('_')
                    title = match.group(2)
                else:
                    artists = ["Unknown Artist"]
                    title = "Unknown Title"

                # Load the MP3 file
                audiofile = eyed3.load(file_path)

                # Update artist and title information in ID3 tag
                if audiofile.tag is None:
                    audiofile.initTag()

                # Set artists as a single string, joined with a semicolon and space
                artist_string = '; '.join(artists)
                audiofile.tag.artist = artist_string
                audiofile.tag.title = title

                # Get album information from MusicBrainz
                mb_artist = artists[0]  # For simplicity, use the first artist for the query
                mb_album_id, mb_album_title = self.get_album_info(mb_artist, title)

                # Update album information in ID3 tag
                if mb_album_id and mb_album_title:
                    audiofile.tag.album = mb_album_title

                # Save the changes
                audiofile.tag.save()

                # Update status to completed
                self.file_status[file_path] = "已完成"

            except Exception as e:
                # Update status to failed
                self.file_status[file_path] = f"失败: {str(e)}"

        # Save the status to a file
        with open(self.status_file_path, "w") as status_file:
            for file, status in self.file_status.items():
                status_file.write(f"{file}: {status}\n")

    def get_album_info(self, artist, title):
        try:
            # 查询MusicBrainz数据库获取专辑信息
            result = musicbrainzngs.search_releases(artist=artist, release=title, limit=1)
            if 'release-list' in result and len(result['release-list']) > 0:
                release = result['release-list'][0]
                return release['id'], release['title']
        except musicbrainzngs.WebServiceError as exc:
            print("Error:", exc)

        return None, None

    def monitor_progress(self):
        if self.update_thread.is_alive():
            completed = sum(1 for status in self.file_status.values() if status == "已完成")
            total = len(self.file_status)
            progress = int((completed / total) * 100)
            self.progress_bar["value"] = progress
            self.root.after(100, self.monitor_progress)
        else:
            self.progress_label.config(text="已完成")
            self.start_button.config(text="开始更新", state="active")
            messagebox.showinfo("提示", "更新完成")
            self.root.destroy()

    def run(self):
        self.root.mainloop()

# 实例化并运行应用程序
updater = MetadataUpdater()
updater.run()
