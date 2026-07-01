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