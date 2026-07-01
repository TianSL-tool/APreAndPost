import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
import matplotlib.dates as mdates
import matplotlib
import os
import matplotlib.font_manager as fm


# 设置Matplotlib环境（解决中文显示和后端问题）
def setup_matplotlib_env():
    # 使用Agg后端，完全无GUI依赖
    matplotlib.use('Agg')

    # 解决中文显示问题 - 尝试多种常见中文字体
    font_candidates = [
        "Microsoft YaHei",  # 微软雅黑
        "SimHei",  # 黑体
        "SimSun",  # 宋体
        "KaiTi",  # 楷体
        "Arial Unicode MS"  # 通用Unicode字体
    ]

    # 修复：正确获取系统可用字体名称
    font_names = set()
    for font_path in fm.findSystemFonts(fontpaths=None, fontext='ttf'):
        try:
            # 从字体文件路径获取字体名称
            font_prop = fm.FontProperties(fname=font_path)
            font_names.add(font_prop.get_name())
        except Exception:
            continue
    available_fonts = list(font_names)

    selected_font = None
    # 寻找第一个可用的中文字体
    for font in font_candidates:
        if any(font.lower() in available.lower() for available in available_fonts):
            selected_font = font
            break

    # 设置字体
    if selected_font:
        plt.rcParams["font.family"] = selected_font
        print(f"已使用中文字体: {selected_font}")
    else:
        print("警告: 未找到可用中文字体，中文可能无法正常显示")

    # 解决负号显示问题
    plt.rcParams['axes.unicode_minus'] = False


# 从Excel读取水位数据
def read_water_level_from_excel(file_path, time_col='时间', level_col='水位'):
    try:
        # 尝试不同引擎读取Excel文件
        try:
            df = pd.read_excel(file_path, engine='openpyxl')
        except Exception:
            df = pd.read_excel(file_path, engine='xlrd')

        # 检查必要的列是否存在
        if time_col not in df.columns:
            raise ValueError(f"Excel文件中未找到名为'{time_col}'的列")
        if level_col not in df.columns:
            raise ValueError(f"Excel文件中未找到名为'{level_col}'的列")

        # 转换时间列并清理数据
        df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
        initial_count = len(df)

        # 移除无效数据
        df = df.dropna(subset=[time_col, level_col])
        df = df.sort_values(by=time_col)

        # 输出数据清理信息
        removed_count = initial_count - len(df)
        if removed_count > 0:
            print(f"已移除{removed_count}条无效数据（时间或水位值缺失）")

        # 格式化结果
        df = df.set_index(time_col)[[level_col]]
        df.columns = ['water_level']

        print(f"成功读取有效数据: {len(df)}条")
        print(f"时间范围: {df.index.min()} 至 {df.index.max()}")
        return df

    except Exception as e:
        print(f"读取Excel文件出错: {str(e)}")
        return None


# 多种平滑方法实现
def smooth_water_level(data, method='savitzky-golay', **kwargs):
    """
    水位数据平滑处理

    参数:
        data: 原始水位数据
        method: 平滑方法，可选 'savitzky-golay', 'moving-average', 'gaussian'
        kwargs: 各方法对应的参数
    """
    if method == 'savitzky-golay':
        window_size = kwargs.get('window_size', 15)
        polyorder = kwargs.get('polyorder', 2)
        # 确保窗口大小为奇数
        if window_size % 2 == 0:
            window_size += 1
        return savgol_filter(data, window_size, polyorder)

    elif method == 'moving-average':
        window_size = kwargs.get('window_size', 15)
        # 使用pandas的滚动平均
        return pd.Series(data).rolling(window=window_size, center=True, min_periods=1).mean().values

    elif method == 'gaussian':
        sigma = kwargs.get('sigma', 2)
        from scipy.ndimage import gaussian_filter1d
        return gaussian_filter1d(data, sigma)

    else:
        raise ValueError(f"不支持的平滑方法: {method}")


# 绘制并保存水位曲线
def plot_water_level(original_df, smoothed_data=None, method_name="平滑方法", save_path='水位曲线.png'):
    try:
        # 创建图形
        fig, ax = plt.subplots(figsize=(16, 9), dpi=120)

        # 绘制原始数据
        ax.plot(original_df.index, original_df['water_level'],
                label='原始水位数据', alpha=0.6, color='#666666', linewidth=1)

        # 绘制平滑数据
        if smoothed_data is not None:
            ax.plot(original_df.index, smoothed_data,
                    label=f'{method_name}处理后', color='#2c7fb8', linewidth=2)

        # 设置图表属性
        ax.set_title('水位时间曲线', fontsize=18, pad=20)
        ax.set_xlabel('时间', fontsize=14, labelpad=10)
        ax.set_ylabel('水位 (m)', fontsize=14, labelpad=10)

        # 格式化时间轴
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=10))
        plt.xticks(rotation=45, ha='right')

        # 添加网格和图例
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend(fontsize=12)

        # 调整布局并保存
        plt.tight_layout()
        plt.savefig(save_path, bbox_inches='tight')
        plt.close(fig)
        print(f"图表已保存至: {os.path.abspath(save_path)}")

    except Exception as e:
        print(f"绘图时出错: {str(e)}")


# 主函数
def main():
    # 初始化环境
    setup_matplotlib_env()

    # 配置文件路径 - 请根据实际情况修改
    input_file = "水位.xlsx"  # 输入Excel文件路径
    output_file = "smoothed_water_level.xlsx"  # 输出Excel文件路径

    # 读取数据
    water_level_df = read_water_level_from_excel(
        file_path=input_file,
        time_col='日期',  # 请修改为实际的时间列名
        level_col='水位'  # 请修改为实际的水位列名
    )

    if water_level_df is not None and not water_level_df.empty:
        # 平滑处理 - 可尝试不同方法
        smooth_method = 'savitzky-golay'  # 可选: 'savitzky-golay', 'moving-average', 'gaussian'
        smoothed_data = smooth_water_level(
            water_level_df['water_level'].values,
            method=smooth_method,
            window_size=50,  # 窗口大小，越大平滑效果越强
            polyorder=2  # 仅用于savitzky-golay方法
        )

        # 保存处理后的数据
        result_df = water_level_df.copy()
        result_df['smoothed_water_level'] = smoothed_data
        try:
            result_df.to_excel(output_file, engine='openpyxl')
            print(f"处理后的数据已保存至: {os.path.abspath(output_file)}")
        except Exception:
            result_df.to_excel(output_file, engine='xlrd')
            print(f"处理后的数据已保存至: {os.path.abspath(output_file)}")

        # 绘制并保存图表
        plot_water_level(
            original_df=water_level_df,
            smoothed_data=smoothed_data,
            method_name=smooth_method,
            save_path='水位曲线对比图.png'
        )

    print("处理完成!")


if __name__ == "__main__":
    main()
