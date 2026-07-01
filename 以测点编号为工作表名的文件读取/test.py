import pandas as pd
from basemethod.base_method import read_and_clean_file
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

