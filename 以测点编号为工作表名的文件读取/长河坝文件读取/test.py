import pandas as pd
def read_and_clean_file(file_path):
    """
    支持GBK/UTF-8编码，忽略任何位置的//后注释，返回处理后的行列表
    """
    # 常见编码列表，优先尝试GBK（解决中文编码问题）
    encodings = ['gbk', 'utf-8', 'gb2312']
    lines = None

    # 尝试不同编码读取文件，直到成功或遍历完所有编码
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                lines = file.readlines()
            break  # 编码正确，跳出循环
        except UnicodeDecodeError:
            continue  # 编码错误，尝试下一个
        except FileNotFoundError:
            print(f"文件 {file_path} 未找到。")
            return []
        except Exception as e:
            print(f"用{encoding}编码读取文件时出错：{e}")
            continue

    # 所有编码都尝试失败
    if lines is None:
        print(f"文件 {file_path} 无法解码，请确认文件编码格式。")
        return []

    # 处理注释和空行
    cleaned_lines = []
    for line in lines:
        # 忽略//后的所有内容，保留前面的有效部分
        valid_part = line.split('//')[0].strip()
        if valid_part:  # 过滤空行和全注释行
            cleaned_lines.append(valid_part)
    return cleaned_lines

def read_and_clean_file_to_values(file_path):
    """
    支持GBK/UTF-8编码，忽略任何位置的//后注释，返回按顺序的数值列表
    """
    encodings = ['gbk', 'utf-8', 'gb2312']
    lines = None

    # 尝试不同编码读取文件
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                lines = file.readlines()
            break
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            print(f"文件 {file_path} 未找到")
            return []
        except Exception as e:
            print(f"用{encoding}编码读取文件时出错：{e}")
            continue

    if lines is None:
        print(f"文件 {file_path} 无法解码，请确认文件编码格式。")
        return []

    # 处理注释，提取有效内容
    all_valid_content = []
    for line in lines:
        valid_part = line.split('//')[0].strip()
        if valid_part:
            all_valid_content.append(valid_part)

    # 拆分为数值列表
    merged_content = ' '.join(all_valid_content)
    all_values = [token.strip() for token in merged_content.split() if token.strip()]
    return all_values


def read_control_file(filename = 'read_control.txt'):
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
    return son_filename,l,r

def read_sheet(filename,l,n):
    # 读取包含多个工作表的 Excel 文件
    excel_file = pd.ExcelFile(filename)

    # 获取所有表名（测点编号）
    sheet_names = excel_file.sheet_names

    # 用于存储每个测点的时间和位移数据
    all_data = []

    # 遍历每个工作表
    for sheet_name in sheet_names:
        # 读取工作表数据，跳过前 l 行
        df = excel_file.parse(sheet_name, skiprows=l)
        print(sheet_name)
        # 获取监测时间和位移列
        time_series = df.iloc[:, 0]
        displacements = df.iloc[:, n - 1]

        # 构建当前测点的数据 DataFrame
        current_data = pd.DataFrame({
            f'{sheet_name}_时间': time_series,
            f'{sheet_name}': displacements
        })

        # 将当前测点的数据添加到总数据列表中
        all_data.append(current_data)

    # 将所有测点的数据按列拼接
    final_df = pd.concat(all_data, axis=1)

    # 将最终数据写入新的 Excel 文件
    final_df.to_excel('out' + filename, sheet_name='所有测点数据', index=False)

    print('数据处理完成，已保存到 out' + filename + '文件中。')


if __name__ == '__main__':
   son_filename,l,r = read_control_file(filename='read_control.txt')
   for i in range(len(son_filename)):
        read_sheet(son_filename[i],l[i],r[i])

