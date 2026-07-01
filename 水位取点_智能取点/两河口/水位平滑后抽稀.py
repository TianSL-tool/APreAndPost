import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter, find_peaks
import matplotlib.dates as mdates
import matplotlib
import os
import matplotlib.font_manager as fm


# 设置Matplotlib环境
def setup_matplotlib_env():
    matplotlib.use('Agg')

    # 中文字体设置
    font_candidates = ["Microsoft YaHei", "SimHei", "SimSun", "KaiTi", "Arial Unicode MS"]
    font_names = set()
    for font_path in fm.findSystemFonts(fontpaths=None, fontext='ttf'):
        try:
            font_prop = fm.FontProperties(fname=font_path)
            font_names.add(font_prop.get_name())
        except Exception:
            continue

    selected_font = None
    for font in font_candidates:
        if any(font.lower() in available.lower() for available in font_names):
            selected_font = font
            break

    if selected_font:
        plt.rcParams["font.family"] = selected_font
        print(f"已使用中文字体: {selected_font}")
    else:
        print("警告: 未找到可用中文字体，中文可能无法正常显示")

    plt.rcParams['axes.unicode_minus'] = False


# 从Excel读取水位数据
def read_water_level_from_excel(file_path, time_col='时间', level_col='水位'):
    try:
        try:
            df = pd.read_excel(file_path, engine='openpyxl')
        except Exception:
            df = pd.read_excel(file_path, engine='xlrd')

        if time_col not in df.columns:
            raise ValueError(f"Excel文件中未找到名为'{time_col}'的列")
        if level_col not in df.columns:
            raise ValueError(f"Excel文件中未找到名为'{level_col}'的列")

        df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
        initial_count = len(df)

        df = df.dropna(subset=[time_col, level_col])
        df = df.sort_values(by=time_col)

        removed_count = initial_count - len(df)
        if removed_count > 0:
            print(f"已移除{removed_count}条无效数据")

        df = df.set_index(time_col)[[level_col]]
        df.columns = ['water_level']

        print(f"成功读取有效数据: {len(df)}条")
        print(f"时间范围: {df.index.min()} 至 {df.index.max()}")
        return df

    except Exception as e:
        print(f"读取Excel文件出错: {str(e)}")
        return None


# 平滑处理
def smooth_water_level(data, method='savitzky-golay', **kwargs):
    if method == 'savitzky-golay':
        window_size = kwargs.get('window_size', 15)
        polyorder = kwargs.get('polyorder', 2)
        if window_size % 2 == 0:
            window_size += 1
        return savgol_filter(data, window_size, polyorder)

    elif method == 'moving-average':
        window_size = kwargs.get('window_size', 15)
        return pd.Series(data).rolling(window=window_size, center=True, min_periods=1).mean().values

    elif method == 'gaussian':
        sigma = kwargs.get('sigma', 2)
        from scipy.ndimage import gaussian_filter1d
        return gaussian_filter1d(data, sigma)

    else:
        raise ValueError(f"不支持的平滑方法: {method}")


# 基于曲线特征的抽稀算法（改进的Douglas-Peucker算法）
def feature_preserving_downsample(df, epsilon=0.1, max_points=None):
    """
    在保留曲线特征的同时减少点数量

    参数:
        df: 包含时间索引和水位数据的DataFrame
        epsilon: 控制抽稀程度的阈值（值越小保留点越多）
        max_points: 最大保留点数（可选）
    """
    # 提取数据和时间
    values = df['smoothed_water_level'].values
    times = df.index.values
    n = len(values)

    if n <= 2:
        return df  # 数据点太少，无需抽稀

    # 1. 首先识别关键特征点（极值点）
    # 计算一阶导数（反映变化率）
    derivatives = np.gradient(values)

    # 找到局部极大值和极小值点
    peaks, _ = find_peaks(values, distance=5)  # 峰值点
    valleys, _ = find_peaks(-values, distance=5)  # 谷值点
    feature_indices = set(peaks) | set(valleys)

    # 确保包含起点和终点
    feature_indices.add(0)
    feature_indices.add(n - 1)
    feature_indices = sorted(feature_indices)

    # 2. 使用Douglas-Peucker算法在特征点之间进一步抽稀
    def douglas_peucker(points, epsilon):
        if len(points) <= 2:
            return points

        # 找到距离最大的点
        x0, y0 = points[0]
        x1, y1 = points[-1]

        # 计算所有点到直线的距离
        distances = []
        for (x, y) in points[1:-1]:
            # 计算点到直线的垂直距离
            distance = abs((y1 - y0) * x - (x1 - x0) * y + x1 * y0 - y1 * x0) / np.sqrt((y1 - y0) ** 2 + (x1 - x0) ** 2)
            distances.append(distance)

        if not distances:
            return [points[0], points[-1]]

        max_dist = max(distances)
        max_index = distances.index(max_dist) + 1  # +1因为排除了第一个点

        if max_dist > epsilon:
            # 递归处理
            left = douglas_peucker(points[:max_index + 1], epsilon)
            right = douglas_peucker(points[max_index:], epsilon)
            return left[:-1] + right
        else:
            # 保留端点
            return [points[0], points[-1]]

    # 3. 对每个特征点区间应用抽稀算法
    all_indices = set(feature_indices)
    for i in range(len(feature_indices) - 1):
        start_idx = feature_indices[i]
        end_idx = feature_indices[i + 1]

        if end_idx - start_idx <= 1:
            continue

        # 提取区间内的点
        segment_points = [(idx, values[idx]) for idx in range(start_idx, end_idx + 1)]

        # 应用Douglas-Peucker算法
        simplified = douglas_peucker(segment_points, epsilon)

        # 添加抽稀后的点索引
        for (idx, _) in simplified[1:-1]:  # 排除已经在feature_indices中的端点
            all_indices.add(idx)

    # 4. 如果设置了最大点数限制，进一步调整
    all_indices = sorted(all_indices)
    if max_points and len(all_indices) > max_points:
        # 计算点之间的间隔，优先保留间隔大的点
        gaps = np.diff(all_indices)
        # 需要移除的点数
        to_remove = len(all_indices) - max_points
        # 找到间隔最小的点并移除
        for _ in range(to_remove):
            if len(gaps) <= 1:
                break
            min_gap_idx = np.argmin(gaps)
            all_indices.pop(min_gap_idx + 1)
            gaps = np.diff(all_indices)

    # 返回抽稀后的结果
    downsampled = df.iloc[all_indices]
    print(f"特征保留抽稀后，数据点数量: {len(downsampled)} (原始: {n})")
    return downsampled


