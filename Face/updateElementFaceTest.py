from Node.node import Node
from Element.ElementFactory import ElementFactory
import Face

# 节点初始化代码
nodes = []  # 节点列表
node_map = {}  # 节点映射字典

# 初始化所有节点
node1 = Node(1, 0.0, 1.0, 1.0, 0, 0, 0, 0, 0, 0, 0)      # y: 0.0 -> 1.0
nodes.append(node1)
node_map[1] = node1

node2 = Node(2, 2.0, 1.0, 1.0, 0, 0, 0, 0, 0, 0, 0)      # y: 0.0 -> 1.0
nodes.append(node2)
node_map[2] = node2

node3 = Node(3, 2.0, 1.0, 0.0, 0, 0, 0, 0, 0, 0, 0)      # y: 0.0 -> 1.0
nodes.append(node3)
node_map[3] = node3

node4 = Node(4, 0.0, 1.0, 0.0, 0, 0, 0, 0, 0, 0, 0)      # y: 0.0 -> 1.0
nodes.append(node4)
node_map[4] = node4

node5 = Node(5, 0.0, 2.0, 1.0, 0, 0, 0, 0, 0, 0, 0)      # y: 1.0 -> 2.0
nodes.append(node5)
node_map[5] = node5

node6 = Node(6, 2.0, 2.0, 1.0, 0, 0, 0, 0, 0, 0, 0)      # y: 1.0 -> 2.0
nodes.append(node6)
node_map[6] = node6

node7 = Node(7, 2.0, 2.0, 0.0, 0, 0, 0, 0, 0, 0, 0)      # y: 1.0 -> 2.0
nodes.append(node7)
node_map[7] = node7

node8 = Node(8, 0.0, 2.0, 0.0, 0, 0, 0, 0, 0, 0, 0)      # y: 1.0 -> 2.0
nodes.append(node8)
node_map[8] = node8

node9 = Node(9, 0.0, 0.0, 1.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node9)
node_map[9] = node9

node10 = Node(10, 1.0, 0.0, 1.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node10)
node_map[10] = node10

node11 = Node(11, 1.0, 0.0, 0.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node11)
node_map[11] = node11

node12 = Node(12, 0.0, 0.0, 0.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node12)
node_map[12] = node12

node13 = Node(13, 0.0, 1.0, 1.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node13)
node_map[13] = node13

node14 = Node(14, 1.0, 1.0, 1.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node14)
node_map[14] = node14

node15 = Node(15, 1.0, 1.0, 0.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node15)
node_map[15] = node15

node16 = Node(16, 0.0, 1.0, 0.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node16)
node_map[16] = node16

node17 = Node(17, 1.0, 0.0, 1.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node17)
node_map[17] = node17

node18 = Node(18, 2.0, 0.0, 1.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node18)
node_map[18] = node18

node19 = Node(19, 2.0, 0.0, 0.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node19)
node_map[19] = node19

node20 = Node(20, 1.0, 0.0, 0.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node20)
node_map[20] = node20

node21 = Node(21, 1.0, 1.0, 1.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node21)
node_map[21] = node21

node22 = Node(22, 2.0, 1.0, 1.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node22)
node_map[22] = node22

node23 = Node(23, 2.0, 1.0, 0.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node23)
node_map[23] = node23

node24 = Node(24, 1.0, 1.0, 0.0, 0, 0, 0, 0, 0, 0, 0)
nodes.append(node24)
node_map[24] = node24

#单元初始化代码
elements = []
element_map = {}

# 初始化所有单元
element1 = ElementFactory.create_element(1, 6, 0,1, 0, 0)
point_parts1 = [1, 2, 3, 4, 5, 6, 7, 8]
element1.read_points(point_parts1, node_map)
element_map[1] = element1
elements.append(element1)

element2 = ElementFactory.create_element(2, 6, 0,1, 0, 0)
point_parts2 = [9, 10, 11, 12, 13, 14, 15, 16]
element2.read_points(point_parts2, node_map)
element_map[2] = element2
elements.append(element2)

element3 = ElementFactory.create_element(3, 6, 0,1, 0, 0)
point_parts3 = [17, 18, 19, 20, 21, 22, 23, 24]
element3.read_points(point_parts3, node_map)
element_map[3] = element3
elements.append(element3)

element4 = element1.to_element57()
element5 = element2.to_element57()
element6 = element3.to_element57()

new_element4 = Face.update_element57_faces(element4, [1, 2, 3, 4], [node13, node14, node15, node16], [node21, node22, node23, node24])
for i, face_nodes in enumerate(new_element4.mianDian):
    print("第"+str(i)+"个面的组成节点编号")
    for node in face_nodes:
        print(node.node_id)


