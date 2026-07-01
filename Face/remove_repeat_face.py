def normalize_face_nodes(nodes):
    """
    优化版本：标准化面节点顺序
    支持正向和反向顺序
    """
    if not nodes:
        return tuple()

    n = len(nodes)
    double_nodes = nodes + nodes

    # 考虑正向和反向两种顺序
    all_representations = []

    # 正向循环
    for i in range(n):
        rep = tuple(double_nodes[i:i + n])
        all_representations.append(rep)

    # 反向循环（面的另一面）
    reversed_nodes = list(reversed(nodes))
    double_reversed = reversed_nodes + reversed_nodes
    for i in range(n):
        rep = tuple(double_reversed[i:i + n])
        all_representations.append(rep)

    # 返回最小表示
    return min(all_representations)


def remove_duplicate_faces_with_neighbors(faces):
    """
    去重面并合并邻居单元信息

    规则：
    1. 第一次出现的面：保留neighbor_cell1，neighbor_cell2=0
    2. 重复的面：将其neighbor_cell1赋值给已存在面的neighbor_cell2

    参数:
        faces: 包含face对象的列表

    返回:
        unique_faces: 去重后的faces列表
        duplicate_map: 重复面映射关系 {重复面ID: 原始面ID}
    """
    face_dict = {}  # key: 标准化节点, value: (face对象, 是否已设置neighbor_cell2)
    unique_faces = []
    duplicate_map = {}

    # 第一次遍历：处理所有面
    for face in faces:
        normalized = normalize_face_nodes(face.nodes)

        if normalized in face_dict:
            # 重复面
            existing_face, has_neighbor2 = face_dict[normalized]

            if not has_neighbor2:
                # 如果原始面还没有neighbor_cell2，使用当前面的neighbor_cell1
                existing_face.neighbor_cell2 = face.neighbor_cell1
                face_dict[normalized] = (existing_face, True)  # 标记已设置
                duplicate_map[face.id] = existing_face.id
            else:
                # 如果原始面已经有neighbor_cell2了，当前面不处理（或者可以记录日志）
                print(f"警告: 面 {face.id} 是 {existing_face.id} 的重复，但原始面已设置neighbor_cell2")
                duplicate_map[face.id] = existing_face.id
        else:
            # 第一次出现
            face_dict[normalized] = (face, False)  # 标记尚未设置neighbor_cell2

    # 第二次遍历：收集唯一面并重新编号
    new_id_counter = 1
    for normalized, (face, _) in face_dict.items():
        # 创建新的face对象，保持原邻居信息，重新编号
        new_face = Face(
            id=new_id_counter,
            nodes=face.nodes,
            neighbor_cell1=face.neighbor_cell1,
            neighbor_cell2=face.neighbor_cell2
        )
        unique_faces.append(new_face)
        new_id_counter += 1

    return unique_faces, duplicate_map


def remove_duplicate_faces_comprehensive(faces):
    """
    综合版本：处理所有重复情况，确保每个面有两个邻居

    规则：
    1. 第一次出现的面：作为主面
    2. 第二次出现的重复面：将其neighbor_cell1作为主面的neighbor_cell2
    3. 第三次及以后出现的重复面：忽略（或者可记录日志）

    返回:
        unique_faces: 去重并重新编号后的faces列表
        processing_info: 处理过程中的详细信息
    """
    # 按标准化节点分组
    groups = {}

    for face in faces:
        normalized = normalize_face_nodes(face.nodes)

        if normalized not in groups:
            groups[normalized] = []

        groups[normalized].append(face)

    # 处理每个分组
    unique_faces = []
    processing_info = {
        'processed_faces': [],
        'duplicate_pairs': [],
        'orphaned_faces': []  # 无法处理的重复面（超过2个重复）
    }

    new_id_counter = 1

    for normalized, face_list in groups.items():
        if len(face_list) == 1:
            # 唯一面，邻居2为0
            face = face_list[0]
            new_face = Face(
                id=new_id_counter,
                nodes=face.nodes,
                neighbor_cell1=face.neighbor_cell1,
                neighbor_cell2=0
            )
            unique_faces.append(new_face)

            processing_info['processed_faces'].append({
                'original_id': face.id,
                'new_id': new_id_counter,
                'neighbor1': face.neighbor_cell1,
                'neighbor2': 0,
                'type': 'unique'
            })

            new_id_counter += 1

        elif len(face_list) == 2:
            # 刚好一对重复面
            face1, face2 = face_list[0], face_list[1]

            # 确定哪个是第一个出现的（保持neighbor_cell1不变）
            # 这里我们假设face1是第一个出现的
            new_face = Face(
                id=new_id_counter,
                nodes=face1.nodes,
                neighbor_cell1=face1.neighbor_cell1,
                neighbor_cell2=face2.neighbor_cell1
            )
            unique_faces.append(new_face)

            processing_info['processed_faces'].append({
                'original_id': face1.id,
                'new_id': new_id_counter,
                'neighbor1': face1.neighbor_cell1,
                'neighbor2': face2.neighbor_cell1,
                'type': 'primary'
            })
            processing_info['duplicate_pairs'].append({
                'primary_id': face1.id,
                'duplicate_id': face2.id,
                'new_id': new_id_counter
            })

            new_id_counter += 1

        else:
            # 超过2个重复面，取前两个，其他的标记为无法处理
            face1, face2 = face_list[0], face_list[1]

            new_face = Face(
                id=new_id_counter,
                nodes=face1.nodes,
                neighbor_cell1=face1.neighbor_cell1,
                neighbor_cell2=face2.neighbor_cell1
            )
            unique_faces.append(new_face)

            processing_info['processed_faces'].append({
                'original_id': face1.id,
                'new_id': new_id_counter,
                'neighbor1': face1.neighbor_cell1,
                'neighbor2': face2.neighbor_cell1,
                'type': 'primary_multi'
            })

            # 记录其他重复面
            for i, extra_face in enumerate(face_list[2:], 2):
                processing_info['orphaned_faces'].append({
                    'original_id': extra_face.id,
                    'primary_id': face1.id,
                    'new_id': new_id_counter,
                    'position': i + 1
                })

            new_id_counter += 1

    return unique_faces, processing_info


