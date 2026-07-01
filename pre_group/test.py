from typing import List, Dict, Callable, Optional, Union


# ------------------------------------------------------------------------------
# 1. 基础数据类（模拟实际业务中的节点、单元、单元工厂，与业务逻辑对齐）
# ------------------------------------------------------------------------------
class Node:
    """节点类：存储节点ID和三维坐标"""

    def __init__(self, node_id: int, x: float, y: float, z: float):
        self.node_id = node_id  # 节点ID
        self.x = x  # X坐标
        self.y = y  # Y坐标
        self.z = z  # Z坐标

    def __repr__(self):
        return f"Node(ID:{self.node_id}, X:{self.x:.2f}, Y:{self.y:.2f}, Z:{self.z:.2f})"


class Element:
    """单元类：存储单元ID、类型、材料ID、节点列表等核心属性"""

    def __init__(self, e_id: int, t_id: int, m_id: int, points: List[Node]):
        self.e_id = e_id  # 单元ID
        self.t_id = t_id  # 单元类型（如60、9）
        self.m_id = m_id  # 材料ID
        self.points = points  # 单元包含的节点列表
        self.num_point = len(points)  # 节点数量（快捷属性）

    def __repr__(self):
        return f"Element(ID:{self.e_id}, Type:{self.t_id}, Mat:{self.m_id}, Nodes:{self.num_point}个)"


class ElementFactory:
    """单元工厂类：统一创建单元实例，避免重复初始化逻辑"""

    @staticmethod
    def create_element(e_id: int, t_id: int, m_id: int, points: List[Node]) -> Element:
        """创建单元实例（可根据实际需求扩展参数，如组件ID、密度等）"""
        return Element(e_id=e_id, t_id=t_id, m_id=m_id, points=points)


