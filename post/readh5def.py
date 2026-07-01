#
# import h5py
# import time
# import pandas as pd
# from pre_group.pre import read_grid_file
#
# def parse_control_file(control_file):
#     """解析控制文件，支持忽略空行和注释"""
#     with open(control_file, 'r') as file:
#         lines = file.readlines()
#
#     output_nodes = []
#     output_elements = []
#     output_steps = []
#     base_node = None
#     podu = 0.0
#     initial_stress = 1
#     initial_strain = 1
#     for i, line in enumerate(lines):
#         line = line.strip()
#         if not line or line.startswith('#') or line.startswith('//'):
#             continue
#
#         if "output node number" in line:
#             num_nodes = int(line.split('=')[1].strip())
#             count = 0
#             valid_nodes = 0
#             while valid_nodes < num_nodes:
#                 next_line = lines[i + count + 1].strip()
#                 count += 1
#                 if next_line and not next_line.startswith(('#', '//')):
#                     output_nodes.append(int(next_line))
#                     valid_nodes += 1
#
#         elif "output element number" in line:
#             num_elements = int(line.split('=')[1].strip())
#             count = 0
#             valid_elements = 0
#             while valid_elements < num_elements:
#                 next_line = lines[i + count + 1].strip()
#                 count += 1
#                 if next_line and not next_line.startswith(('#', '//')):
#                     output_elements.append(int(next_line))
#                     valid_elements += 1
#
#         elif "output step number" in line:
#             num_steps = int(line.split('=')[1].strip())
#             count = 0
#             valid_steps = 0
#             while valid_steps < num_steps:
#                 next_line = lines[i + count + 1].strip()
#                 count += 1
#                 if next_line and not next_line.startswith(('#', '//')):
#                     output_steps.append(int(next_line))
#                     valid_steps += 1
#         elif "base node" in line:
#             base_node = int(line.split('=')[1].strip())
#
#             if base_node != 0:
#                 output_nodes.append(base_node)
#
#         elif "podu" in line:
#             podu = float(line.split('=')[1].strip())
#
#         elif "initial stress" in line:
#             initial_stress = float(line.split('=')[1].strip())
#
#         elif "initial strain" in line:
#             initial_strain = float(line.split('=')[1].strip())
#
#     return output_nodes, output_elements, output_steps, base_node, podu, initial_stress, initial_strain
#
#
# def extract_data(h5_file, node_results, element_results, output_nodes, base_node, output_elements, output_file_prefix,
#                  output_steps, podu, initial_stress, initial_strain):
#     """提取指定节点的位移和单元的应力数据并保存到文件"""
#     with h5py.File(h5_file, 'r') as f:
#         frames = f['frames']
#
#         last_active_nodes = []
#         last_active_elements = {}
#
#         active_elem_indices = {}
#         for frame in sorted(frames.keys(), key=int):
#             frame_data = frames[frame]
#
#             if 'new_topology' in frame_data and 'node_ids' in frame_data['new_topology']:
#                 last_active_nodes = frame_data['new_topology/node_ids'][:]
#                 active_node_indices = {nid: i for i, nid in enumerate(last_active_nodes) if nid in output_nodes}
#
#             if len(last_active_nodes) > 0 and 'node_vars/displacement' in frame_data:
#                 node_displacement = frame_data['node_vars/displacement']
#                 for nid, index in active_node_indices.items():
#                     if index < len(node_displacement):
#                         disp = node_displacement[index]
#                         node_results[nid].disp.append(disp)
#                         node_results[nid].steps.append(frame)
#
#             if len(last_active_nodes) > 0 and 'node_vars/poressure' in frame_data:
#                 node_poressure = frame_data['node_vars/poressure']
#                 for nid, index in active_node_indices.items():
#                     if index < len(node_poressure):
#                         pore = node_poressure[index]
#                         node_results[nid].poress.append(pore)
#
#             if len(last_active_nodes) > 0 and 'node_vars/acceleration' in frame_data:
#                 node_acceleration = frame_data['node_vars/acceleration']
#                 for nid, index in active_node_indices.items():
#                     if index < len(node_acceleration):
#                         acceleration = node_acceleration[index]
#                         node_results[nid].acc.append(acceleration)
#
#             if len(last_active_nodes) > 0 and 'node_vars/velocity' in frame_data:
#                 node_velocity = frame_data['node_vars/velocity']
#                 for nid, index in active_node_indices.items():
#                     if index < len(node_velocity):
#                         velocity = node_velocity[index]
#                         node_results[nid].vel.append(velocity)
#
#             if 'parts' in frame_data:
#                 for part in frame_data['parts']:
#                     part_path = frame_data[f'parts/{part}']
#
#                     if 'elem_ids' in part_path:
#                         last_active_elements[part] = part_path['elem_ids'][:]
#                         new_active_elem_indices = {eid: i for i, eid in enumerate(last_active_elements[part]) if
#                                                    eid in output_elements}
#
#                         active_elem_indices[part] = new_active_elem_indices
#
#                     if part in last_active_elements:
#                         if 'elem_vars/stress' in part_path:
#                             elem_stress = part_path['elem_vars/stress']
#                             for eid, index in active_elem_indices[part].items():
#                                 if index < len(elem_stress):
#                                     stress = elem_stress[index]
#                                     element_results[eid].stresses.append(stress)
#                                     element_results[eid].steps.append(frame)
#
#                         if 'elem_vars/strain' in part_path:
#                             elem_strain = part_path['elem_vars/strain']
#                             for eid, index in active_elem_indices[part].items():
#                                 if index < len(elem_strain):
#                                     strain = elem_strain[index]
#                                     element_results[eid].strains.append(strain)
#
#                         if 'elem_vars/interface_stress' in part_path:
#                             elem_stress = part_path['elem_vars/interface_stress']
#                             for eid, index in active_elem_indices[part].items():
#                                 if index < len(elem_stress):
#                                     stress = elem_stress[index]
#                                     element_results[eid].stresses.append(stress)
#                                     element_results[eid].steps.append(frame)
#
#                         if 'elem_vars/interface_relative_displacement' in part_path:
#                             elem_strain = part_path['elem_vars/interface_relative_displacement']
#                             for eid, index in active_elem_indices[part].items():
#                                 if index < len(elem_strain):
#                                     strain = elem_strain[index]
#                                     element_results[eid].strains.append(strain)
#
#         for node, result in node_results.items():
#             if base_node is not None:
#                 if node != base_node:
#                     # result.disp-= node_results[base_node].disp
#                     result.disp = [[a - b for a, b in zip(row1, row2)] for row1, row2 in
#                                    zip(result.disp, node_results[base_node].disp)]
#             if result.disp:
#                 result.write_Schedule()
#
#         for elem_id, result in element_results.items():
#             result.calculate_stress_strain_variables(podu,initial_stress,initial_strain)
#             result.write_ele_Schedule()
#
#         for step in output_steps:
#             step = str(step)
#             node_file_name = f"step_{step}_node_data.txt"
#             with open(node_file_name, 'w') as node_file:
#                 node_file.write(f"Node data for step {step}:\n")
#                 for node_id, result in node_results.items():
#                     result.write_step(step,node_file)
#
#             element_file_name = f"step_{step}_element_data.txt"
#             with open(element_file_name, 'w') as element_file:
#                 element_file.write(f"Element data for step {step}:\n")
#                 for elem_id, result in element_results.items():
#                     result.write_step(step,element_file)
#
#         with open("max_node_step.dat", 'w') as node_file:
#             node_file.write(f"Node data for max :\n")
#             for node_id, result in node_results.items():
#                 result.write_max_step(node_file)
#
#         with open("max_element_step.dat", 'w') as element_file:
#             element_file.write(f"Element data for max :\n")
#             for elem_id, result in element_results.items():
#                 result.write_max_step(element_file)
#         # ========== 新增：生成节点/单元时程 Excel ==========
#         convert_schedule_files_to_excel(output_file_prefix, output_nodes, output_elements)
# import os
#
# def convert_schedule_files_to_excel(output_prefix, output_nodes, output_elements):
#     """
#     将控制文件中指定的节点时程文件（*.node）和单元时程文件（*.ele）
#     整合为一个节点 Excel 和一个单元 Excel。
#     - output_prefix : 输出 Excel 文件名前缀
#     - output_nodes  : 节点 ID 列表
#     - output_elements: 单元 ID 列表
#     文件格式假设：第一行列标题（如 Step accx accy ...），空白分隔。
#     """
#     # ----- 节点时程 -----
#     if output_nodes:
#         node_excel = f"{output_prefix}_node_schedule.xlsx"
#         with pd.ExcelWriter(node_excel, engine='openpyxl') as writer:
#             for node_id in output_nodes:
#                 fpath = f"{node_id}.node"
#                 if not os.path.isfile(fpath):
#                     continue  # 文件不存在则跳过
#                 try:
#                     df = pd.read_csv(fpath, sep=r'\s+', header=0, engine='python')
#                 except Exception:
#                     continue
#                 if df.empty:
#                     continue
#                 sheet_name = str(node_id)[:31]
#                 df.to_excel(writer, sheet_name=sheet_name, index=False)
#
#     # ----- 单元时程 -----
#     if output_elements:
#         elem_excel = f"{output_prefix}_element_schedule.xlsx"
#         with pd.ExcelWriter(elem_excel, engine='openpyxl') as writer:
#             for elem_id in output_elements:
#                 fpath = f"{elem_id}.ele"
#                 if not os.path.isfile(fpath):
#                     continue
#                 try:
#                     df = pd.read_csv(fpath, sep=r'\s+', header=0, engine='python')
#                 except Exception:
#                     continue
#                 if df.empty:
#                     continue
#                 sheet_name = str(elem_id)[:31]
#                 df.to_excel(writer, sheet_name=sheet_name, index=False)
#
# class ReadH5Calc:
#     def readh5(self, control_file="control.txt", h5_file="static.h5", output_file_prefix="output",
#                gril_file="Inimesh.dat"):
#         start_time = time.time()
#
#         output_nodes, output_elements, output_steps, base_node, podu, initial_stress, initial_strain = parse_control_file(
#             control_file)
#         print("读取控制文件完成")
#         _, _, nodes_map, elements_map = read_grid_file(gril_file)
#         node_results = {node_id: nodes_map[node_id] for node_id in output_nodes}
#         element_results = {elem_id: elements_map[elem_id] for elem_id in output_elements}
#
#         extract_data(h5_file, node_results, element_results, output_nodes, base_node, output_elements,
#                      output_file_prefix, output_steps, podu, initial_stress, initial_strain)
#         end_time = time.time()
#         execution_time = end_time - start_time
#         print(f"计算执行时间: {execution_time} 秒")
import h5py
import time
import pandas as pd
import os
import traceback

