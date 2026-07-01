import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os


def select_points(time_series, water_levels, max_days=30, max_change=10):
    """
    根据指定的时间间隔和水位变化幅度要求选择水位过程线上的点

    参数:
    time_series (list): 时间序列，元素为datetime对象
    water_levels (list): 对应的水位值列表
    max_days (int): 最大时间间隔（天）
    max_change (int): 最大水位变化幅度（米），包含上升和下降

    返回:
    selected_times (list): 选择的时间点
    selected_levels (list): 对应的水位值
    """
    if not time_series or not water_levels:
        return [], []

    # 确保数据按时间排序
    sorted_data = sorted(zip(time_series, water_levels), key=lambda x: x[0])
    time_series, water_levels = zip(*sorted_data)

    selected_indices = [0]  # 始终选择第一个点
    current_index = 0

    while current_index < len(time_series) - 1:
        next_possible_index = current_index + 1

        # 寻找符合条件的最远点
        while next_possible_index < len(time_series):
            # 检查时间间隔
            days_diff = (time_series[next_possible_index] - time_series[current_index]).days
            if days_diff > max_days:
                break

            # 检查水位变化幅度（上升或下降）
            current_level = water_levels[current_index]
            next_level = water_levels[next_possible_index]
            level_change = abs(current_level - next_level)

            if level_change > max_change:
                break

            next_possible_index += 1

        # 如果没有找到符合条件的点，选择下一个点
        if next_possible_index == current_index + 1:
            selected_indices.append(next_possible_index)
            current_index = next_possible_index
        else:
            # 选择符合条件的最远点的前一个点
            selected_indices.append(next_possible_index - 1)
            current_index = next_possible_index - 1

    # 根据选择的索引获取时间和水位值
    selected_times = [time_series[i] for i in selected_indices]
    selected_levels = [water_levels[i] for i in selected_indices]

    return selected_times, selected_levels


def find_peaks_and_valleys(time_series, water_levels, peak_threshold=None, valley_threshold=None):
    """
    查找水位过程线中的波峰和波谷

    参数:
    time_series (list): 时间序列
    water_levels (list): 水位值序列
    peak_threshold (float): 波峰阈值，低于此值的波峰将被忽略
    valley_threshold (float): 波谷阈值，高于此值的波谷将被忽略

    返回:
    peaks_times (list): 波峰时间
    peaks_levels (list): 波峰水位
    valleys_times (list): 波谷时间
    valleys_levels (list): 波谷水位
    """
    if len(time_series) < 3:
        return [], [], [], []

    peaks_indices = []
    valleys_indices = []

    # 使用差分方法寻找波峰和波谷
    for i in range(1, len(water_levels) - 1):
        # 波峰条件：当前点比前一个点高，比后一个点高
        if water_levels[i] > water_levels[i - 1] and water_levels[i] > water_levels[i + 1]:
            if peak_threshold is None or water_levels[i] >= peak_threshold:
                peaks_indices.append(i)

        # 波谷条件：当前点比前一个点低，比后一个点低
        if water_levels[i] < water_levels[i - 1] and water_levels[i] < water_levels[i + 1]:
            if valley_threshold is None or water_levels[i] <= valley_threshold:
                valleys_indices.append(i)

    # 处理边界情况：第一个点是波谷
    if len(water_levels) >= 2 and water_levels[0] < water_levels[1]:
        if valley_threshold is None or water_levels[0] <= valley_threshold:
            valleys_indices.insert(0, 0)

    # 处理边界情况：最后一个点是波谷
    if len(water_levels) >= 2 and water_levels[-1] < water_levels[-2]:
        if valley_threshold is None or water_levels[-1] <= valley_threshold:
            valleys_indices.append(len(water_levels) - 1)

    # 获取波峰和波谷的时间和水位值
    peaks_times = [time_series[i] for i in peaks_indices]
    peaks_levels = [water_levels[i] for i in peaks_indices]
    valleys_times = [time_series[i] for i in valleys_indices]
    valleys_levels = [water_levels[i] for i in valleys_indices]

    return peaks_times, peaks_levels, valleys_times, valleys_levels


def read_water_level_from_excel(file_path, date_column='日期', level_column='水位'):
    """
    从Excel文件读取水位数据

    参数:
    file_path (str): Excel文件路径
    date_column (str): 日期列的列名
    level_column (str): 水位列的列名

    返回:
    time_series (list): 时间序列
    water_levels (list): 水位值序列
    """
    try:
        df = pd.read_excel(file_path)

        # 检查必要的列是否存在
        if date_column not in df.columns or level_column not in df.columns:
            print(f"错误: 文件中找不到列 '{date_column}' 或 '{level_column}'")
            return [], []

        # 转换日期列
        try:
            df[date_column] = pd.to_datetime(df[date_column])
        except:
            print(f"错误: 无法将列 '{date_column}' 转换为日期格式")
            return [], []

        # 检查水位列是否为数值类型
        if not pd.api.types.is_numeric_dtype(df[level_column]):
            print(f"错误: 列 '{level_column}' 不是数值类型")
            return [], []

        # 过滤掉缺失值
        valid_data = df.dropna(subset=[date_column, level_column])

        return valid_data[date_column].tolist(), valid_data[level_column].tolist()
    except Exception as e:
        print(f"读取Excel文件时出错: {e}")
        return [], []


