import time

from PySide6.QtWidgets import QDialog
from .scale_coor_by_direction import Ui_Form
from pre_group import pre
from basemethod.base_method import read_and_clean_file

def scale_local_with_base(nodes, base_point, direction, range_min, range_max, scale_factor):
    """
    基于基准点的局部坐标缩放，范围外节点自动平移以保证无缝衔接
    :param nodes: 节点列表（Node对象列表）
    :param base_point: 基准点坐标，元组格式 (x0, y0, z0)
    :param direction: 缩放方向，可选 'x'/'y'/'z'
    :param range_min: 缩放范围最小值（如x_min）
    :param range_max: 缩放范围最大值（如x_max），要求 range_min < range_max
    :param scale_factor: 缩放因子（>1扩大，0<factor<1缩小，1不变）
    :return: 无返回，直接修改nodes中节点的坐标
    """
    # 严格入参校验，避免计算错误
    if not isinstance(base_point, tuple) or len(base_point) != 3:
        raise ValueError("基准点base_point必须是3元组，格式：(x0, y0, z0)")
    if direction not in ['x', 'y', 'z']:
        raise ValueError(f"缩放方向direction只能是 'x'/'y'/'z'，当前输入：{direction}")
    if range_min >= range_max:
        raise ValueError(f"范围最小值必须小于最大值，当前：{range_min} >= {range_max}")
    if scale_factor <= 0:
        raise ValueError(f"缩放因子scale_factor必须大于0，当前：{scale_factor}")
    if not nodes:
        raise ValueError("节点列表nodes不能为空")

    start_time = time.time()
    # 提取基准点对应方向的坐标（如x方向取base_point[0]）
    base_coord = base_point[0] if direction == 'x' else (base_point[1] if direction == 'y' else base_point[2])
    # 统计各区域节点数
    count_in = 0   # 范围内（缩放）
    count_left = 0 # 范围外左侧（< range_min，平移）
    count_right = 0# 范围外右侧（> range_max，平移）

    # 遍历所有节点，按区域处理坐标
    for node in nodes:
        # 获取节点当前方向的坐标
        curr_coord = getattr(node, direction)
        if range_min <= curr_coord <= range_max:
            # 1. 范围内节点：相对基准点的偏移量 * 缩放因子
            offset = curr_coord - base_coord
            new_coord = base_coord + offset * scale_factor
            setattr(node, direction, new_coord)
            count_in += 1
        elif curr_coord < range_min:
            # 2. 范围外左侧：基于缩放后的左边界，保持原相对偏移
            offset_original = curr_coord - range_min  # 原相对左边界的偏移（负数）
            new_range_min = base_coord + (range_min - base_coord) * scale_factor  # 缩放后的左边界
            new_coord = new_range_min + offset_original
            setattr(node, direction, new_coord)
            count_left += 1
        else:
            # 3. 范围外右侧：基于缩放后的右边界，保持原相对偏移
            offset_original = curr_coord - range_max  # 原相对右边界的偏移（正数）
            new_range_max = base_coord + (range_max - base_coord) * scale_factor  # 缩放后的右边界
            new_coord = new_range_max + offset_original
            setattr(node, direction, new_coord)
            count_right += 1

    # 打印处理统计信息
    total = count_in + count_left + count_right
    elapsed_time = time.time() - start_time
    print(f"\n📏 局部缩放平移完成 | 基准点：{base_point} | 方向：{direction} | 缩放因子：{scale_factor}")
    print(f"📊 节点统计 | 总节点：{total} | 范围内缩放：{count_in} | 左侧平移：{count_left} | 右侧平移：{count_right}")
    print(f"⌛ 处理耗时：{elapsed_time:.4f}s")


