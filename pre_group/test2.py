from typing import List, Dict, Callable, Optional, Union
import csv  # 用于解析CSV文件
from pathlib import Path  # 用于处理文件路径，兼容Windows/Linux


# ------------------------------------------------------------------------------
# 1. 基础数据类（不变，与原业务逻辑对齐）
# ------------------------------------------------------------------------------
class Node:
    def __init__(self, node_id: int, x: float, y: float, z: float):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.z = z

    def __repr__(self):
        return f"Node(ID:{self.node_id}, X:{self.x:.2f}, Y:{self.y:.2f}, Z:{self.z:.2f})"


class Element:
    def __init__(self, e_id: int, t_id: int, m_id: int, points: List[Node]):
        self.e_id = e_id  # 单元ID（唯一，保证顺序）
        self.t_id = t_id  # 单元类型
        self.m_id = m_id  # 材料ID
        self.points = points
        self.num_point = len(points)

    def __repr__(self):
        return f"Element(ID:{self.e_id}, Type:{self.t_id}, Mat:{self.m_id}, Nodes:{self.num_point}个)"


class ElementFactory:
    @staticmethod
    def create_element(e_id: int, t_id: int, m_id: int, points: List[Node]) -> Element:
        return Element(e_id=e_id, t_id=t_id, m_id=m_id, points=points)


# ------------------------------------------------------------------------------
# 2. 单元转换核心类（不变，支持动态规则所需的转换方法）
# ------------------------------------------------------------------------------
class ElementConverter:
    def __init__(self):
        self.conversion_methods: Dict[tuple, Callable[[Element, int], Element]] = {}
        self._init_default_conversion_methods()

    def _init_default_conversion_methods(self):
        """初始化所有可能用到的转换方法（同结构转换为主，支持未知类型对）"""
        # 此处无需硬编码具体类型对，后续通过register_conversion_method动态注册
        # 先注册通用的“同结构转换”（90%场景适用，如需特殊转换可后续扩展）
        self.register_conversion_method(
            old_type=-1, new_type=-1, conversion_method=self._convert_same_structure
        )

    def register_conversion_method(self, old_type: int, new_type: int, conversion_method: Callable):
        """支持动态注册未知的类型对转换方法"""
        if not callable(conversion_method):
            raise TypeError("conversion_method必须是可调用函数")
        method_key = (old_type, new_type)
        if method_key not in self.conversion_methods:
            self.conversion_methods[method_key] = conversion_method
            print(f"✅ 动态注册转换方法：{old_type}→{new_type}")

    def execute_conversion(self, element: Element, old_type: int, new_type: int) -> Element:
        # 1. 校验单元类型
        if element.t_id != old_type:
            print(f"⚠️  单元{element.e_id}：类型{element.t_id}≠{old_type}，跳过")
            return element

        # 2. 动态注册“同结构转换”（若该类型对未注册）
        method_key = (old_type, new_type)
        if method_key not in self.conversion_methods:
            self.register_conversion_method(
                old_type=old_type,
                new_type=new_type,
                conversion_method=self._convert_same_structure
            )

        # 3. 执行转换
        try:
            conversion_func = self.conversion_methods[method_key]
            new_element = conversion_func(element, new_type)
            print(f"✅ 单元{element.e_id}：Mat{element.m_id}，Type{old_type}→{new_type}")
            return new_element
        except Exception as e:
            print(f"❌ 单元{element.e_id}转换失败：{str(e)}，保留原类型")
            return element

    def _convert_same_structure(self, old_element: Element, new_type: int) -> Element:
        """通用同结构转换：支持所有类型对，仅改类型，保留其他属性"""
        return ElementFactory.create_element(
            e_id=old_element.e_id,
            t_id=new_type,
            m_id=old_element.m_id,
            points=old_element.points
        )


