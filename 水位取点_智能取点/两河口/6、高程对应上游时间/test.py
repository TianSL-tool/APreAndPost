import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt


def read_time_elevation_data(file_path):
    """读取时间-高程序列数据"""
    try:
        # 假设数据以空格或逗号分隔，第一列为时间，第二列为高程
        data = pd.read_csv(
            file_path,
            sep=r'\s+|,',  # 支持空格或逗号分隔
            header=None,
            engine='python',
            names=['time', 'elevation']
        )
        return data['time'].values, data['elevation'].values
    except Exception as e:
        print(f"读取时间-高程序列数据出错: {e}")
        return None, None


def read_elevations_to_find(file_path):
    """读取需要查找对应时间的高程数据"""
    try:
        # 读取单列高程数据
        elevations = pd.read_csv(
            file_path,
            header=None,
            names=['elevation']
        )['elevation'].values
        return elevations
    except Exception as e:
        print(f"读取待查找高程数据出错: {e}")
        return None


def find_corresponding_times(time_data, elevation_data, target_elevations):
    """通过插值找到目标高程对应的时间"""
    # 检查数据是否有序，如果不是则先排序
    if not np.all(np.diff(elevation_data) >= 0) and not np.all(np.diff(elevation_data) <= 0):
        print("高程数据不是单调的，将按高程排序后进行插值")
        # 按高程排序
        sorted_indices = np.argsort(elevation_data)
        elevation_data = elevation_data[sorted_indices]
        time_data = time_data[sorted_indices]

    # 创建插值函数：高程到时间的映射
    # 使用线性插值，超出范围的使用最近邻插值
    interp_func = interp1d(
        elevation_data,
        time_data,
        kind='linear',  # 线性插值
        bounds_error=False,  # 不抛出边界错误
        fill_value="extrapolate"  # 超出范围时外推
    )

    # 计算目标高程对应的时间
    corresponding_times = interp_func(target_elevations)
    return corresponding_times


def plot_results(time_data, elevation_data, target_elevations, target_times):
    """可视化结果"""
    plt.figure(figsize=(10, 6))
    # 绘制原始数据
    plt.plot(time_data, elevation_data, 'b-', label='原始时间-高程序列')
    # 绘制找到的对应点
    plt.plot(target_times, target_elevations, 'ro', label='插值得到的对应点')
    plt.xlabel('时间')
    plt.ylabel('高程')
    plt.title('高程与时间对应关系')
    plt.legend()
    plt.grid(True)
    plt.show()


def main():
    # 输入文件路径（可根据实际情况修改）
    time_elevation_file = 'time_elevation_data.txt'
    target_elevations_file = 'target_elevations.txt'

    # 读取数据
    time_data, elevation_data = read_time_elevation_data(time_elevation_file)
    target_elevations = read_elevations_to_find(target_elevations_file)

    if time_data is None or elevation_data is None or target_elevations is None:
        print("数据读取失败，程序退出")
        return

    # 查找对应时间
    target_times = find_corresponding_times(time_data, elevation_data, target_elevations)

    # 输出结果
    print("高程与对应时间:")
    for elev, time in zip(target_elevations, target_times):
        print(f"高程: {elev:.6f}  对应时间: {time:.6f}")

    # 可视化结果
    # plot_results(time_data, elevation_data, target_elevations, target_times)

    # 保存结果到文件
    result_df = pd.DataFrame({
        'target_elevation': target_elevations,
        'corresponding_time': target_times
    })
    result_df.to_csv('elevation_time_results.csv', index=False)
    print("结果已保存到 elevation_time_results.csv 文件")


if __name__ == "__main__":
    main()
