import librosa
import numpy as np
import matplotlib.pyplot as plt


def format_seconds(seconds):
    m, s = divmod(seconds, 60)
    return f"{int(m)}:{int(s)}"


# audio_path = librosa.example('nutcracker')
audio_path = "なんでもないや - RADWIMPS.mp3"
# audio_path = "金蛇狂舞 - 纯音乐.mp3"
y, sr = librosa.load(audio_path, sr=None)
music_length = len(y) / sr
print(f"时长: {format_seconds(music_length)} s 采样率: {sr / 1000} kHz")
xs = np.linspace(0, music_length, len(y))
plt.plot(xs, y)
plt.show()