# ------------------------------------------------------------------------------
# 3. 新增：从文件动态读取转换规则（核心适配未知数量的材料号和类型对）
# ------------------------------------------------------------------------------
def read_conversion_rules_from_file(rule_file_path: str) -> List[Dict]:
    """
    从CSV文件读取未知数量的转换规则，支持动态材料号和类型对

    参数:
        rule_file_path: 规则文件路径（如"conversion_rules.csv"）

    返回:
        List[Dict]: 解析后的多组转换规则，格式兼容batch_convert_with_multiple_rules

    规则文件格式（CSV）：
    每行代表一组规则，格式为：材料号列表,旧单元类型,新单元类型,额外条件（可选）
    示例：
    1,2,3,6,500          # 材料1-3，Type6→500（无额外条件）
    1,9,903               # 材料1，Type9→903（无额外条件）
    2,3,44,47             # 材料2-3，Type44→47（无额外条件）
    1,2,60,601,node>=8    # 材料1-2，Type60→601（额外条件：节点数≥8）
    """
    # 1. 校验文件是否存在
    rule_file = Path(rule_file_path)
    if not rule_file.exists():
        raise FileNotFoundError(f"规则文件不存在：{rule_file.absolute()}")
    if rule_file.suffix != ".csv":
        raise ValueError(f"仅支持CSV格式文件，当前为：{rule_file.suffix}")

    parsed_rules = []  # 存储解析后的规则

    # 2. 读取并解析CSV文件
    with open(rule_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)  # 按逗号拆分每行内容
        for line_num, row in enumerate(reader, 1):  # line_num：行号（便于报错定位）
            # 清理每行空格（避免用户输入时的多余空格）
            row = [item.strip() for item in row if item.strip()]
            if not row:  # 跳过空行
                continue

            # 3. 解析每行规则（核心：适配未知数量的材料号）
            # 规则格式要求：至少包含“材料号列表+旧类型+新类型”（最少3列）
            if len(row) < 3:
                raise ValueError(
                    f"第{line_num}行格式错误：需至少3列（材料号列表,旧类型,新类型），当前{len(row)}列"
                )

            # 3.1 解析材料号列表（前N-2列：N为总行数，最后2列是旧/新类型）
            material_str_list = row[:-2]  # 材料号部分（可能1个或多个）
            try:
                material_ids = [int(m) for m in material_str_list]  # 转为整数列表
                if any(m < 0 for m in material_ids):
                    raise ValueError("材料号不能为负数")
            except ValueError as e:
                raise ValueError(f"第{line_num}行材料号格式错误（需为整数）：{e}") from e

            # 3.2 解析旧单元类型（倒数第2列）
            try:
                old_type = int(row[-2])
                if old_type < 0:
                    raise ValueError("单元类型不能为负数")
            except ValueError as e:
                raise ValueError(f"第{line_num}行旧类型格式错误（需为整数）：{e}") from e

            # 3.3 解析新单元类型（最后1列）
            try:
                new_type = int(row[-1])
                if new_type < 0:
                    raise ValueError("单元类型不能为负数")
            except ValueError as e:
                raise ValueError(f"第{line_num}行新类型格式错误（需为整数）：{e}") from e

            # 3.4 解析额外条件（可选，当前支持“node>=N”“mat==M”等简单条件，可扩展）
            condition_input = True  # 默认无额外条件
            # （可选）若需支持额外条件，可在CSV中增加第4列，示例：
            # if len(row) >=4:
            #     condition_str = row[3]
            #     if condition_str.startswith("node>="):
            #         min_node = int(condition_str.split(">=")[1])
            #         condition_input = [lambda elem: elem.num_point >= min_node]
            #     else:
            #         raise ValueError(f"第{line_num}行不支持的额外条件：{condition_str}")

            # 4. 生成标准化规则（适配原有多规则转换逻辑）
            # 为每个材料号单独生成一条规则（避免多材料逻辑复杂，便于匹配）
            for mat_id in material_ids:
                parsed_rule = {
                    "material_id": mat_id,
                    "old_type": old_type,
                    "new_type": new_type,
                    "condition_input": condition_input
                }
                parsed_rules.append(parsed_rule)

    # 5. 打印解析结果（让用户确认规则是否正确）
    print(f"\n📄 从文件{rule_file.name}解析完成：")
    print(f"   共读取{len(set((r['old_type'], r['new_type']) for r in parsed_rules))}组类型对")
    print(f"   共涉及{len(set(r['material_id'] for r in parsed_rules))}种材料号")
    print("   解析后的规则列表：")
    for idx, rule in enumerate(parsed_rules, 1):
        print(f"     规则{idx}：Mat{rule['material_id']}，Type{rule['old_type']}→{rule['new_type']}")

    return parsed_rules


# ------------------------------------------------------------------------------
# 4. 多组规则批量转换（不变，兼容动态解析的规则）
# ------------------------------------------------------------------------------
def check_element_conversion_condition(element: Element,
                                       old_type: int,
                                       condition_input: Union[bool, List[Callable[[Element], bool]], Dict]) -> bool:
    """条件判断工具（不变）"""
    if element.t_id != old_type:
        return False
    if isinstance(condition_input, bool):
        return condition_input
    elif isinstance(condition_input, list) and all(callable(cond) for cond in condition_input):
        return all(cond(element) for cond in condition_input)
    elif isinstance(condition_input, dict):
        if "conditions" not in condition_input:
            raise ValueError("条件字典必须包含'conditions'键")
        conditions = condition_input["conditions"]
        logic = condition_input.get("logic", "and")
        if not all(callable(cond) for cond in conditions):
            raise ValueError("'conditions'必须是可调用函数列表")
        return all(cond(element) for cond in conditions) if logic == "and" else any(
            cond(element) for cond in conditions)
    else:
        raise TypeError("condition_input仅支持bool、List[Callable]、Dict")


def batch_convert_with_multiple_rules(
        elements: List[Element],
        conversion_rules: List[Dict],
        converter: Optional[ElementConverter] = None
) -> List[Element]:
    """多组规则批量转换（不变，保持单元顺序）"""
    if converter is None:
        converter = ElementConverter()
    converted_elements = []
    for elem in elements:
        converted = False
        for rule in conversion_rules:
            # 匹配当前单元的材料号和旧类型
            if elem.m_id == rule["material_id"] and elem.t_id == rule["old_type"]:
                # 检查额外条件
                if check_element_conversion_condition(elem, rule["old_type"], rule["condition_input"]):
                    converted_elem = converter.execute_conversion(elem, rule["old_type"], rule["new_type"])
                    converted_elements.append(converted_elem)
                    converted = True
                    break
        if not converted:
            converted_elements.append(elem)
    return converted_elements