# ------------------------------------------------------------------------------
# 2. 单元转换核心类（仅负责“怎么转”，不绑定固定条件）
# ------------------------------------------------------------------------------
class ElementConverter:
    def __init__(self):
        # 转换方法库：key=(旧类型, 新类型)，value=转换逻辑函数
        self.conversion_methods: Dict[tuple, Callable[[Element, int], Element]] = {}
        self._init_default_conversion_methods()  # 初始化默认转换方法

    def _init_default_conversion_methods(self):
        """初始化常用的单元转换方法（可根据业务扩展）"""
        # 注册 60号单元 → 9号单元 的转换方法
        self.register_conversion_method(
            old_type=60,
            new_type=601,
            conversion_method=self._convert_same_structure
        )
        # 注册 60号单元 → 9号单元 的转换方法
        self.register_conversion_method(
            old_type=60,
            new_type=602,
            conversion_method=self._convert_same_structure
        )
        # 注册 60号单元 → 9号单元 的转换方法
        self.register_conversion_method(
            old_type=57,
            new_type=59,
            conversion_method=self._convert_same_structure
        )
        # 注册 60号单元 → 9号单元 的转换方法
        self.register_conversion_method(
            old_type=57,
            new_type=80,
            conversion_method=self._convert_same_structure
        )
        # 注册 60号单元 → 9号单元 的转换方法
        self.register_conversion_method(
            old_type=6,
            new_type=61,
            conversion_method=self._convert_6_to_61
        )
        # 注册 60号单元 → 9号单元 的转换方法
        self.register_conversion_method(
            old_type=6,
            new_type=5,
            conversion_method=self._convert_same_structure
        )
        # 注册 60号单元 → 9号单元 的转换方法
        self.register_conversion_method(
            old_type=6,
            new_type=500,
            conversion_method=self._convert_same_structure
        )
        # 注册 60号单元 → 9号单元 的转换方法
        self.register_conversion_method(
            old_type=1,
            new_type=2,
            conversion_method=self._convert_same_structure
        )
        # 注册 9号单元 → 60号单元 的转换方法（示例扩展）
        self.register_conversion_method(
            old_type=1,
            new_type=222,
            conversion_method=self._convert_same_structure
        )
        # 注册 9号单元 → 60号单元 的转换方法（示例扩展）
        self.register_conversion_method(
            old_type=4,
            new_type=700,
            conversion_method=self._convert_same_structure
        )
        self.register_conversion_method(
            old_type=4,
            new_type=777,
            conversion_method=self._convert_same_structure
        )
        self.register_conversion_method(
            old_type=44,
            new_type=47,
            conversion_method=self._convert_same_structure
        )
        self.register_conversion_method(
            old_type=44,
            new_type=470,
            conversion_method=self._convert_same_structure
        )
        self.register_conversion_method(
            old_type=9,
            new_type=902,
            conversion_method=self._convert_same_structure
        )
        self.register_conversion_method(
            old_type=9,
            new_type=903,
            conversion_method=self._convert_same_structure
        )

    def register_conversion_method(self,
                                   old_type: int,
                                   new_type: int,
                                   conversion_method: Callable[[Element, int], Element]):
        """
        注册新的单元转换方法（对外扩展接口）

        参数:
            old_type: 待转换的旧单元类型
            new_type: 目标新单元类型
            conversion_method: 转换逻辑函数（输入旧单元+新类型，输出新单元）
        """
        if not callable(conversion_method):
            raise TypeError("conversion_method必须是可调用函数（如def定义的函数）")
        self.conversion_methods[(old_type, new_type)] = conversion_method
        print(f"已注册转换方法：{old_type}→{new_type}")

    def execute_conversion(self,
                           element: Element,
                           old_type: int,
                           new_type: int) -> Element:
        """
        执行单元转换（前提：已确认单元满足转换条件）

        参数:
            element: 待转换的单元
            old_type: 旧单元类型（用于校验和匹配转换方法）
            new_type: 目标新单元类型

        返回:
            转换后的单元（失败则返回原单元）
        """
        # 1. 基础校验：单元类型是否匹配旧类型
        if element.t_id != old_type:
            print(f"⚠️  单元{element.e_id}：当前类型{element.t_id}≠指定旧类型{old_type}，跳过转换")
            return element

        # 2. 校验转换方法是否存在
        method_key = (old_type, new_type)
        if method_key not in self.conversion_methods:
            raise ValueError(
                f"❌ 未找到{old_type}→{new_type}的转换方法！\n"
                f"请先调用 register_conversion_method({old_type}, {new_type}, 转换函数) 注册"
            )

        # 3. 执行转换逻辑
        try:
            conversion_func = self.conversion_methods[method_key]
            new_element = conversion_func(element, new_type)
            print(f"✅ 单元{element.e_id}：{old_type}→{new_type}转换成功")
            return new_element
        except Exception as e:
            print(f"❌ 单元{element.e_id}转换失败：{str(e)}，保留原类型")
            return element

    # ------------------------------
    # 具体转换逻辑（根据单元类型定义）
    # ------------------------------

    def _convert_same_structure(self, old_element: Element, new_type: int) -> Element:

        old_element.t_id = new_type

        # 创建新单元（继承原单元ID、材料ID，更新类型和节点）
        return old_element

    def _convert_60_to_61(self, old_element: Element, new_type: int) -> Element:
        if old_element.points[3].node_id == old_element.points[4].node_id and old_element.points[4].node_id == \
                old_element.points[5].node_id and old_element.points[5].node_id == old_element.points[6].node_id and \
                old_element.points[6].node_id == old_element.points[7].node_id:
            old_element.t_id = new_type
            return old_element

    def _convert_60_to_9(self, old_element: Element, new_type: int) -> Element:
        """
        60号单元 → 9号单元 转换逻辑（示例：9号单元仅保留前6个节点）
        注：实际逻辑需与您的单元定义对齐（如节点顺序、属性继承等）
        """
        # 校验60号单元的节点数（假设60号单元必须≥6个节点才能转9号）
        if old_element.num_point < 6:
            raise ValueError(f"60号单元需≥6个节点（当前{old_element.num_point}个），无法转9号单元")

        # 9号单元取前6个节点（按实际单元定义调整）
        new_points = old_element.points[:6]

        # 创建新单元（继承原单元ID、材料ID，更新类型和节点）
        return ElementFactory.create_element(
            e_id=old_element.e_id,
            t_id=new_type,
            m_id=old_element.m_id,
            points=new_points
        )