def get_control(config_file="control_config.txt"):
    """
    从配置文件读取网格缩放的控制参数，并完成参数校验
    :param config_file: 配置文件路径（默认：control_config.txt）
    :return: 元组 (BASE_POINT, SCALE_DIR, SCALE_RANGE_MIN, SCALE_RANGE_MAX, SCALE_FACTOR)
             - BASE_POINT: 基准点坐标，三元组 (float, float, float)
             - SCALE_DIR: 缩放方向，字符串 'x'/'y'/'z'
             - SCALE_RANGE_MIN: 缩放范围最小值，float
             - SCALE_RANGE_MAX: 缩放范围最大值，float
             - SCALE_FACTOR: 缩放因子，float（>0）
    """
    # 1. 读取并清理配置文件（自动处理注释、空行、编码）
    cleaned_lines = read_and_clean_file(config_file)
    if not cleaned_lines:
        raise FileNotFoundError(f"配置文件{config_file}读取失败或为空，请检查文件路径/内容")

    # 2. 解析配置行（支持 key=value 格式，忽略空格）
    config_dict = {}
    for line_num, line in enumerate(cleaned_lines, 1):
        # 分割key和value（仅分割第一个=，避免value中包含=的情况）
        if "=" not in line:
            raise ValueError(f"配置文件第{line_num}行格式错误：缺少'='，正确格式如 'BASE_POINT = 0.0,0.0,0.0'")

        key, value = line.split("=", 1)
        key = key.strip().upper()  # 统一转大写，兼容大小写（如 Base_Point / base_point）
        value = value.strip()
        config_dict[key] = value

    # 3. 提取并转换参数（带默认值+严格校验）
    try:
        # ---------------------- 解析基准点 BASE_POINT ----------------------
        if "BASE_POINT" not in config_dict:
            raise KeyError("配置文件缺少必填参数：BASE_POINT（格式示例：0.0,0.0,0.0）")
        # 分割基准点坐标（兼容逗号/空格分隔，如 "0.0,0.0,0.0" 或 "0.0 0.0 0.0"）
        point_str = config_dict["BASE_POINT"].replace(",", " ").split()
        if len(point_str) != 3:
            raise ValueError("BASE_POINT格式错误：必须是3个数值（如 0.0,0.0,0.0）")
        BASE_POINT = tuple(float(p) for p in point_str)

        # ---------------------- 解析缩放方向 SCALE_DIR ----------------------
        if "SCALE_DIR" not in config_dict:
            raise KeyError("配置文件缺少必填参数：SCALE_DIR（可选值：x/y/z）")
        SCALE_DIR = config_dict["SCALE_DIR"].strip().lower()  # 统一转小写
        if SCALE_DIR not in ["x", "y", "z"]:
            raise ValueError(f"SCALE_DIR值错误：{SCALE_DIR}，仅支持 x/y/z")

        # ---------------------- 解析缩放范围最小值 SCALE_RANGE_MIN ----------------------
        if "SCALE_RANGE_MIN" not in config_dict:
            raise KeyError("配置文件缺少必填参数：SCALE_RANGE_MIN（数值，如 5.0）")
        SCALE_RANGE_MIN = float(config_dict["SCALE_RANGE_MIN"])

        # ---------------------- 解析缩放范围最大值 SCALE_RANGE_MAX ----------------------
        if "SCALE_RANGE_MAX" not in config_dict:
            raise KeyError("配置文件缺少必填参数：SCALE_RANGE_MAX（数值，如 20.0）")
        SCALE_RANGE_MAX = float(config_dict["SCALE_RANGE_MAX"])
        if SCALE_RANGE_MIN >= SCALE_RANGE_MAX:
            raise ValueError(
                f"SCALE_RANGE_MIN({SCALE_RANGE_MIN}) >= SCALE_RANGE_MAX({SCALE_RANGE_MAX})，最小值必须小于最大值")

        # ---------------------- 解析缩放因子 SCALE_FACTOR ----------------------
        if "SCALE_FACTOR" not in config_dict:
            raise KeyError("配置文件缺少必填参数：SCALE_FACTOR（数值>0，如 1.5）")
        SCALE_FACTOR = float(config_dict["SCALE_FACTOR"])
        if SCALE_FACTOR <= 0:
            raise ValueError(f"SCALE_FACTOR值错误：{SCALE_FACTOR}，必须大于0")

    except KeyError as e:
        raise KeyError(f"配置参数缺失：{e}")
    except ValueError as e:
        raise ValueError(f"参数格式/值错误：{e}")
    except Exception as e:
        raise Exception(f"参数解析未知错误：{e}")

    # 4. 打印参数确认信息（方便调试）
    print("=" * 50)
    print("✅ 配置参数读取成功：")
    print(f"   基准点 BASE_POINT: {BASE_POINT}")
    print(f"   缩放方向 SCALE_DIR: {SCALE_DIR}")
    print(f"   缩放范围 SCALE_RANGE: [{SCALE_RANGE_MIN}, {SCALE_RANGE_MAX}]")
    print(f"   缩放因子 SCALE_FACTOR: {SCALE_FACTOR}")
    print("=" * 50)

    return BASE_POINT, SCALE_DIR, SCALE_RANGE_MIN, SCALE_RANGE_MAX, SCALE_FACTOR

# -------------------------- 示例：完整的网格修改流程（直接运行） --------------------------
def scale_coor_by_direction(control_filenname,Inimesh_filename,Output__filename):

    # *****************************************************************************

    try:
        # 1. 读取配置参数
        BASE_POINT, SCALE_DIR, SCALE_RANGE_MIN, SCALE_RANGE_MAX, SCALE_FACTOR = get_control(control_filenname)

        # 2. 读取原始网格
        nodes, elements, node_map, element_map = pre.read_grid_file(Inimesh_filename)
        if not nodes or not elements:
            exit(1)

        # 3. 执行局部缩放+平移
        scale_local_with_base(
            nodes=nodes,
            base_point=BASE_POINT,
            direction=SCALE_DIR,
            range_min=SCALE_RANGE_MIN,
            range_max=SCALE_RANGE_MAX,
            scale_factor=SCALE_FACTOR
        )

        # 4. 写入修改后的网格
        pre.write_grid_file_01(Output__filename, nodes, elements)
        print(f"\n✅ 网格修改完成！输出文件：{Output__filename}")

    except Exception as e:
        print(f"\n❌ 执行失败：{e}")
        exit(1)


class UiScaleCoorByDirection(QDialog):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.init()
    def ui_scale_coor_by_direction(self):
        print("开始检索")
        Inimesh_filename = self.ui.lineEdit.text()
        control_filenname = self.ui.lineEdit_2.text()
        outpuit_filenname = self.ui.lineEdit_3.text()
        scale_coor_by_direction(control_filenname,Inimesh_filename,outpuit_filenname)
        return 1

    def init(self):
        self.ui.buttonBox_2.accepted.connect(self.accept)  # OK 按钮
        self.ui.buttonBox_2.rejected.connect(self.reject)  # Cancel 按钮
