import sys

import librosa
import numpy as np
import pyqtgraph as pg
import vlc
from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QFileDialog, QPushButton

from dsp import ExpFilter


class WaveformThread(QThread):
    update_signal = Signal(np.ndarray, np.ndarray)

    def __init__(self, y, sr, sampling_interval, music_length, bin_nums, frequency_threshold):
        super().__init__()
        self.y = y
        self.sr = sr
        self.sampling_interval = sampling_interval
        self.music_length = music_length
        self.bin_nums = bin_nums
        self.frequency_threshold = frequency_threshold

    def run(self):
        try:
            music_fft = self.getBin(self.y, self.sr, self.sampling_interval)
            y_max = music_fft.max() // 3
            self.update_signal.emit(music_fft, y_max)
        except Exception as e:
            print(f"Error in WaveformThread: {e}")

    def getBin(self, y, sr, sampling_interval):
        fft_interval = int(sr * sampling_interval)
        length = fft_interval // 2
        nums = (sr * self.bin_nums) // (self.frequency_threshold * 2)
        batch = length // nums
        result = np.atleast_2d(np.zeros(self.bin_nums))
        for i in range(int(self.music_length // sampling_interval)):
            fft = np.fft.fft(y[fft_interval * i: fft_interval * (i + 1)])
            freqbin = np.array([np.abs(fft[batch * x: batch * (x + 1)]).sum() // sampling_interval
                                for x in range(self.bin_nums)])
            result = np.vstack([result, freqbin])
        return result


class LoadMusicThread(QThread):
    update_signal = Signal(np.ndarray, int)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            y, sr = librosa.load(self.file_path, sr=None)
            self.update_signal.emit(y, sr)
        except Exception as e:
            print(f"Error in LoadMusicThread: {e}")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music Visualizer")
        self.setGeometry(100, 100, 800, 600)
        self.main_layout = QVBoxLayout(self)

        self.plot_widget = pg.PlotWidget()
        # self.wave_plot_widget = pg.PlotWidget()
        # self.wave_line = pg.InfiniteLine(pos=0, angle=90, movable=False,
        #                                  pen=pg.mkPen(color='r', width=1))
        # self.wave_plot_widget.addItem(self.wave_line)
        # self.wave_line.setPos(10)
        # self.main_layout.addWidget(self.wave_plot_widget, stretch=1)
        self.main_layout.addWidget(self.plot_widget, stretch=3)

        # 设置显示的柱状图的个数
        self.bin_nums = 29
        # 设置显示的频率范围：(0 ~ frequency_threshold Hz)
        # self.frequency_threshold = 1350
        self.frequency_threshold = 1750

        # 帧时长，即每一帧所需的时长,简而言之就是每隔‘sampling_interval’ 秒刷新一次，
        # 所以我们所看到的某一个柱状图的状态就是从当前的一帧分析得出的，
        self.sampling_interval = 0.05

        temp = np.zeros(self.bin_nums)
        self.bars = pg.BarGraphItem(x=range(1, self.bin_nums + 1), height=temp, width=1, brush='w')
        self.plot_widget.addItem(self.bars)

        self.filter = ExpFilter(np.zeros(self.bin_nums), alpha_decay=0.30, alpha_rise=0.70)

        self.music_fft = np.empty(0)
        self.bins = np.empty(0)

        self.init_plot()
        self.init_ui()
        self.tick_count = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)

    def init_plot(self):
        self.plot_widget.setXRange(0, self.bin_nums + 1)
        self.plot_widget.setYRange(0, 1)
        # self.plot_widget.setLabel('bottom', "frequency ( * " + str(self.frequency_threshold / self.bin_nums) + " Hz)")
        self.plot_widget.setTitle("Simple Music Visualizer")

        # 移除坐标轴
        self.plot_widget.getPlotItem().hideAxis('left')
        self.plot_widget.getPlotItem().hideAxis('bottom')

    def init_ui(self):
        open_button = QPushButton("Open Music File", self)
        open_button.clicked.connect(self.open_file)
        self.main_layout.addWidget(open_button)

        self.play_pause_button = QPushButton("Play", self)
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.main_layout.addWidget(self.play_pause_button)

    def open_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Audio Files (*.mp3 *.wav *.flac *.m4a)")
        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]
            self.load_music(file_path)

    def load_music_complete(self, y, sr):
        self.y = y
        self.sr = sr
        self.wave_x_len = len(y)
        self.music_length = len(y) / sr
        # self.wave_plot_widget.clear()
        # self.wave_plot_widget.plot(y, pen='w')
        # self.wave_plot_widget.addItem(self.wave_line)

        self.waveform_thread = WaveformThread(y, sr, self.sampling_interval, self.music_length, self.bin_nums,
                                              self.frequency_threshold)
        self.waveform_thread.update_signal.connect(self.update_plot)
        self.waveform_thread.start()

        if not hasattr(self, "p"):
            self.p = vlc.MediaPlayer(self.load_music_thread.file_path)
        else:
            self.p.set_media(vlc.Media(self.load_music_thread.file_path))
            print(self.p.get_time())
        self.play_pause_button.setText("Play")

    def load_music(self, file_path):
        try:
            self.bars.setOpts(height=np.tile(0, self.bin_nums))
            # y, sr = librosa.load(file_path, sr=None)

            self.load_music_thread = LoadMusicThread(file_path)
            self.load_music_thread.update_signal.connect(self.load_music_complete)
            self.load_music_thread.start()
            #
            # self.wave_x_len = len(y)
            # self.music_length = len(y) / sr
            # self.wave_plot_widget.clear()
            # self.wave_plot_widget.plot(y, pen='w')
            # self.wave_plot_widget.addItem(self.wave_line)
            #
            # self.waveform_thread = WaveformThread(y, sr, self.sampling_interval, self.music_length, self.bin_nums,
            #                                       self.frequency_threshold)
            # self.waveform_thread.update_signal.connect(self.update_plot)
            # self.waveform_thread.start()
            #
            # if not hasattr(self, "p"):
            #     self.p = vlc.MediaPlayer(file_path)
            # else:
            #     self.p.set_media(vlc.Media(file_path))
            #     print(self.p.get_time())
            # self.play_pause_button.setText("Play")
        except Exception as e:
            print(f"Error loading music: {e}")

    def update_plot(self, music_fft, y_max):
        try:
            print("Update plot")
            print(music_fft, music_fft.shape)
            self.music_fft = music_fft
            self.y_max = y_max
            self.FRAMES = self.music_fft.shape[0]
            self.current_frame = 0

            self.plot_widget.setTitle("Simple Music Visualizer - " + self.p.get_media().get_meta(0))
        except Exception as e:
            print(f"Error in update_plot: {e}")

    def update(self):
        try:
            # self.tick_count += 1
            # print("Update")
            current_time = self.p.get_time() / 1000.0  # Get current playback time in seconds
            frame_index = int(current_time / self.sampling_interval)
            # self.wave_line.setPos(0)
            # if self.tick_count == 10:
            #     self.tick_count = 0
            #     QTimer.singleShot(200, lambda: self.wave_line.setPos(self.p.get_position() * self.wave_x_len))
            # self.wave_line.setPos(self.p.get_position() * self.wave_x_len)
            # print(self.p.get_position() * self.wave_x_len)
            if frame_index >= self.FRAMES:
                self.timer.stop()
                return

            source = self.music_fft[frame_index]
            index_max = self.y_max - (self.y_max // 80) < source
            source[index_max] = self.y_max - (self.y_max // 80)
            self.bins = self.filter.update(source)

            # Normalize
            self.bins = self.bins / self.y_max
            # print(self.bins)

            self.bars.setOpts(height=self.bins)

            # Dynamically adjust the timer interval
            self.timer.setInterval(int(self.sampling_interval * 1000 / 2))

            # Update the current frame index
            self.current_frame = frame_index
        except Exception as e:
            print(f"Error in update: {e}")

    def toggle_play_pause(self):
        if self.p.is_playing():
            self.p.pause()
            self.play_pause_button.setText("Play")
            self.timer.stop()
        else:
            self.p.play()
            self.play_pause_button.setText("Pause")
            self.timer.start(int(self.sampling_interval * 1000 / 2))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
