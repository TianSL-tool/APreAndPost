import h5py
import os


def merge_h5_files_keep_both_frames(file1, file2, output_file):
    """
    合并两个HDF5文件，保留第一个文件的完整结构和frames组，
    同时将第二个文件的frames组合并到输出文件中

    参数:
    file1 (str): 第一个输入HDF5文件路径（提供基础结构和frames组）
    file2 (str): 第二个输入HDF5文件路径（提供额外的frames组内容）
    output_file (str): 输出HDF5文件路径
    """
    # 检查输入文件是否存在
    for f in [file1, file2]:
        if not os.path.exists(f):
            raise FileNotFoundError(f"错误: 文件 {f} 不存在")

    print(f"开始合并文件:")
    print(f"  1. {file1} (基础结构和frames组)")
    print(f"  2. {file2} (仅合并frames组内容)")
    print(f"输出文件: {output_file}")

    # 打开第一个文件作为基础
    with h5py.File(file1, 'r') as f1, h5py.File(output_file, 'w') as out_f:
        # 复制第一个文件的所有内容到输出文件
        print("正在复制第一个文件的完整结构...")
        for name, obj in f1.items():
            f1.copy(name, out_f)

        # 处理第二个文件的frames组
        print("正在合并第二个文件的frames组内容...")
        with h5py.File(file2, 'r') as f2:
            if 'frames' not in f2:
                print(f"警告: 第二个文件 {file2} 不包含frames组，仅使用第一个文件的frames组")
                return

            input_frames = f2['frames']
            output_frames = out_f['frames']

            # 遍历第二个文件中的所有frame
            for frame_name in input_frames.keys():
                # 检查frame是否已存在于输出文件中
                if frame_name in output_frames:
                    print(f"警告: frame {frame_name} 已存在于输出文件中，将被覆盖")
                    del output_frames[frame_name]

                # 复制frame组及其所有内容
                input_frames.copy(frame_name, output_frames)

        print(f"合并完成!")


def get_valid_file_path(prompt, check_exists=True):
    """获取有效的文件路径输入"""
    while True:
        file_path = input(prompt).strip()
        if not file_path:
            print("文件名不能为空，请重新输入。")
            continue

        # 如果需要检查文件是否存在
        if check_exists and not os.path.exists(file_path):
            print(f"文件 '{file_path}' 不存在，请重新输入。")
            continue

        return file_path


def main():
    print("==== HDF5文件合并工具 ====")

    # 获取第一个输入文件
    file1 = get_valid_file_path("请输入第一个HDF5文件路径(提供基础结构和frames组): ")

    # 获取第二个输入文件
    file2 = get_valid_file_path("请输入第二个HDF5文件路径(提供额外frames组内容): ")

    # 获取输出文件路径
    output_file = get_valid_file_path("请输入输出HDF5文件路径: ", check_exists=False)

    # 确保输出文件有.h5扩展名


class MergeH5:
    def calc(self, file1="static1.h5", file2="static2.h5", output_file="static.h5"):

        if not output_file.lower().endswith('.h5'):
            output_file += '.h5'
            print(f"注意: 自动添加了.h5扩展名，输出文件将为: {output_file}")

        try:
            merge_h5_files_keep_both_frames(file1, file2, output_file)
            print("合并完成")
        except Exception as e:
            print(f"合并过程中发生错误: {str(e)}")