# ------------------------------------------------------------------------------
# 3. 外部条件判断工具（独立于转换类，支持灵活定义条件）
# ------------------------------------------------------------------------------
def check_element_conversion_condition(element: Element,
                                       old_type: int,
                                       condition_input: Union[bool, List[Callable[[Element], bool]], Dict]) -> bool:
    """
    检查单元是否满足转换条件（支持3种灵活输入方式）

    参数:
        element: 待检查的单元
        old_type: 目标旧单元类型（先校验单元类型）
        condition_input: 条件输入（3种类型可选）
            - bool：直接指定是否满足（如用户手动选择）
            - List[Callable]：条件函数列表（默认and逻辑）
            - Dict：带逻辑的条件配置（如{"conditions": [...], "logic": "or"}）

    返回:
        bool：是否满足转换条件
    """
    # 前置校验：单元类型是否匹配
    if element.t_id != old_type:
        return False

    # 处理不同类型的条件输入
    if isinstance(condition_input, bool):
        # 方式1：外部直接指定结果（如用户勾选“允许转换”）
        return condition_input

    elif isinstance(condition_input, list) and all(callable(cond) for cond in condition_input):
        # 方式2：条件函数列表（默认所有条件都满足）
        return all(cond(element) for cond in condition_input)

    elif isinstance(condition_input, dict):
        # 方式3：带逻辑的条件配置（支持and/or）
        required_keys = ["conditions"]
        if not all(key in condition_input for key in required_keys):
            raise ValueError("条件字典必须包含'conditions'键（值为条件函数列表）")

        conditions = condition_input["conditions"]
        logic = condition_input.get("logic", "and")  # 默认and逻辑

        # 校验条件格式
        if not isinstance(conditions, list) or not all(callable(cond) for cond in conditions):
            raise ValueError("'conditions'必须是可调用函数的列表（如lambda或def定义的函数）")
        if logic not in ["and", "or"]:
            raise ValueError(f"逻辑类型仅支持'and'/'or'，当前为{logic}")

        # 执行条件判断
        if logic == "and":
            return all(cond(element) for cond in conditions)
        else:
            return any(cond(element) for cond in conditions)

    else:
        raise TypeError(
            "condition_input仅支持3种类型：\n"
            "1. bool（直接指定是否满足）\n"
            "2. List[Callable]（条件函数列表，默认and逻辑）\n"
            "3. Dict（如{'conditions': [...], 'logic': 'or'}）"
        )


# ------------------------------------------------------------------------------
# 4. 对外统一接口（先判断条件，满足后再执行转换）
# ------------------------------------------------------------------------------
def convert_element_with_condition(element: Element,
                                   old_type: int,
                                   new_type: int,
                                   condition_input: Union[bool, List[Callable[[Element], bool]], Dict],
                                   converter: Optional[ElementConverter] = None) -> Element:
    """
    单个单元转换接口：先判断条件，满足后执行转换

    参数:
        element: 待转换单元
        old_type: 旧单元类型
        new_type: 新单元类型
        condition_input: 转换条件（3种输入方式）
        converter: 转换实例（可选，默认自动创建）

    返回:
        Element：转换后/原单元
    """
    # 初始化转换器（默认实例，也可外部传入自定义实例）
    if converter is None:
        converter = ElementConverter()

    # 步骤1：检查是否满足转换条件
    if not check_element_conversion_condition(element, old_type, condition_input):
        print(f"⚠️  单元{element.e_id}：不满足转换条件，保留原类型")
        return element

    # 步骤2：满足条件，执行转换
    return converter.execute_conversion(element, old_type, new_type)


def batch_convert_elements(elements: List[Element],
                           old_type: int,
                           new_type: int,
                           condition_input: Union[bool, List[Callable[[Element], bool]], Dict],
                           converter: Optional[ElementConverter] = None) -> List[Element]:
    """
    批量单元转换接口：对每个单元执行“条件判断→转换”流程

    参数:
        elements: 待转换单元列表
        old_type: 旧单元类型
        new_type: 新单元类型
        condition_input: 转换条件（3种输入方式）
        converter: 转换实例（可选）

    返回:
        List[Element]：转换后的单元列表
    """
    if not isinstance(elements, list):
        raise TypeError("elements必须是Element实例的列表")

    # 批量处理每个单元
    return [
        convert_element_with_condition(elem, old_type, new_type, condition_input, converter)
        for elem in elements
    ]


