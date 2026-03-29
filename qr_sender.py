#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QR Data Bridge Sender
二维码幻灯片发送器 - 将文件切分成数据块并生成二维码幻灯片

Python 3.10+ required
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import qrcode
import base64
import json
import threading
import time
from pathlib import Path
from typing import List, Optional, Tuple
import struct

__version__ = "1.0.0"
__author__ = "terrycong"


class FileChunker:
    """文件切分器 - 将文件切分成指定大小的数据块"""
    
    def __init__(self, chunk_size: int = 200):
        """
        初始化切分器
        
        Args:
            chunk_size: 每个数据块的大小（字节），默认 200 字节
        """
        self.chunk_size = chunk_size
    
    def chunk_file(self, file_path: str) -> List[bytes]:
        """
        将文件切分成数据块
        
        Args:
            file_path: 文件路径
            
        Returns:
            数据块列表
        """
        chunks = []
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                chunks.append(chunk)
        return chunks
    
    def chunk_to_base64(self, chunk: bytes) -> str:
        """将数据块转换为 Base64 字符串"""
        return base64.b64encode(chunk).decode('ascii')
    
    def create_metadata(self, filename: str, total_chunks: int, chunk_size: int) -> dict:
        """创建文件元数据"""
        return {
            'name': filename,
            'chunks': total_chunks,
            'chunk_size': chunk_size,
            'version': 1
        }