def add_selected_points_to_excel(input_file, output_file, selected_times, selected_levels,
                                 peaks_times, peaks_levels, valleys_times, valleys_levels,
                                 date_column='日期', level_column='水位',
                                 selected_date_column='取点日期', selected_level_column='取点水位',
                                 peak_date_column='波峰日期', peak_level_column='波峰水位',
                                 valley_date_column='波谷日期', valley_level_column='波谷水位'):
    """
    将选择的点、波峰和波谷添加到Excel文件中

    参数:
    input_file (str): 输入Excel文件路径
    output_file (str): 输出Excel文件路径
    selected_times (list): 选择的时间点
    selected_levels (list): 对应的水位值
    peaks_times (list): 波峰时间
    peaks_levels (list): 波峰水位
    valleys_times (list): 波谷时间
    valleys_levels (list): 波谷水位
    date_column (str): 日期列的列名
    level_column (str): 水位列的列名
    selected_date_column (str): 取点日期列的列名
    selected_level_column (str): 取点水位列的列名
    peak_date_column (str): 波峰日期列的列名
    peak_level_column (str): 波峰水位列的列名
    valley_date_column (str): 波谷日期列的列名
    valley_level_column (str): 波谷水位列的列名
    """
    try:
        # 读取原始数据
        df = pd.read_excel(input_file)

        # 确保日期列是datetime类型
        df[date_column] = pd.to_datetime(df[date_column])

        # 创建新列，初始化为NaN
        df[selected_date_column] = np.nan
        df[selected_level_column] = np.nan
        df[peak_date_column] = np.nan
        df[peak_level_column] = np.nan
        df[valley_date_column] = np.nan
        df[valley_level_column] = np.nan

        # 将选择的点添加到新列中
        for time, level in zip(selected_times, selected_levels):
            mask = df[date_column] == time
            if mask.any():
                df.loc[mask, selected_date_column] = time.strftime('%Y-%m-%d')
                df.loc[mask, selected_level_column] = level

        # 将波峰添加到新列中
        for time, level in zip(peaks_times, peaks_levels):
            mask = df[date_column] == time
            if mask.any():
                df.loc[mask, peak_date_column] = time.strftime('%Y-%m-%d')
                df.loc[mask, peak_level_column] = level

        # 将波谷添加到新列中
        for time, level in zip(valleys_times, valleys_levels):
            mask = df[date_column] == time
            if mask.any():
                df.loc[mask, valley_date_column] = time.strftime('%Y-%m-%d')
                df.loc[mask, valley_level_column] = level

        # 保存到新文件
        df.to_excel(output_file, index=False)
        print(f"结果已保存到 {output_file}")
    except Exception as e:
        print(f"处理Excel文件时出错: {e}")


def main():
    """主函数"""
    print("=== 水位过程线取点程序 ===")

    # 获取当前目录
    current_dir = os.getcwd()

    # 默认输入文件
    default_input_file = os.path.join(current_dir, "水位.xlsx")

    # 获取输入文件路径
    input_file = input(f"请输入Excel文件路径（默认为: {default_input_file}）: ")
    if not input_file:
        input_file = default_input_file

    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 文件 '{input_file}' 不存在")
        sys.exit(1)

    # 读取水位数据
    time_series, water_levels = read_water_level_from_excel(input_file)

    if not time_series or not water_levels:
        print("无法读取有效的水位数据，程序退出。")
        sys.exit(1)

    print(f"成功读取 {len(time_series)} 个数据点")

    # 从用户输入获取参数
    try:
        max_days = int(input("请输入最大时间间隔（天），默认为30: ") or "30")
        max_change = float(input("请输入最大水位变化幅度（米），默认为10: ") or "10")

        # 获取波峰波谷阈值
        peak_threshold_input = input("请输入波峰阈值（米），低于此值的波峰将被忽略，直接回车则不设置阈值: ")
        peak_threshold = float(peak_threshold_input) if peak_threshold_input else None

        valley_threshold_input = input("请输入波谷阈值（米），高于此值的波谷将被忽略，直接回车则不设置阈值: ")
        valley_threshold = float(valley_threshold_input) if valley_threshold_input else None
    except ValueError:
        print("输入无效，使用默认值")
        max_days = 30
        max_change = 10
        peak_threshold = None
        valley_threshold = None

    # 选择点
    selected_times, selected_levels = select_points(time_series, water_levels, max_days, max_change)

    # 查找波峰和波谷
    peaks_times, peaks_levels, valleys_times, valleys_levels = find_peaks_and_valleys(
        time_series, water_levels, peak_threshold, valley_threshold
    )

    # 打印结果
    print(f"\n共选择了 {len(selected_times)} 个点")
    print("选择的点:")
    for time, level in zip(selected_times, selected_levels):
        print(f"{time.strftime('%Y-%m-%d')}: {level:.2f} 米")

    print(f"\n共找到 {len(peaks_times)} 个波峰")
    for time, level in zip(peaks_times, peaks_levels):
        print(f"{time.strftime('%Y-%m-%d')}: {level:.2f} 米")

    print(f"\n共找到 {len(valleys_times)} 个波谷")
    for time, level in zip(valleys_times, valleys_levels):
        print(f"{time.strftime('%Y-%m-%d')}: {level:.2f} 米")

    # 默认输出文件
    base_name, ext = os.path.splitext(input_file)
    default_output_file = f"{base_name}_取点{ext}"

    # 获取输出文件路径
    output_file = input(f"请输入输出Excel文件路径（默认为: {default_output_file}）: ")
    if not output_file:
        output_file = default_output_file

    # 添加选择的点和波峰波谷到Excel文件
    add_selected_points_to_excel(
        input_file, output_file,
        selected_times, selected_levels,
        peaks_times, peaks_levels,
        valleys_times, valleys_levels
    )


if __name__ == "__main__":
    main()    