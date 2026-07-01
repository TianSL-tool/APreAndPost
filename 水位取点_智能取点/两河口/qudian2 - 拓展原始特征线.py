import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os


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


def merge_and_sort_points(origin_times, origin_levels, peaks_times, peaks_levels, valleys_times, valleys_levels):
    """
    合并波峰和波谷点，并按时间排序

    参数:
    peaks_times (list): 波峰时间
    peaks_levels (list): 波峰水位
    valleys_times (list): 波谷时间
    valleys_levels (list): 波谷水位

    返回:
    sorted_times (list): 排序后的时间点
    sorted_levels (list): 排序后的水位值
    """
    # 合并波峰和波谷点
    all_times = peaks_times + valleys_times + origin_times
    all_levels = peaks_levels + valleys_levels + origin_levels

    # 按时间排序
    sorted_points = sorted(zip(all_times, all_levels), key=lambda x: x[0])
    sorted_times, sorted_levels = zip(*sorted_points)

    return list(sorted_times), list(sorted_levels)


def interpolate_by_time(sorted_times, sorted_levels, max_interval_days=30):
    """
    基于时间间隔对排序后的点进行插值处理

    参数:
    sorted_times (list): 排序后的时间点
    sorted_levels (list): 排序后的水位值
    max_interval_days (int): 最大插值间隔（天）

    返回:
    interpolated_times (list): 插值后的时间点
    interpolated_levels (list): 插值后的水位值
    """
    if not sorted_times or len(sorted_times) < 2:
        return sorted_times, sorted_levels

    interpolated_times = sorted_times.copy()
    interpolated_levels = sorted_levels.copy()

    i = 0
    while i < len(interpolated_times) - 1:
        current_time = interpolated_times[i]
        next_time = interpolated_times[i + 1]
        current_level = interpolated_levels[i]
        next_level = interpolated_levels[i + 1]

        # 计算时间间隔（天）
        days_diff = (next_time - current_time).days

        # 如果时间间隔大于1.5倍的最大插值间隔，则进行插值
        if days_diff > max_interval_days * 1.5:
            # 计算需要插入的点数
            num_points_to_insert = int(days_diff / max_interval_days) - 1

            if num_points_to_insert > 0:
                # 计算插值点
                inserted_times = []
                inserted_levels = []

                for j in range(1, num_points_to_insert + 1):
                    # 计算插值时间
                    time_fraction = j / (num_points_to_insert + 1)
                    delta_days = timedelta(days=days_diff * time_fraction)
                    inserted_time = current_time + delta_days

                    # 计算插值水位（线性插值）
                    level_fraction = j / (num_points_to_insert + 1)
                    inserted_level = current_level + (next_level - current_level) * level_fraction

                    inserted_times.append(inserted_time)
                    inserted_levels.append(inserted_level)

                # 插入新点
                interpolated_times = (
                        interpolated_times[:i + 1] + inserted_times + interpolated_times[i + 1:]
                )
                interpolated_levels = (
                        interpolated_levels[:i + 1] + inserted_levels + interpolated_levels[i + 1:]
                )

                # 跳过已经插入的点
                i += num_points_to_insert + 1
                continue

        # 处理下一对点
        i += 1

    return interpolated_times, interpolated_levels


