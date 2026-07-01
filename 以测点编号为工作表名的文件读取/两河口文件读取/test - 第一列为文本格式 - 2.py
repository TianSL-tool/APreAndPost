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


def convert_to_target_date(date_str):
    """
    尝试多种格式将文本转换为日期，最终统一输出为“年/月/日”格式（如2021/1/2）
    返回：pandas日期对象或原始值（转换失败时）
    """
    # 定义原始文本可能的日期格式
    possible_formats = [
        '%Y-%m-%d', '%Y/%m/%d', '%Y年%m月%d日',
        '%m-%d-%Y', '%m/%d/%Y', '%d-%m-%Y', '%d/%m/%Y',
        '%Y%m%d', '%y-%m-%d', '%y/%m/%d',
        '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S'
    ]

    date_str_stripped = str(date_str).strip()
    for fmt in possible_formats:
        try:
            # 转换为pandas日期对象
            return pd.to_datetime(date_str_stripped, format=fmt, errors='raise').date()
        except (ValueError, TypeError):
            continue

    # 转换失败，返回原始值
    return date_str_stripped


def read_sheet(filename, l, n):
    # 读取包含多个工作表的 Excel 文件
    excel_file = pd.ExcelFile(filename)
    sheet_names = excel_file.sheet_names
    all_data = []
    conversion_errors = {}  # 记录转换失败的日期

    # 遍历每个工作表
    for sheet_name in sheet_names:
        print(f"正在处理测点工作表：{sheet_name}")
        # 读取数据：跳过前l行
        df = excel_file.parse(sheet_name, skiprows=l, dtype=str)

        # 转换日期列（第一列）
        raw_date_col = df.iloc[:, 0]
        converted_dates = []

        for row_idx, raw_date in enumerate(raw_date_col):
            converted_date = convert_to_target_date(raw_date)

            # 修改：使用更通用的方式判断是否为日期类型
            is_date = False
            if isinstance(converted_date, pd.Timestamp):
                is_date = True
            # 检查是否为datetime.date对象
            elif 'datetime.date' in str(type(converted_date)):
                is_date = True

            # 记录转换失败的情况
            if not is_date:
                if sheet_name not in conversion_errors:
                    conversion_errors[sheet_name] = []
                actual_row = l + row_idx + 1
                conversion_errors[sheet_name].append(f"行{actual_row}：{raw_date}")

            converted_dates.append(converted_date)

        # 提取位移数据（第n列）
        displacement_col = pd.to_numeric(df.iloc[:, n - 1], errors='coerce')

        # 构建当前测点的DataFrame
        current_df = pd.DataFrame({
            f'{sheet_name}_时间': converted_dates,
            f'{sheet_name}_位移': displacement_col
        })

        # 将日期列强制转换为pandas日期类型
        current_df[f'{sheet_name}_时间'] = pd.to_datetime(
            current_df[f'{sheet_name}_时间'],
            errors='coerce'
        )

        all_data.append(current_df)

    # 合并所有测点数据
    final_df = pd.concat(all_data, axis=1)

    # 写入Excel：指定日期格式为“YYYY/M/D”
    with pd.ExcelWriter(f'out{filename}', engine='openpyxl') as writer:
        final_df.to_excel(writer, sheet_name='所有测点数据', index=False)

        # 设置日期列的格式
        worksheet = writer.sheets['所有测点数据']

        for col_idx, col_name in enumerate(final_df.columns):
            if '时间' in col_name:
                date_col_letter = chr(65 + col_idx)
                for row in worksheet.iter_rows(
                        min_row=2,
                        max_row=len(final_df) + 1,
                        min_col=col_idx + 1,
                        max_col=col_idx + 1
                ):
                    for cell in row:
                        cell.number_format = 'YYYY/M/D'

    # 打印结果信息
    print(f"\n数据处理完成！输出文件：out{filename}")
    if conversion_errors:
        print("\n⚠️  部分日期转换失败：")
        for sheet, errors in conversion_errors.items():
            print(f"测点{sheet}：共{len(errors)}个错误")
            for err in errors[:3]:
                print(f"  - {err}")
            if len(errors) > 3:
                print(f"  - ... 还有{len(errors) - 3}个错误未显示")
    else:
        print("✅ 所有日期均成功转换为“2021/1/2”格式")


if __name__ == '__main__':
    son_filename, l, r = read_control_file(filename='read_control.txt')
    for i in range(len(son_filename)):
        read_sheet(son_filename[i], l[i], r[i])