class QRGenerator:
    """二维码生成器"""
    
    @staticmethod
    def generate_qr(data: str, version: int = 10) -> Image.Image:
        """
        生成二维码图片
        
        Args:
            data: 要编码的数据
            version: 二维码版本（1-40），固定版本确保每帧信息密度一致
                     版本 10 最大容量约 200 字节（HIGH 纠错级别）
            
        Returns:
            PIL Image 对象
        """
        qr = qrcode.QRCode(
            version=version,  # 固定版本，不使用 fit=True 自动调整
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # 高纠错级别
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make()  # 不使用 fit=True，保持固定版本
        
        img = qr.make_image(fill_color="black", back_color="white")
        return img


class QRSlideshowPlayer:
    """二维码幻灯片播放器"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("QR Data Bridge Sender - 二维码幻灯片发送器")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # 数据
        self.chunks: List[str] = []
        self.metadata: dict = {}
        self.current_index: int = 0
        self.is_playing: bool = False
        self.play_speed: float = 1.0  # 秒/帧
        self.play_thread: Optional[threading.Thread] = None
        self.stop_flag: bool = False
        
        # 创建 UI
        self._create_ui()
        
        # 文件切分器
        self.chunker = FileChunker()
    
    def _create_ui(self):
        """创建用户界面"""
        # 顶部工具栏
        self._create_toolbar()
        
        # 二维码显示区域
        self._create_display_area()
        
        # 底部控制栏
        self._create_controls()
        
        # 状态栏
        self._create_status_bar()
    
    def _create_toolbar(self):
        """创建顶部工具栏"""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        # 选择文件按钮
        ttk.Button(toolbar, text="📁 选择文件", command=self.select_file).pack(side=tk.LEFT, padx=2)
        
        # 数据块大小设置
        ttk.Label(toolbar, text="数据块大小 (字节):").pack(side=tk.LEFT, padx=5)
        self.chunk_size_var = tk.StringVar(value="200")
        chunk_size_combo = ttk.Combobox(toolbar, textvariable=self.chunk_size_var, width=10, values=[
            "100", "150", "200", "250", "300", "400", "500", "1000"
        ])
        chunk_size_combo.pack(side=tk.LEFT, padx=2)
        
        # 应用设置
        ttk.Button(toolbar, text="应用设置", command=self.apply_settings).pack(side=tk.LEFT, padx=5)
        
        # 文件信息
        self.file_info_label = ttk.Label(toolbar, text="未选择文件", foreground="gray")
        self.file_info_label.pack(side=tk.LEFT, padx=10)
    
    def _create_display_area(self):
        """创建二维码显示区域"""
        display_frame = ttk.Frame(self.root)
        display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 二维码标签
        self.qr_label = ttk.Label(display_frame, text="请选择文件开始", anchor=tk.CENTER)
        self.qr_label.pack(fill=tk.BOTH, expand=True)
        
        # 数据预览
        preview_frame = ttk.LabelFrame(display_frame, text="当前数据块内容")
        preview_frame.pack(fill=tk.X, pady=5)
        
        self.data_preview = tk.Text(preview_frame, height=4, wrap=tk.WORD, state=tk.DISABLED)
        self.data_preview.pack(fill=tk.X, padx=5, pady=5)
    
    def _create_controls(self):
        """创建底部控制栏"""
        controls_frame = ttk.Frame(self.root)
        controls_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 播放控制
        control_group = ttk.LabelFrame(controls_frame, text="播放控制")
        control_group.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 播放速度
        ttk.Label(control_group, text="播放速度 (秒/帧):").grid(row=0, column=0, padx=5, pady=5)
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_spinbox = ttk.Spinbox(control_group, from_=0.1, to=10.0, increment=0.1, 
                                    textvariable=self.speed_var, width=8)
        speed_spinbox.grid(row=0, column=1, padx=5, pady=5)
        
        # 控制按钮
        btn_frame = ttk.Frame(control_group)
        btn_frame.grid(row=0, column=2, columnspan=4, padx=20)
        
        ttk.Button(btn_frame, text="⏮️ 上一个", command=self.prev_frame).pack(side=tk.LEFT, padx=2)
        self.play_btn = ttk.Button(btn_frame, text="▶️ 播放", command=self.toggle_play)
        self.play_btn.pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="⏭️ 下一个", command=self.next_frame).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🔄 重放", command=self.replay).pack(side=tk.LEFT, padx=2)
        
        # 进度控制
        progress_group = ttk.LabelFrame(controls_frame, text="进度")
        progress_group.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_group, variable=self.progress_var, 
                                           maximum=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        self.position_label = ttk.Label(progress_group, text="0 / 0")
        self.position_label.pack(pady=2)
        
        # 跳转
        ttk.Label(progress_group, text="跳转到:").pack(side=tk.LEFT, padx=5)
        self.jump_var = tk.StringVar()
        jump_entry = ttk.Entry(progress_group, textvariable=self.jump_var, width=8)
        jump_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(progress_group, text="跳转", command=self.jump_to).pack(side=tk.LEFT, padx=2)
    
    def _create_status_bar(self):
        """创建状态栏"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(status_frame, text="就绪", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.count_label = ttk.Label(status_frame, text="数据块：0", anchor=tk.E)
        self.count_label.pack(side=tk.RIGHT, padx=5)
    
    def select_file(self):
        """选择文件"""
        file_path = filedialog.askopenfilename(
            title="选择要传输的文件",
            filetypes=[
                ("所有文件", "*.*"),
                ("文本文件", "*.txt"),
                ("图片文件", "*.jpg *.jpeg *.png *.gif"),
                ("文档文件", "*.pdf *.doc *.docx"),
            ]
        )
        
        if file_path:
            self._process_file(file_path)
    
    def _process_file(self, file_path: str):
        """处理文件"""
        try:
            self.status_label.config(text="正在处理文件...")
            self.root.update()
            
            # 获取设置
            chunk_size = int(self.chunk_size_var.get())
            self.chunker = FileChunker(chunk_size)
            
            # 切分文件
            chunks = self.chunker.chunk_file(file_path)
            
            if not chunks:
                messagebox.showerror("错误", "文件为空或读取失败")
                return
            
            # 转换为 Base64
            self.chunks = [self.chunker.chunk_to_base64(chunk) for chunk in chunks]
            
            # 创建元数据
            filename = Path(file_path).name
            self.metadata = self.chunker.create_metadata(filename, len(self.chunks), chunk_size)
            
            # 添加元数据作为第一个二维码
            metadata_str = json.dumps(self.metadata)
            self.chunks.insert(0, f"META:{metadata_str}")
            
            # 更新 UI
            self.current_index = 0
            self.file_info_label.config(text=f"✓ {filename} ({len(chunks)} 块)", foreground="green")
            self.count_label.config(text=f"数据块：{len(self.chunks)}")
            self.progress_var = tk.IntVar(value=0)
            self.progress_bar.configure(variable=self.progress_var, maximum=len(self.chunks))
            
            # 显示第一个二维码
            self._display_current_frame()
            
            self.status_label.config(text=f"文件已加载：{filename}")
            
        except Exception as e:
            messagebox.showerror("错误", f"处理文件失败：{str(e)}")
            self.status_label.config(text="处理失败")
    
    def apply_settings(self):
        """应用设置"""
        try:
            chunk_size = int(self.chunk_size_var.get())
            if chunk_size < 50 or chunk_size > 2000:
                raise ValueError("数据块大小必须在 50-2000 之间")
            
            if self.chunks:
                if messagebox.askyesno("确认", "更改设置将重新处理文件，确定吗？"):
                    # 需要重新选择文件
                    self.chunks = []
                    self.metadata = {}
                    self.current_index = 0
                    self.file_info_label.config(text="请重新选择文件", foreground="gray")
                    self.qr_label.config(image='')
                    self.data_preview.config(state=tk.NORMAL)
                    self.data_preview.delete(1.0, tk.END)
                    self.data_preview.config(state=tk.DISABLED)
                    self.status_label.config(text="请重新选择文件")
            else:
                self.status_label.config(text=f"设置已应用：数据块大小={chunk_size}字节")
                
        except ValueError as e:
            messagebox.showerror("错误", str(e))
    
    def _display_current_frame(self):
        """显示当前帧"""
        if not self.chunks or self.current_index >= len(self.chunks):
            return
        
        # 获取当前数据
        data = self.chunks[self.current_index]
        
        # 生成二维码
        try:
            qr_img = QRGenerator.generate_qr(data)
            
            # 调整大小以适应显示区域
            display_size = min(self.qr_label.winfo_width(), self.qr_label.winfo_height(), 500)
            if display_size < 100:
                display_size = 400
            qr_img = qr_img.resize((display_size, display_size), Image.Resampling.LANCZOS)
            
            # 转换为 PhotoImage
            photo = ImageTk.PhotoImage(qr_img)
            self.qr_label.config(image=photo, text="")
            self.qr_label.image = photo  # 保持引用
            
            # 更新数据预览
            self.data_preview.config(state=tk.NORMAL)
            self.data_preview.delete(1.0, tk.END)
            
            # 显示元数据或数据预览
            if data.startswith("META:"):
                meta = json.loads(data[5:])
                preview = f"【元数据】\n文件名：{meta['name']}\n总块数：{meta['chunks']}\n块大小：{meta['chunk_size']}字节"
            else:
                preview = f"【数据块 #{self.current_index}】\n{data[:200]}..." if len(data) > 200 else f"【数据块 #{self.current_index}】\n{data}"
            
            self.data_preview.insert(1.0, preview)
            self.data_preview.config(state=tk.DISABLED)
            
            # 更新进度
            self.progress_var.set(self.current_index + 1)
            self.position_label.config(text=f"{self.current_index + 1} / {len(self.chunks)}")
            
        except Exception as e:
            self.status_label.config(text=f"显示错误：{str(e)}")
    
    def toggle_play(self):
        """切换播放状态"""
        if self.is_playing:
            self.stop_play()
        else:
            self.start_play()
    
    def start_play(self):
        """开始播放"""
        if not self.chunks:
            messagebox.showwarning("警告", "请先选择文件")
            return
        
        self.is_playing = True
        self.stop_flag = False
        self.play_btn.config(text="⏸️ 暂停")
        self.status_label.config(text="正在播放...")
        
        # 启动播放线程
        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.play_thread.start()
    
    def stop_play(self):
        """停止播放"""
        self.is_playing = False
        self.stop_flag = True
        self.play_btn.config(text="▶️ 播放")
        self.status_label.config(text="已暂停")
    
    def _play_loop(self):
        """播放循环"""
        self.play_speed = self.speed_var.get()
        
        while self.is_playing and not self.stop_flag:
            if self.current_index >= len(self.chunks):
                # 播放完成
                self.is_playing = False
                self.root.after(0, self.stop_play)
                break
            
            # 在 UI 线程更新
            self.root.after(0, self._display_current_frame)
            self.root.after(0, lambda: self._increment_index())
            
            # 等待
            time.sleep(self.play_speed)
    
    def _increment_index(self):
        """增加索引"""
        self.current_index += 1
    
    def prev_frame(self):
        """上一帧"""
        if self.current_index > 0:
            self.current_index -= 1
            self._display_current_frame()
            self.stop_play()
    
    def next_frame(self):
        """下一帧"""
        if self.current_index < len(self.chunks) - 1:
            self.current_index += 1
            self._display_current_frame()
            self.stop_play()
    
    def replay(self):
        """重放"""
        self.current_index = 0
        self._display_current_frame()
        self.stop_play()
        if messagebox.askyesno("确认", "从头开始播放？"):
            self.start_play()
    
    def jump_to(self):
        """跳转到指定位置"""
        try:
            pos = int(self.jump_var.get())
            if 1 <= pos <= len(self.chunks):
                self.current_index = pos - 1
                self._display_current_frame()
                self.stop_play()
            else:
                messagebox.showerror("错误", f"位置必须在 1-{len(self.chunks)} 之间")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")


def main():
    """主函数"""
    root = tk.Tk()
    
    # 设置样式
    style = ttk.Style()
    style.theme_use('clam')  # 使用现代主题
    
    # 创建播放器
    player = QRSlideshowPlayer(root)
    
    # 窗口关闭处理
    root.protocol("WM_DELETE_WINDOW", lambda: root.quit())
    
    # 运行主循环
    root.mainloop()


if __name__ == "__main__":
    main()
