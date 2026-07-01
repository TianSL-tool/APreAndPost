from Node.node import Node
from Element.ElementFactory import ElementFactory
import Face

# 节点初始化代码
nodes = []  # 节点列表
node_map = {}  # 节点映射字典

# 初始化所有节点
node1 = Node(1, 0.0, 0.0, 1.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node1)
node_map[1] = node1

node2 = Node(2, 1.0, 0.0, 1.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node2)
node_map[2] = node2

node3 = Node(3, 1.0, 0.0, 0.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node3)
node_map[3] = node3

node4 = Node(4, 0.0, 0.0, 0.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node4)
node_map[4] = node4

node5 = Node(5, 0.0, 1.0, 1.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node5)
node_map[5] = node5

node6 = Node(6, 1.0, 1.0, 1.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node6)
node_map[6] = node6

node7 = Node(7, 1.0, 1.0, 0.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node7)
node_map[7] = node7

node8 = Node(8, 0.0, 1.0, 0.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node8)
node_map[8] = node8

node9 = Node(9, 0.5, 2.0, 0.5, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node9)
node_map[9] = node9

#单元初始化代码
elements = []
element_map = {}

# 初始化所有单元
element1 = ElementFactory.create_element(1, 6, 0,1, 0, 0)
point_parts1 = [1, 2, 3, 4, 5, 6, 7, 8]
element1.read_points(point_parts1, node_map)
element_map[1] = element1
elements.append(element1)

element2 = ElementFactory.create_element(2, 57, 0, 1, 0,0)
point_parts2 = [5, 4, 3, 3, 3, 3, 5, 8, 7, 6, 9, 5, 6, 9, 8, 5, 9, 7, 8, 9, 6, 7]
element2.read_points(point_parts2, node_map)
element_map[2] = element2
elements.append(element2)

Face.create_face_list(elements)