# 使用示例
class Face:
    """面的类定义，包含邻居单元信息"""

    def __init__(self, id, nodes, neighbor_cell1, neighbor_cell2=0):
        self.id = id
        self.nodes = nodes  # 节点编号列表
        self.neighbor_cell1 = neighbor_cell1  # 邻居单元1的ID
        self.neighbor_cell2 = neighbor_cell2  # 邻居单元2的ID

    def __repr__(self):
        neighbors = f"n1={self.neighbor_cell1}, n2={self.neighbor_cell2}"
        return f"Face(id={self.id}, nodes={self.nodes}, {neighbors})"


# 测试数据
# 创建一些测试面，每个面都有neighbor_cell1
faces = [
    Face(1, [1, 2, 3, 4], 101),  # 面1，邻居单元101
    Face(2, [2, 3, 4, 1], 102),  # 与面1相同，节点顺序不同，邻居单元102
    Face(3, [5, 6, 7, 8], 201),  # 面3，邻居单元201
    Face(4, [6, 7, 8, 5], 202),  # 与面3相同，节点顺序不同，邻居单元202
    Face(5, [9, 10, 11, 12], 301),  # 面5，唯一面，邻居单元301
    Face(6, [1, 2, 3, 4], 103),  # 与面1相同，邻居单元103（第三个重复）
    Face(7, [13, 14, 15, 16], 401),  # 面7，唯一面，邻居单元401
    Face(8, [5, 6, 7, 8], 203),  # 与面3相同，邻居单元203（第三个重复）
]

print("=" * 70)
print("原始faces列表（每个面有neighbor_cell1，neighbor_cell2为0）:")
print("=" * 70)
for face in faces:
    print(f"  {face}")

print("\n" + "=" * 70)
print("方法1: 简单合并邻居信息")
print("=" * 70)

unique_faces1, dup_map1 = remove_duplicate_faces_with_neighbors(faces)

print("去重合并后的faces列表:")
for face in unique_faces1:
    print(f"  {face}")

print("\n重复面映射关系:")
for dup_id, primary_id in dup_map1.items():
    print(f"  Face {dup_id} → Face {primary_id}")

print("\n" + "=" * 70)
print("方法2: 综合处理（处理所有情况）")
print("=" * 70)

unique_faces2, proc_info = remove_duplicate_faces_comprehensive(faces)

print("去重合并后的faces列表:")
for face in unique_faces2:
    print(f"  {face}")

print(f"\n处理统计:")
print(f"  原始面数: {len(faces)}")
print(f"  处理后面数: {len(unique_faces2)}")
print(f"  重复对数量: {len(proc_info['duplicate_pairs'])}")
print(f"  无法处理的面: {len(proc_info['orphaned_faces'])}")

if proc_info['orphaned_faces']:
    print(f"\n警告: 以下面因为超过2个重复而无法处理:")
    for orphan in proc_info['orphaned_faces']:
        print(f"  Face {orphan['original_id']}: 第{orphan['position']}个重复面，原始面Face {orphan['primary_id']}")

# 验证处理结果
print("\n" + "=" * 70)
print("验证邻居信息是否正确合并:")
print("=" * 70)

# 创建一个查找字典，便于验证
face_dict = {tuple(f.nodes): f for f in faces}

for unique_face in unique_faces2:
    # 找到对应的原始面
    original_faces = []
    for f in faces:
        if normalize_face_nodes(f.nodes) == normalize_face_nodes(unique_face.nodes):
            original_faces.append(f)

    print(f"\nFace {unique_face.id} (nodes={unique_face.nodes}):")
    print(f"  邻居信息: cell1={unique_face.neighbor_cell1}, cell2={unique_face.neighbor_cell2}")

    if len(original_faces) == 1:
        print(f"  原始面: Face {original_faces[0].id} (cell1={original_faces[0].neighbor_cell1})")
        print(f"  状态: 唯一面")
    elif len(original_faces) == 2:
        print(f"  原始面: Face {original_faces[0].id} (cell1={original_faces[0].neighbor_cell1})")
        print(f"           Face {original_faces[1].id} (cell1={original_faces[1].neighbor_cell1})")
        print(f"  状态: 已正确合并邻居信息")
    else:
        print(f"  原始面: {[f.id for f in original_faces]}")
        print(f"  状态: 有{len(original_faces)}个重复，取了前2个的邻居信息")