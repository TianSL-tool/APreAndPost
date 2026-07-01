import pandas as pd
from basemethod.base_method import read_and_clean_file
import numpy as np


def read_control_file(filename='read_control.txt'):
    cleaned_lines = read_and_clean_file(filename)

    # 获取切割面个数
    num_filename = int(cleaned_lines.pop(0))
    son_filename = []
    l = []
    r = []
    for _ in range(num_filename):
        # 读取范围信息
        son_filename.extend(map(str, cleaned_lines.pop(0).split()))
        l.extend(map(int, cleaned_lines.pop(0).split()))
        r.extend(map(int, cleaned_lines.pop(0).split()))
    print(son_filename)
    print(l)
    print(r)
    return son_filename, l, r


def convert_to_date(date_str):
    """尝试多种日期格式转换，提高成功率"""
    # 定义可能的日期格式
    date_formats = [
        '%Y-%m-%d', '%Y/%m/%d', '%Y年%m月%d日',
        '%m-%d-%Y', '%m/%d/%Y', '%d-%m-%Y', '%d/%m/%Y',
        '%Y%m%d', '%y-%m-%d', '%y/%m/%d'
    ]

    for fmt in date_formats:
        try:
            return pd.to_datetime(date_str, format=fmt)
        except:
            continue

    # 如果所有格式都尝试失败，返回原始值和转换失败标记
    return (date_str, False)


def read_sheet(filename, l, n):
    # 读取包含多个工作表的 Excel 文件
    excel_file = pd.ExcelFile(filename)

    # 获取所有表名（测点编号）
    sheet_names = excel_file.sheet_names

    # 用于存储每个测点的时间和位移数据
    all_data = []
    # 记录转换失败的日期
    conversion_errors = {}

    # 遍历每个工作表
    for sheet_name in sheet_names:
        # 读取工作表数据，跳过前 l 行
        df = excel_file.parse(sheet_name, skiprows=l)
        print(f"处理工作表: {sheet_name}")

        # 获取原始时间列
        raw_dates = df.iloc[:, 0].astype(str)  # 确保为字符串类型
        converted_dates = []

        # 逐行转换日期
        for idx, date_str in enumerate(raw_dates):
            result = convert_to_date(date_str.strip())  # 去除前后空格
            if isinstance(result, tuple):
                # 转换失败
                converted_dates.append(result[0])  # 保留原始值
                if sheet_name not in conversion_errors:
                    conversion_errors[sheet_name] = []
                conversion_errors[sheet_name].append(f"行 {idx + 1 + l}: {date_str}")  # 加上跳过的行数
            else:
                # 转换成功
                converted_dates.append(result.strftime('%Y-%m-%d'))

        # 提取位移数据
        displacements = df.iloc[:, n - 1]

        # 构建当前测点的数据 DataFrame
        current_data = pd.DataFrame({
            f'{sheet_name}_时间': converted_dates,
            f'{sheet_name}': displacements
        })

        # 将当前测点的数据添加到总数据列表中
        all_data.append(current_data)

    # 打印转换错误信息
    if conversion_errors:
        print("\n日期转换警告:")
        for sheet, errors in conversion_errors.items():
            print(f"工作表 {sheet} 中发现 {len(errors)} 个无法转换的日期:")
            for err in errors[:5]:  # 只显示前5个错误
                print(f"  - {err}")
            if len(errors) > 5:
                print(f"  - 还有 {len(errors) - 5} 个错误未显示")

    # 将所有测点的数据按列拼接
    final_df = pd.concat(all_data, axis=1)

    # 将最终数据写入新的 Excel 文件
    final_df.to_excel('out' + filename, sheet_name='所有测点数据', index=False)

    print(f'\n数据处理完成，已保存到 out{filename} 文件中。')


if __name__ == '__main__':
    son_filename, l, r = read_control_file(filename='read_control.txt')
    for i in range(len(son_filename)):
        read_sheet(son_filename[i], l[i], r[i])