# ------------------------------------------------------------------------------
# 5. 完整测试示例（覆盖3种条件输入方式+批量转换）
# ------------------------------------------------------------------------------
def full_demo():
    """完整演示：创建测试数据→3种条件转换→输出结果"""
    print("=" * 80)
    print("1. 准备测试数据（节点+单元）")
    print("=" * 80)

    #  创建8个测试节点（坐标模拟实际场景）
    test_nodes = [
        Node(node_id=1, x=0.0, y=0.0, z=0.0),
        Node(node_id=2, x=1.0, y=0.0, z=0.0),
        Node(node_id=3, x=1.0, y=1.0, z=0.0),
        Node(node_id=4, x=0.0, y=1.0, z=0.0),
        Node(node_id=5, x=0.0, y=0.0, z=1.0),
        Node(node_id=6, x=1.0, y=0.0, z=1.0),
        Node(node_id=7, x=1.0, y=1.0, z=1.0),
        Node(node_id=8, x=1.0, y=1.0, z=1.0)  # 与节点7坐标重合
    ]

    # 创建3个测试单元（2个60号，1个9号）
    test_elements = [
        # 单元1：60号（满足转换条件：8节点、材料1、最后两节点重合）
        ElementFactory.create_element(
            e_id=101, t_id=60, m_id=1, points=test_nodes
        ),
        # 单元2：60号（不满足条件：7节点、材料2）
        ElementFactory.create_element(
            e_id=102, t_id=60, m_id=2, points=test_nodes[:7]
        ),
        # 单元3：9号（满足转换条件：6节点、材料1）
        ElementFactory.create_element(
            e_id=103, t_id=9, m_id=1, points=test_nodes[:6]
        )
    ]

    # 打印初始数据
    for elem in test_elements:
        print(f"初始单元：{elem}")

    # ------------------------------
    # 场景1：直接传bool条件（外部已判断，强制转换）
    # ------------------------------
    print("\n" + "=" * 80)
    print("2. 场景1：直接传bool条件（True=允许转换所有60→9）")
    print("=" * 80)
    # 复制测试数据（避免影响其他场景）
    elements_scene1 = [elem for elem in test_elements if elem.t_id == 60]
    # 批量转换：60→9，条件直接传True（所有60号单元都转）
    result_scene1 = batch_convert_elements(
        elements=elements_scene1,
        old_type=60,
        new_type=9,
        condition_input=True  # 外部强制允许转换
    )
    # 输出结果
    for elem in result_scene1:
        print(f"场景1结果：{elem}")

    # ------------------------------
    # 场景2：传条件函数列表（and逻辑，需所有条件满足）
    # ------------------------------
    print("\n" + "=" * 80)
    print("3. 场景2：条件函数列表（and逻辑：60→9需满足3个条件）")
    print("=" * 80)

    # 定义3个条件函数（60→9的严格条件）
    def cond_node_count(elem):
        """条件1：节点数=8"""
        return elem.num_point == 8

    def cond_material_id(elem):
        """条件2：材料ID=1"""
        return elem.m_id == 1

    def cond_last_two_nodes_coincide(elem):
        """条件3：最后两个节点坐标完全重合（精度1e-6）"""
        node7 = elem.points[-2]
        node8 = elem.points[-1]
        return (abs(node7.x - node8.x) < 1e-6 and
                abs(node7.y - node8.y) < 1e-6 and
                abs(node7.z - node8.z) < 1e-6)

    # 条件列表（and逻辑：所有条件必须满足）
    condition_list = [cond_node_count, cond_material_id, cond_last_two_nodes_coincide]

    # 批量转换60→9
    elements_scene2 = [elem for elem in test_elements if elem.t_id == 60]
    result_scene2 = batch_convert_elements(
        elements=elements_scene2,
        old_type=60,
        new_type=9,
        condition_input=condition_list
    )
    # 输出结果
    for elem in result_scene2:
        print(f"场景2结果：{elem}")

    # ------------------------------
    # 场景3：传带or逻辑的条件配置（满足任一条件即可）
    # ------------------------------
    print("\n" + "=" * 80)
    print("4. 场景3：带or逻辑的条件配置（9→60需满足任一条件）")
    print("=" * 80)
    # 条件配置：or逻辑（满足任一即可）
    condition_config = {
        "conditions": [
            lambda elem: elem.m_id == 1,  # 条件1：材料ID=1
            lambda elem: elem.num_point == 6  # 条件2：节点数=6
        ],
        "logic": "or"  # 满足任一条件即可转换
    }

    # 批量转换9→60
    elements_scene3 = [elem for elem in test_elements if elem.t_id == 9]
    result_scene3 = batch_convert_elements(
        elements=elements_scene3,
        old_type=9,
        new_type=60,
        condition_input=condition_config
    )
    # 输出结果
    for elem in result_scene3:
        print(f"场景3结果：{elem}")


# 执行完整测试
if __name__ == "__main__":
    full_demo()