def interpolate_by_level(interpolated_times, interpolated_levels, max_level_diff=10):
    """
    基于水位差对插值后的点进行二次插值处理

    参数:
    interpolated_times (list): 插值后的时间点
    interpolated_levels (list): 插值后的水位值
    max_level_diff (float): 最大水位差

    返回:
    final_times (list): 最终的时间点
    final_levels (list): 最终的水位值
    """
    if not interpolated_times or len(interpolated_times) < 2:
        return interpolated_times, interpolated_levels

    final_times = interpolated_times.copy()
    final_levels = interpolated_levels.copy()
    print(max_level_diff)
    i = 0
    while i < len(final_times) - 1:
        current_time = final_times[i]
        next_time = final_times[i + 1]
        current_level = final_levels[i]
        next_level = final_levels[i + 1]

        # 计算水位差
        level_diff = abs(next_level - current_level)

        # 如果水位差大于1.5倍的最大水位差，则进行插值
        if level_diff > max_level_diff * 1.5:
            # 计算需要插入的点数
            num_points_to_insert = int(level_diff / max_level_diff) - 1

            if num_points_to_insert > 0:
                # 计算插值点
                inserted_times = []
                inserted_levels = []

                # 计算总时间差（秒）
                total_seconds = (next_time - current_time).total_seconds()

                for j in range(1, num_points_to_insert + 1):
                    # 计算插值水位
                    level_fraction = j / (num_points_to_insert + 1)
                    inserted_level = current_level + (next_level - current_level) * level_fraction

                    # 计算插值时间（线性插值）
                    time_fraction = j / (num_points_to_insert + 1)
                    delta_seconds = timedelta(seconds=total_seconds * time_fraction)
                    inserted_time = current_time + delta_seconds

                    inserted_times.append(inserted_time)
                    inserted_levels.append(inserted_level)

                # 插入新点
                final_times = (
                        final_times[:i + 1] + inserted_times + final_times[i + 1:]
                )
                final_levels = (
                        final_levels[:i + 1] + inserted_levels + final_levels[i + 1:]
                )

                # 跳过已经插入的点
                i += num_points_to_insert + 1
                continue

        # 处理下一对点
        i += 1

    return final_times, final_levels


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
                                 date_column='日期', level_column='水位',
                                 selected_date_column='取点日期', selected_level_column='取点水位'):
    """
    将选择的点添加到Excel文件中

    参数:
    input_file (str): 输入Excel文件路径
    output_file (str): 输出Excel文件路径
    selected_times (list): 选择的时间点
    selected_levels (list): 对应的水位值
    date_column (str): 日期列的列名
    level_column (str): 水位列的列名
    selected_date_column (str): 取点日期列的列名
    selected_level_column (str): 取点水位列的列名
    """
    try:
        # 读取原始数据
        df = pd.read_excel(input_file)

        # 确保日期列是datetime类型
        df[date_column] = pd.to_datetime(df[date_column])

        # 创建新列，初始化为NaN
        df[selected_date_column] = np.nan
        df[selected_level_column] = np.nan

        # 将选择的点添加到新列中
        for time, level in zip(selected_times, selected_levels):
            mask = df[date_column] == time
            if mask.any():
                df.loc[mask, selected_date_column] = time.strftime('%Y-%m-%d')
                df.loc[mask, selected_level_column] = level

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
    ##########################################################################################################
    print("=== 原始特征线读取 ===")

    # 获取当前目录
    current_dir = os.getcwd()

    # 默认输入文件
    default_input_file = os.path.join(current_dir, "原始特征线.xlsx")

    # 获取输入文件路径
    input_file = input(f"请输入Excel文件路径（默认为: {default_input_file}）: ")
    if not input_file:
        input_file = default_input_file

    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 文件 '{input_file}' 不存在")
        sys.exit(1)

    # 读取水位数据
    origin_time_series, origin_water_levels = read_water_level_from_excel(input_file)

    if not origin_time_series or not origin_water_levels:
        print("无法读取有效的水位数据，程序退出。")
        sys.exit(1)

    print(f"成功读取 {len(time_series)} 个数据点")

    ##########################################################################################################


    # 从用户输入获取参数
    try:
        peak_threshold_input = input("请输入波峰阈值（米），低于此值的波峰将被忽略，直接回车则不设置阈值: ")
        peak_threshold = float(peak_threshold_input) if peak_threshold_input else None

        valley_threshold_input = input("请输入波谷阈值（米），高于此值的波谷将被忽略，直接回车则不设置阈值: ")
        valley_threshold = float(valley_threshold_input) if valley_threshold_input else None

        max_interval_days = int(input("请输入最大插值时间间隔（天），默认为30: ") or "30")
        max_level_diff = float(input("请输入最大插值水位差（米），默认为10: ") or "10")
    except ValueError:
        print("输入无效，使用默认值")
        peak_threshold = None
        valley_threshold = None
        max_interval_days = 30
        max_level_diff = 10

    # 1. 先提取波峰和波谷
    peaks_times, peaks_levels, valleys_times, valleys_levels = find_peaks_and_valleys(
        time_series, water_levels, peak_threshold, valley_threshold
    )


    # 2. 合并并按时间排序
    sorted_times, sorted_levels = merge_and_sort_points(origin_time_series, origin_water_levels,
        peaks_times, peaks_levels, valleys_times, valleys_levels
    )

    # 3. 第一次插值：基于时间间隔
    time_interpolated_times, time_interpolated_levels = interpolate_by_time(
        sorted_times, sorted_levels, max_interval_days
    )

    # 4. 第二次插值：基于水位差
    final_times, final_levels = interpolate_by_level(
        time_interpolated_times, time_interpolated_levels, max_level_diff
    )

    # 打印结果
    print(f"\n共找到 {len(peaks_times)} 个波峰")
    for time, level in zip(peaks_times, peaks_levels):
        print(f"{time.strftime('%Y-%m-%d')}: {level:.2f} 米")

    print(f"\n共找到 {len(valleys_times)} 个波谷")
    for time, level in zip(valleys_times, valleys_levels):
        print(f"{time.strftime('%Y-%m-%d')}: {level:.2f} 米")

    print(f"\n第一次插值（时间间隔）后: {len(time_interpolated_times)} 个点")
    for time, level in zip(time_interpolated_times, time_interpolated_levels):
        print(f"{time.strftime('%Y-%m-%d')}: {level:.2f} 米")
    print(f"第二次插值（水位差）后: {len(final_times)} 个点")
    for time, level in zip(final_times, final_levels):
        # 打印结果时显示小时、分钟和秒
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {level:.2f} 米")
    # 默认输出文件
    base_name, ext = os.path.splitext(input_file)
    default_output_file = f"{base_name}_取点{ext}"

    # 获取输出文件路径
    output_file = input(f"请输入输出Excel文件路径（默认为: {default_output_file}）: ")
    if not output_file:
        output_file = default_output_file

    # 添加选择的点到Excel文件
    add_selected_points_to_excel(
        input_file, output_file,
        final_times, final_levels
    )


if __name__ == "__main__":
    main()    