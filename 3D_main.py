import sys
import numpy as np
import librosa
import vlc
from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QFileDialog, QPushButton
from pyqtgraph.opengl import GLViewWidget, GLBarGraphItem
from pyqtgraph import Vector


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
        result = np.atleast_2d(np.tile(0, self.bin_nums))
        for i in range(int(self.music_length // sampling_interval)):
            fft = np.fft.fft(y[fft_interval * i: fft_interval * (i + 1)])
            freqbin = np.array([np.abs(fft[batch * x: batch * (x + 1)]).sum() // sampling_interval
                                for x in range(self.bin_nums)])
            result = np.vstack([result, freqbin])
        return result


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music Visualizer 3D")
        self.setGeometry(100, 100, 800, 600)
        self.main_layout = QVBoxLayout(self)

        self.view = GLViewWidget()
        self.main_layout.addWidget(self.view)

        # 设置显示的柱状图的个数
        self.bin_nums = 29
        # 设置显示的频率范围：(0 ~ frequency_threshold Hz)
        self.frequency_threshold = 1350

        # 帧时长，即每一帧所需的时长,简而言之就是每隔’sampling_interval’ 秒刷新一次，
        # 所以我们所看到的某一个柱状图的状态就是从当前的一帧分析得出的，
        self.sampling_interval = 0.05

        temp = np.zeros(self.bin_nums)
        self.bars = GLBarGraphItem(
            pos=np.column_stack((np.arange(self.bin_nums), np.zeros(self.bin_nums), np.zeros(self.bin_nums))),
            size=np.column_stack((np.full(self.bin_nums, 0.5), np.full(self.bin_nums, 1), np.full(self.bin_nums, 0.2))),
            # size is a 3D array of the sizes of each bar
        )
        self.view.addItem(self.bars)

        self.view.opts['distance'] = 20  # 调整相机距离
        self.view.opts['elevation'] = 30  # 调整相机仰角
        self.view.opts['azimuth'] = 30  # 调整相机水平角度

        self.init_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)

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

    def load_music(self, file_path):
        try:
            y, sr = librosa.load(file_path, sr=None)
            music_length = len(y) / sr

            self.waveform_thread = WaveformThread(y, sr, self.sampling_interval, music_length, self.bin_nums,
                                                  self.frequency_threshold)
            self.waveform_thread.update_signal.connect(self.update_plot)
            self.waveform_thread.start()

            if not hasattr(self, "p"):
                self.p = vlc.MediaPlayer(file_path)
            else:
                self.p.set_media(vlc.Media(file_path))
                print(self.p.get_time())
            self.play_pause_button.setText("Play")
        except Exception as e:
            print(f"Error loading music: {e}")

    def update_plot(self, music_fft, y_max):
        try:
            print("Update plot")
            self.music_fft = music_fft
            self.y_max = y_max
            self.FRAMES = self.music_fft.shape[0]
            self.current_frame = 0

            self.view.setWindowTitle("Simple Music Visualizer 3D - " + self.p.get_media().get_meta(0))
        except Exception as e:
            print(f"Error in update_plot: {e}")

    def update(self):
        try:
            # print("Update")
            current_time = self.p.get_time() / 1000.0  # Get current playback time in seconds
            frame_index = int(current_time / self.sampling_interval)

            if frame_index >= self.FRAMES:
                self.timer.stop()
                return

            source = self.music_fft[frame_index]
            index_max = self.y_max - (self.y_max // 80) < source
            source[index_max] = self.y_max - (self.y_max // 80)

            # Normalize
            self.bins = source / self.y_max

            # Create a new GLBarGraphItem with the updated heights
            new_bars = GLBarGraphItem(
                pos=np.column_stack((np.arange(self.bin_nums), np.zeros(self.bin_nums), np.zeros(self.bin_nums))),
                size=np.column_stack((np.full(self.bin_nums, 0.5), self.bins, np.full(self.bin_nums, 0.2))),
            )

            # Remove the old bars if they exist
            if self.bars is not None:
                self.view.removeItem(self.bars)
            # Add the new bars to the view
            self.view.addItem(new_bars)
            # Update the reference to the new bars
            self.bars = new_bars

            # Dynamically adjust the timer interval
            self.timer.setInterval(int(self.sampling_interval * 1000))

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
            self.timer.start(int(self.sampling_interval * 1000))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
