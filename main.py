import tkinter as tk
from tkinter import scrolledtext
import threading
import asyncio
import queue

import customtkinter as ctk

from script import everia

 # 日志队列（线程安全通信）
log_queue = queue.Queue()



# ========= 模拟后台任务（异步任务） =========
def run_async_task(keyword, log_queue):
    log_queue.put(f"[后台任务]  处理中...")
    start_asyncio_task(keyword, log_queue)
    log_queue.put(f"[后台任务]  完成 ✅")

# ========= 线程启动包装 =========
def start_asyncio_task(keyword, log_queue):
    asyncio.run(everia(keyword, log_queue))

# ========= 主UI =========
class DownloaderUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🖼️ 智能图片下载器")
        self.geometry("700x500")
        ctk.set_appearance_mode("dark")  # 可选: "light" / "dark"
        ctk.set_default_color_theme("blue")

        # ======= 顶部输入区 =======
        frame_top = ctk.CTkFrame(self, corner_radius=10)
        frame_top.pack(padx=20, pady=15, fill="x")

        self.keyword_entry = ctk.CTkEntry(frame_top, placeholder_text="默认为全搜索", width=400)
        self.keyword_entry.pack(side="left", padx=10, pady=10)

        self.start_btn = ctk.CTkButton(frame_top, text="开始下载", command=self.start_task)
        self.start_btn.pack(side="left", padx=10)

        self.progress = ctk.CTkProgressBar(frame_top, width=200)
        self.progress.pack(side="left", padx=10)
        self.progress.set(0)

        # ======= 日志显示区 =======
        frame_log = ctk.CTkFrame(self, corner_radius=10)
        frame_log.pack(padx=20, pady=10, fill="both", expand=True)

        self.log_box = ctk.CTkTextbox(frame_log, width=650, height=300)
        self.log_box.pack(padx=10, pady=10, fill="both", expand=True)
        self.log_box.configure(state="disabled")

        self.after(100, self.update_logs)  # 定时刷新日志




    def log_message(self, text):
        """安全写日志到UI"""
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # 主线程轮询更新日志（安全更新UI）
    def update_logs(self):
        while not log_queue.empty():
            msg = log_queue.get_nowait()
            self.log_message(msg)
        self.after(100, self.update_logs)

    # 点击按钮时启动后台任务

    def start_task(self):
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            keyword=""
        self.log_message(f"🚀 开始任务：{keyword}")
        self.progress.set(0.1)

        # 启动后台线程
        threading.Thread(target=run_async_task, args=(keyword,log_queue), daemon=True).start()



if __name__ == "__main__":
    app = DownloaderUI()
    app.mainloop()