from pre_group.pre import read_grid_file


def parse_control_file(control_file):
    """解析控制文件，支持忽略空行和注释"""
    with open(control_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    output_nodes = []
    output_elements = []
    output_steps = []
    base_node = None
    podu = 0.0
    initial_stress = 1
    initial_strain = 1

    for i, line in enumerate(lines):
        line = line.strip()

        if not line or line.startswith('#') or line.startswith('//'):
            continue

        if "output node number" in line:
            num_nodes = int(line.split('=')[1].strip())
            count = 0
            valid_nodes = 0

            while valid_nodes < num_nodes:
                next_line = lines[i + count + 1].strip()
                count += 1

                if next_line and not next_line.startswith(('#', '//')):
                    output_nodes.append(int(next_line))
                    valid_nodes += 1

        elif "output element number" in line:
            num_elements = int(line.split('=')[1].strip())
            count = 0
            valid_elements = 0

            while valid_elements < num_elements:
                next_line = lines[i + count + 1].strip()
                count += 1

                if next_line and not next_line.startswith(('#', '//')):
                    output_elements.append(int(next_line))
                    valid_elements += 1

        elif "output step number" in line:
            num_steps = int(line.split('=')[1].strip())
            count = 0
            valid_steps = 0

            while valid_steps < num_steps:
                next_line = lines[i + count + 1].strip()
                count += 1

                if next_line and not next_line.startswith(('#', '//')):
                    output_steps.append(int(next_line))
                    valid_steps += 1

        elif "base node" in line:
            base_node = int(line.split('=')[1].strip())

            if base_node != 0:
                output_nodes.append(base_node)

        elif "podu" in line:
            podu = float(line.split('=')[1].strip())

        elif "initial stress" in line:
            initial_stress = float(line.split('=')[1].strip())

        elif "initial strain" in line:
            initial_strain = float(line.split('=')[1].strip())

    # 去重，避免 base_node 和 output_nodes 重复
    output_nodes = list(dict.fromkeys(output_nodes))
    output_elements = list(dict.fromkeys(output_elements))
    output_steps = list(dict.fromkeys(output_steps))

    return output_nodes, output_elements, output_steps, base_node, podu, initial_stress, initial_strain


def extract_data(
    h5_file,
    node_results,
    element_results,
    output_nodes,
    base_node,
    output_elements,
    output_file_prefix,
    output_steps,
    podu,
    initial_stress,
    initial_strain
):
    """提取指定节点的位移和单元的应力数据并保存到文件"""

    with h5py.File(h5_file, 'r') as f:
        frames = f['frames']

        last_active_nodes = []
        last_active_elements = {}

        active_node_indices = {}
        active_elem_indices = {}

        for frame in sorted(frames.keys(), key=int):
            frame_data = frames[frame]

            # ========== 节点拓扑 ==========
            if 'new_topology' in frame_data and 'node_ids' in frame_data['new_topology']:
                last_active_nodes = frame_data['new_topology/node_ids'][:]
                active_node_indices = {
                    nid: i
                    for i, nid in enumerate(last_active_nodes)
                    if nid in output_nodes
                }

            # ========== 节点位移 ==========
            if len(last_active_nodes) > 0 and 'node_vars/displacement' in frame_data:
                node_displacement = frame_data['node_vars/displacement']

                for nid, index in active_node_indices.items():
                    if index < len(node_displacement):
                        disp = node_displacement[index]
                        node_results[nid].disp.append(disp)
                        node_results[nid].steps.append(frame)

            # ========== 节点孔压 ==========
            # 注意：这里原代码是 poressure，疑似拼写来自 h5 文件字段。
            if len(last_active_nodes) > 0 and 'node_vars/poressure' in frame_data:
                node_poressure = frame_data['node_vars/poressure']

                for nid, index in active_node_indices.items():
                    if index < len(node_poressure):
                        pore = node_poressure[index]
                        node_results[nid].poress.append(pore)

            # ========== 节点加速度 ==========
            if len(last_active_nodes) > 0 and 'node_vars/acceleration' in frame_data:
                node_acceleration = frame_data['node_vars/acceleration']

                for nid, index in active_node_indices.items():
                    if index < len(node_acceleration):
                        acceleration = node_acceleration[index]
                        node_results[nid].acc.append(acceleration)

            # ========== 节点速度 ==========
            if len(last_active_nodes) > 0 and 'node_vars/velocity' in frame_data:
                node_velocity = frame_data['node_vars/velocity']

                for nid, index in active_node_indices.items():
                    if index < len(node_velocity):
                        velocity = node_velocity[index]
                        node_results[nid].vel.append(velocity)

            # ========== 单元数据 ==========
            if 'parts' in frame_data:
                for part in frame_data['parts']:
                    part_path = frame_data[f'parts/{part}']

                    if 'elem_ids' in part_path:
                        last_active_elements[part] = part_path['elem_ids'][:]

                        new_active_elem_indices = {
                            eid: i
                            for i, eid in enumerate(last_active_elements[part])
                            if eid in output_elements
                        }

                        active_elem_indices[part] = new_active_elem_indices

                    if part in last_active_elements and part in active_elem_indices:

                        # 普通单元应力
                        if 'elem_vars/stress' in part_path:
                            elem_stress = part_path['elem_vars/stress']

                            for eid, index in active_elem_indices[part].items():
                                if index < len(elem_stress):
                                    stress = elem_stress[index]
                                    element_results[eid].stresses.append(stress)
                                    element_results[eid].steps.append(frame)

                        # 普通单元应变
                        if 'elem_vars/strain' in part_path:
                            elem_strain = part_path['elem_vars/strain']

                            for eid, index in active_elem_indices[part].items():
                                if index < len(elem_strain):
                                    strain = elem_strain[index]
                                    element_results[eid].strains.append(strain)

                        # 接触/界面单元应力
                        if 'elem_vars/interface_stress' in part_path:
                            elem_interface_stress = part_path['elem_vars/interface_stress']

                            for eid, index in active_elem_indices[part].items():
                                if index < len(elem_interface_stress):
                                    stress = elem_interface_stress[index]
                                    element_results[eid].stresses.append(stress)
                                    element_results[eid].steps.append(frame)

                        # 接触/界面单元相对位移
                        if 'elem_vars/interface_relative_displacement' in part_path:
                            elem_interface_strain = part_path['elem_vars/interface_relative_displacement']

                            for eid, index in active_elem_indices[part].items():
                                if index < len(elem_interface_strain):
                                    strain = elem_interface_strain[index]
                                    element_results[eid].strains.append(strain)

        # ========== 节点时程处理 ==========
        for node, result in node_results.items():
            if base_node is not None and base_node != 0:
                if node != base_node:
                    if base_node not in node_results:
                        print(f"警告：base_node={base_node} 不在 node_results 中，跳过相对位移计算。")
                    elif not node_results[base_node].disp:
                        print(f"警告：base_node={base_node} 没有位移数据，跳过节点 {node} 的相对位移计算。")
                    elif len(result.disp) != len(node_results[base_node].disp):
                        print(
                            f"警告：节点 {node} 与 base_node={base_node} 的位移步数不一致，"
                            f"节点步数={len(result.disp)}，基准节点步数={len(node_results[base_node].disp)}。"
                            f"将按较短长度计算。"
                        )

                        min_len = min(len(result.disp), len(node_results[base_node].disp))
                        result.disp = [
                            [a - b for a, b in zip(row1, row2)]
                            for row1, row2 in zip(result.disp[:min_len], node_results[base_node].disp[:min_len])
                        ]
                    else:
                        result.disp = [
                            [a - b for a, b in zip(row1, row2)]
                            for row1, row2 in zip(result.disp, node_results[base_node].disp)
                        ]

            if result.disp:
                try:
                    result.write_Schedule()
                except Exception as e:
                    print(f"写入节点 {node} 时程文件失败：{e}")
                    traceback.print_exc()

        # ========== 单元时程处理 ==========
        for elem_id, result in element_results.items():
            try:
                # 这里是你原来 index 3 越界最可能发生的位置。
                # 例如某些 stress/strain 只有 3 个分量，但内部函数按 4 或 6 个分量读取。
                result.calculate_stress_strain_variables(
                    podu,
                    initial_stress,
                    initial_strain
                )

                result.write_ele_Schedule()

            except IndexError as e:
                print("=" * 80)
                print(f"单元 {elem_id} 处理失败：数组维度不匹配。")
                print(f"错误信息：{e}")
                print("该单元可能是界面单元或特殊单元，stress/strain 分量数量与普通单元不同。")
                print(f"stresses 数量：{len(getattr(result, 'stresses', []))}")
                print(f"strains 数量：{len(getattr(result, 'strains', []))}")

                if getattr(result, 'stresses', []):
                    try:
                        print(f"第一条 stress 数据：{result.stresses[0]}")
                        print(f"第一条 stress 分量数：{len(result.stresses[0])}")
                    except Exception:
                        pass

                if getattr(result, 'strains', []):
                    try:
                        print(f"第一条 strain 数据：{result.strains[0]}")
                        print(f"第一条 strain 分量数：{len(result.strains[0])}")
                    except Exception:
                        pass

                print("已跳过该单元，继续处理其他单元。")
                print("=" * 80)

            except Exception as e:
                print("=" * 80)
                print(f"单元 {elem_id} 处理失败：{e}")
                traceback.print_exc()
                print("已跳过该单元，继续处理其他单元。")
                print("=" * 80)

        # ========== 输出指定 step 的节点/单元数据 ==========
        for step in output_steps:
            step = str(step)

            node_file_name = f"step_{step}_node_data.txt"
            with open(node_file_name, 'w', encoding='utf-8') as node_file:
                node_file.write(f"Node data for step {step}:\n")

                for node_id, result in node_results.items():
                    try:
                        result.write_step(step, node_file)
                    except Exception as e:
                        print(f"写入节点 {node_id} 在 step={step} 的数据失败：{e}")

            element_file_name = f"step_{step}_element_data.txt"
            with open(element_file_name, 'w', encoding='utf-8') as element_file:
                element_file.write(f"Element data for step {step}:\n")

                for elem_id, result in element_results.items():
                    try:
                        result.write_step(step, element_file)
                    except Exception as e:
                        print(f"写入单元 {elem_id} 在 step={step} 的数据失败：{e}")

        # ========== 输出最大值对应 step ==========
        with open("max_node_step.dat", 'w', encoding='utf-8') as node_file:
            node_file.write("Node data for max :\n")

            for node_id, result in node_results.items():
                try:
                    result.write_max_step(node_file)
                except Exception as e:
                    print(f"写入节点 {node_id} 最大值数据失败：{e}")

        with open("max_element_step.dat", 'w', encoding='utf-8') as element_file:
            element_file.write("Element data for max :\n")

            for elem_id, result in element_results.items():
                try:
                    result.write_max_step(element_file)
                except Exception as e:
                    print(f"写入单元 {elem_id} 最大值数据失败：{e}")

        # ========== 生成节点/单元时程 Excel ==========
        convert_schedule_files_to_excel(
            output_file_prefix,
            output_nodes,
            output_elements
        )


def convert_schedule_files_to_excel(output_prefix, output_nodes, output_elements):
    """
    将控制文件中指定的节点时程文件（*.node）和单元时程文件（*.ele）
    整合为一个节点 Excel 和一个单元 Excel。

    修改点：
    1. 如果没有任何有效文件，也会写入一个 empty sheet，避免 openpyxl 报：
       IndexError: At least one sheet must be visible
    2. 打印每个被跳过的文件原因，方便排查。
    """

    # ========== 节点时程 Excel ==========
    if output_nodes:
        node_excel = f"{output_prefix}_node_schedule.xlsx"
        print(f"正在生成节点 Excel 文件：{node_excel}")

        written = False

        with pd.ExcelWriter(node_excel, engine='openpyxl') as writer:
            for node_id in output_nodes:
                fpath = f"{node_id}.node"

                if not os.path.isfile(fpath):
                    print(f"跳过节点 {node_id}：文件不存在 {fpath}")
                    continue

                try:
                    df = pd.read_csv(
                        fpath,
                        sep=r'\s+',
                        header=0,
                        engine='python'
                    )
                except Exception as e:
                    print(f"跳过节点 {node_id}：读取 {fpath} 失败：{e}")
                    continue

                if df.empty:
                    print(f"跳过节点 {node_id}：{fpath} 是空文件或没有有效数据")
                    continue

                sheet_name = safe_sheet_name(str(node_id))
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                written = True

            if not written:
                pd.DataFrame({
                    "message": ["没有找到可写入的节点时程文件"],
                    "reason": ["所有 .node 文件不存在、读取失败或为空"]
                }).to_excel(writer, sheet_name="empty", index=False)

        print(f"节点 Excel 文件生成完成：{node_excel}")

    # ========== 单元时程 Excel ==========
    if output_elements:
        elem_excel = f"{output_prefix}_element_schedule.xlsx"
        print(f"正在生成单元 Excel 文件：{elem_excel}")

        written = False

        with pd.ExcelWriter(elem_excel, engine='openpyxl') as writer:
            for elem_id in output_elements:
                fpath = f"{elem_id}.ele"

                if not os.path.isfile(fpath):
                    print(f"跳过单元 {elem_id}：文件不存在 {fpath}")
                    continue

                try:
                    df = pd.read_csv(
                        fpath,
                        sep=r'\s+',
                        header=0,
                        engine='python'
                    )
                except Exception as e:
                    print(f"跳过单元 {elem_id}：读取 {fpath} 失败：{e}")
                    continue

                if df.empty:
                    print(f"跳过单元 {elem_id}：{fpath} 是空文件或没有有效数据")
                    continue

                sheet_name = safe_sheet_name(str(elem_id))
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                written = True

            if not written:
                pd.DataFrame({
                    "message": ["没有找到可写入的单元时程文件"],
                    "reason": ["所有 .ele 文件不存在、读取失败、为空，或前面单元计算失败导致未生成 .ele 文件"]
                }).to_excel(writer, sheet_name="empty", index=False)

        print(f"单元 Excel 文件生成完成：{elem_excel}")


def safe_sheet_name(name):
    """
    Excel sheet 名称限制：
    1. 最长 31 个字符
    2. 不能包含 : \\ / ? * [ ]
    """
    invalid_chars = [':', '\\', '/', '?', '*', '[', ']']

    for ch in invalid_chars:
        name = name.replace(ch, '_')

    if not name:
        name = "Sheet"

    return name[:31]


class ReadH5Calc:
    def readh5(
        self,
        control_file="control.txt",
        h5_file="static.h5",
        output_file_prefix="output",
        gril_file="Inimesh.dat"
    ):
        start_time = time.time()

        output_nodes, output_elements, output_steps, base_node, podu, initial_stress, initial_strain = parse_control_file(
            control_file
        )

        print("读取控制文件完成")

        _, _, nodes_map, elements_map = read_grid_file(gril_file)

        # ========== 检查控制文件中的节点是否存在 ==========
        node_results = {}

        for node_id in output_nodes:
            if node_id in nodes_map:
                node_results[node_id] = nodes_map[node_id]
            else:
                print(f"警告：控制文件中的节点 {node_id} 不存在于网格文件中，已跳过。")

        # ========== 检查控制文件中的单元是否存在 ==========
        element_results = {}

        for elem_id in output_elements:
            if elem_id in elements_map:
                element_results[elem_id] = elements_map[elem_id]
            else:
                print(f"警告：控制文件中的单元 {elem_id} 不存在于网格文件中，已跳过。")

        if not node_results:
            print("警告：没有有效输出节点。")

        if not element_results:
            print("警告：没有有效输出单元。")

        extract_data(
            h5_file,
            node_results,
            element_results,
            list(node_results.keys()),
            base_node,
            list(element_results.keys()),
            output_file_prefix,
            output_steps,
            podu,
            initial_stress,
            initial_strain
        )

        end_time = time.time()
        execution_time = end_time - start_time

        print(f"计算执行时间: {execution_time} 秒")