# ------------------------------------------------------------------------------
# 5. 测试示例：从文件读取动态规则→执行转换
# ------------------------------------------------------------------------------
def dynamic_rule_demo(rule_file_path: str = "conversion_rules.csv"):
    """
    测试流程：
    1. 创建含未知材料号/类型的测试单元
    2. 从CSV文件读取动态规则（材料号、类型对数量未知）
    3. 执行多规则转换，保持单元顺序
    """
    print("=" * 100)
    print("1. 准备测试数据（含未知材料号和单元类型）")
    print("=" * 100)

    # 1.1 创建测试节点
    test_nodes = [
        Node(1, 0.0, 0.0, 0.0), Node(2, 1.0, 0.0, 0.0), Node(3, 1.0, 1.0, 0.0), Node(4, 0.0, 1.0, 0.0),
        Node(5, 0.0, 0.0, 1.0), Node(6, 1.0, 0.0, 1.0), Node(7, 1.0, 1.0, 1.0), Node(8, 1.0, 1.0, 1.0)
    ]

    # 1.2 创建测试单元（材料号1-5，类型6/9/44/60，模拟未知组合）
    test_elements = [
        ElementFactory.create_element(e_id=101, t_id=6, m_id=1, points=test_nodes[:4]),  # 应转500
        ElementFactory.create_element(e_id=102, t_id=9, m_id=1, points=test_nodes[:6]),  # 应转903
        ElementFactory.create_element(e_id=103, t_id=6, m_id=3, points=test_nodes[:4]),  # 应转500
        ElementFactory.create_element(e_id=104, t_id=44, m_id=2, points=test_nodes[:8]),  # 应转47
        ElementFactory.create_element(e_id=105, t_id=60, m_id=2, points=test_nodes),  # 应转601
        ElementFactory.create_element(e_id=106, t_id=6, m_id=5, points=test_nodes[:4]),  # 不转换（材料5不在规则）
        ElementFactory.create_element(e_id=107, t_id=9, m_id=3, points=test_nodes[:6])  # 不转换（材料3无9→903规则）
    ]

    # 打印原始单元
    print("原始单元列表（按ID顺序）：")
    for idx, elem in enumerate(test_elements, 1):
        print(f"  顺序{idx}：{elem}")

    # ------------------------------
    # 2. 从文件读取动态规则（核心步骤）
    # ------------------------------
    print("\n" + "=" * 100)
    print("2. 从文件读取动态转换规则")
    print("=" * 100)
    try:
        # 读取规则（若文件不存在/格式错误，会抛出异常并提示）
        conversion_rules = read_conversion_rules_from_file(rule_file_path)
    except Exception as e:
        print(f"❌ 规则读取失败：{str(e)}")
        return

    # ------------------------------
    # 3. 执行动态规则转换
    # ------------------------------
    print("\n" + "=" * 100)
    print("3. 执行动态规则转换（保持原始顺序）")
    print("=" * 100)
    converted_elements = batch_convert_with_multiple_rules(
        elements=test_elements,
        conversion_rules=conversion_rules
    )

    # ------------------------------
    # 4. 打印转换结果
    # ------------------------------
    print("\n" + "=" * 100)
    print("4. 转换结果（顺序与原始一致）")
    print("=" * 100)
    print("转换后单元列表：")
    for idx, elem in enumerate(converted_elements, 1):
        original_elem = test_elements[idx - 1]
        status = "✅ 已转换" if elem.t_id != original_elem.t_id else "❌ 未转换"
        print(f"  顺序{idx}：{elem} | {status}")


# ------------------------------------------------------------------------------
# 6. 生成示例规则文件（帮助用户快速测试）
# ------------------------------------------------------------------------------
def generate_sample_rule_file(file_path: str = "conversion_rules.csv"):
    """生成示例CSV规则文件，避免用户不懂格式"""
    sample_rules = [
        # 材料号列表,旧类型,新类型（示例：材料1-3→6→500；材料1→9→903；材料2-3→44→47；材料2→60→601）
        "1,2,3,6,500",
        "1,9,903",
        "2,3,44,47",
        "2,60,601"
    ]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sample_rules))
    print(f"📝 已生成示例规则文件：{Path(file_path).absolute()}")
    print("   规则说明：")
    print("   - 每行格式：材料号1,材料号2,...（可多个）,旧单元类型,新单元类型")
    print("   - 示例1：1,2,3,6,500 → 材料1-3的Type6单元→500")
    print("   - 示例2：1,9,903 → 材料1的Type9单元→903")


# 执行测试（先生成示例文件，再读取规则执行转换）
if __name__ == "__main__":
    # 步骤1：生成示例规则文件（首次运行时帮助用户创建模板）
    generate_sample_rule_file()
    # 步骤2：从文件读取规则并执行转换
    dynamic_rule_demo(rule_file_path="conversion_rules.csv")