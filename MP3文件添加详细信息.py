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

        # 用于存储文件状态的字典
        self.file_status = {}

        # 进度条
        self.progress_label = Label(self.root, text="等待中...")
        self.progress_label.pack()

        self.progress_bar = Progressbar(self.root, orient="horizontal", mode="determinate", length=300)
        self.progress_bar.pack()

        # 开始按钮
        self.start_button = Label(self.root, text="开始更新", padx=10, pady=5, relief="groove", cursor="hand2")
        self.start_button.bind("<Button-1>", self.start_update)
        self.start_button.pack()

        # 用于更新元数据的线程
        self.update_thread = None

        # 更新状态文件路径
        self.status_file_path = os.path.join(os.path.expanduser("~"), "Desktop", "mp3_update_log.txt")

    def start_update(self, event):
        self.progress_label.config(text="进行中...")
        self.start_button.config(text="更新中", state="disabled")

        # 获取选择文件的列表
        files = filedialog.askopenfilenames(
            title="选择 MP3 文件",
            filetypes=[("MP3 文件", "*.mp3")]
        )

        if not files:
            messagebox.showinfo("提示", "没有选择文件")
            return

        # 初始化文件状态
        self.file_status = {file: "等待" for file in files}

        # 启动线程来更新元数据
        self.update_thread = Thread(target=self.update_metadata, args=(files,))
        self.update_thread.start()

        # 启动线程来监视进度
        self.root.after(100, self.monitor_progress)

    def update_metadata(self, files):
        for file_path in files:
            try:
                # 从文件名中提取艺术家和标题信息
                filename = os.path.basename(file_path)
                match = re.search(r'^(.+?) - (.+?)\.mp3$', filename)
                if match:
                    artists = match.group(1).split('_')
                    title = match.group(2)
                else:
                    artists = ["Unknown Artist"]
                    title = "Unknown Title"

                # 加载 MP3 文件
                audiofile = eyed3.load(file_path)

                # 在 ID3 标签中更新艺术家和标题信息
                if audiofile.tag is None:
                    audiofile.initTag()

                # 将艺术家作为一个字符串设置，用分号和空格连接
                artist_string = '; '.join(artists)
                audiofile.tag.artist = artist_string
                audiofile.tag.title = title

                # 从 MusicBrainz 获取专辑信息
                mb_artist = artists[0]  # 为简单起见，使用查询的第一个艺术家
                mb_album_id, mb_album_title = self.get_album_info(mb_artist, title)

                # 在 ID3 标签中更新专辑信息
                if mb_album_id and mb_album_title:
                    audiofile.tag.album = mb_album_title

                # 保存更改
                audiofile.tag.save()

                # 更新状态为已完成
                self.file_status[file_path] = "已完成"

            except Exception as e:
                # 更新状态为失败
                self.file_status[file_path] = f"失败: {str(e)}"

        # 将状态保存到文件
        with open(self.status_file_path, "w") as status_file:
            for file, status in self.file_status.items():
                status_file.write(f"{file}: {status}\n")

    def get_album_info(self, artist, title):
        try:
            # 查询 MusicBrainz 数据库获取专辑信息
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
