import pyqtgraph as pg
import numpy as np

# 创建图形窗口
win = pg.GraphicsLayoutWidget(show=True, title="LinearRegionItem 示例")
win.resize(800, 600)

# 添加一个绘图区域
plot = win.addPlot(title="绘图区域")
# 设置plot不可以缩放
plot.setMouseEnabled(x=False, y=False)

# 生成一些随机数据
data = np.random.normal(size=1000)

# 绘制数据
plot.plot(data, pen="b")

# 创建一个 InfiniteLine
vline = pg.InfiniteLine(pos=500,
                        angle=90,
                        movable=True,
                        bounds=[0, 1000],
                        pen=pg.mkPen(color="r", width=1),
                        hoverPen=pg.mkPen(color="g", width=2),
                        )
vline.sigPositionChangeFinished.connect(lambda pos: print(f"当前位置：{pos}"))
plot.addItem(vline)

# 显示图形窗口
if __name__ == '__main__':
    pg.exec()