# 绘制对比图
def plot_comparison(original_df, smoothed_df, downsampled_df, save_path='水位曲线_特征保留抽稀.png'):
    try:
        fig, ax = plt.subplots(figsize=(16, 9), dpi=120)

        # 原始数据（淡灰色）
        ax.plot(original_df.index, original_df['water_level'],
                label='原始数据', alpha=0.2, color='#999999', linewidth=1)

        # 平滑数据（蓝色线）
        ax.plot(smoothed_df.index, smoothed_df['smoothed_water_level'],
                label='平滑后数据', color='#2c7fb8', linewidth=1.5)

        # 抽稀后的数据（红色点+线连接）
        ax.plot(downsampled_df.index, downsampled_df['smoothed_water_level'],
                'r-', linewidth=1.5, alpha=0.7)
        ax.scatter(downsampled_df.index, downsampled_df['smoothed_water_level'],
                   label=f'抽稀后数据（{len(downsampled_df)}点）',
                   color='#e41a1c', s=30, alpha=0.8)

        # 图表设置
        ax.set_title('水位曲线（特征保留抽稀结果）', fontsize=18, pad=20)
        ax.set_xlabel('时间', fontsize=14, labelpad=10)
        ax.set_ylabel('水位 (m)', fontsize=14, labelpad=10)

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=10))
        plt.xticks(rotation=45, ha='right')

        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend(fontsize=12)

        plt.tight_layout()
        plt.savefig(save_path, bbox_inches='tight')
        plt.close(fig)
        print(f"图表已保存至: {os.path.abspath(save_path)}")

    except Exception as e:
        print(f"绘图时出错: {str(e)}")


# 主函数
def main():
    setup_matplotlib_env()

    # 配置文件路径
    input_file = "水位.xlsx"  # 输入Excel文件路径
    output_file = "water_level_processed.xlsx"  # 输出文件路径

    # 读取数据
    water_level_df = read_water_level_from_excel(
        file_path=input_file,
        time_col='日期',  # 实际时间列名
        level_col='水位'  # 实际水位列名
    )

    if water_level_df is not None and not water_level_df.empty:
        # 1. 平滑处理
        smoothed_data = smooth_water_level(
            water_level_df['water_level'].values,
            method='savitzky-golay',
            window_size=15,
            polyorder=2
        )

        smoothed_df = water_level_df.copy()
        smoothed_df['smoothed_water_level'] = smoothed_data

        # 2. 特征保留抽稀
        # 调整epsilon值控制抽稀程度：值越小保留点越多，特征保留越完整
        # 对于水位数据，建议epsilon设置为水位变化范围的1%-5%
        water_range = water_level_df['water_level'].max() - water_level_df['water_level'].min()
        epsilon = water_range * 0.02  # 自动计算epsilon（水位范围的2%）

        # 可选：设置最大点数限制
        max_points = 300  # 例如最多保留300个点

        downsampled_df = feature_preserving_downsample(
            smoothed_df,
            epsilon=epsilon,
            max_points=max_points  # 注释掉此行则不限制最大点数
        )

        # 3. 保存结果
        result_df = pd.DataFrame({
            '原始水位': water_level_df['water_level'],
            '平滑后水位': smoothed_df['smoothed_water_level'],
            '抽稀后水位': downsampled_df['smoothed_water_level']
        })

        try:
            result_df.to_excel(output_file, engine='openpyxl')
        except Exception:
            result_df.to_excel(output_file, engine='xlrd')
        print(f"处理后的数据已保存至: {os.path.abspath(output_file)}")

        # 4. 绘制对比图
        plot_comparison(water_level_df, smoothed_df, downsampled_df)

    print("处理完成!")


if __name__ == "__main__":
    main()
