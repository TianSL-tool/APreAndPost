import pandas as pd
import numpy as np
import datetime


class Control:
    def __init__(self, method, direction, scale, scale2):
        self.working_condition = " "
        self.total_num = None
        self.method = method
        self.direction = direction

        self.scale = scale
        self.scale2 = scale2
        self.scale3 = -1000

        self.cadxdirection = 0
        self.cadydirection = 1
        self.cadxnotedis = 0
        self.cadynotedis = -3
        self.contsize = 4

        self.realinitvalue = -1
        self.calcinitvalue = -1

        self.adddis = 1
        self.readNodeMethod = 1

        self.initTime = 0


class NodePair:
    def __init__(self, pairNum):
        self.pairNum = pairNum
        self.cedianLabel = []
        self.cedianId = []
        self.nodeId = []
        self.cedianCoor = []
        self.pair_type = ["node" for i in range(pairNum)]

def get_value2(cell, default):
    if isinstance(cell, pd.Series):
        # 对 Series 中的每个元素进行判断
        result = [default if pd.isna(value) else value for value in cell]
        return result
    else:
        return default if pd.isna(cell) else cell

class StepPair:
    def __init__(self, pairNum):
        self.pairNum = pairNum
        self.step = []
        self.time = []


class Node:
    def __init__(self, cedianId):
        self.cedianId = cedianId
        self.type = "node"
        self.sheetName = ''
        self.local = 0
        self.colNum = 0
        self.label = 0
        self.nodeId = 0
        self.valuenum = 4

        self.intTime = 0
        self.endTime = []

        self.time = []
        self.calcTime = []
        self.calcStep = []

        # 以下几个变量是输出监测时程和计算时程
        self.coor = np.zeros((1, 4))  #节点坐标

        self.coorCalcDis = np.zeros(4)  #计算节点位移
        self.coorCalcInitDis = np.zeros(4)  #计算节点初始位移
        self.coorCalcEndDis = []  #计算节点固定时间节点的位移
        self.coorCalcInterDis = []  #计算节点固定时间节点的位移增量（减去起测时间的位移）

        self.coorRealDis = []  #监测位移时程
        self.coorRealDis_noclear = []  #监测位移时程，经过数据清洗
        self.coorRealInitDis = 0  #监测位移时程，起测的位移
        self.coorRealEndDis = []  #监测固定时间节点的位移
        self.coorRealInterDis = []  #监测固定时间节点的位移增量（减去起测位移）

        # 以下几个变量是输出cad图纸节点位置相关

        self.originRealEndDis = []  #固定时间的测点坐标
        self.originRealEndDis_tostr = []  #固定时间的测点坐标偏移后的
        self.originRealEndDisNote_tostr = []  #坐标注释

        self.originRealInterDis = []  #固定时间的测点坐标 同self.originRealEndDis
        self.originRealInterDis_tostr = []  #固定时间的测点坐标偏移后的（增量）
        self.originRealInterDisNote_tostr = []  #坐标注释

        self.originCalcEndDis = []  #固定时间的测点坐标 同self.originRealEndDis
        self.originCalcEndDis_tostr = []  #固定时间的测点坐标根据计算值偏移后的
        self.originCalcEndDisNote_tostr = []  #坐标注释

        self.originCalcInterDis = []  #固定时间的测点坐标 同self.originRealEndDis
        self.originCalcInterDis_tostr = []  #固定时间的测点坐标根据计算值偏移后的（增量）
        self.originCalcInterDisNote_tostr = []  #坐标注释

        self.is_changeTimeType = False
        self.is_calc_coorRealInitDis = False
        self.is_calc_coorRealInterDis = False

        self.is_changeNodeTimeType = False
        self.is_calc_coorNodeInitDis = False
        self.is_calc_coorNodeInterDis = False

    def changeTimeType(self):
        if self.is_changeTimeType == True:
            pass
        else:
            self.intTime = float(self.intTime.timestamp())
            for i in range(len(self.time)):
                if isinstance(self.time[i], datetime.datetime):
                    self.time[i] = float(self.time[i].timestamp())
            for i in range(len(self.endTime)):
                if isinstance(self.endTime[i], datetime.datetime):
                    self.endTime[i] = float(self.endTime[i].timestamp())
            self.is_changeTimeType = True

    def calc_coorRealInitDis(self, control):
        if self.is_calc_coorRealInitDis == True:
            pass
        elif control.realinitvalue == -1:
            self.changeTimeType()
            for i in range(len(self.time) - 1):
                if self.time[i] <= self.intTime < self.time[i + 1]:
                    self.coorRealInitDis = (self.coorRealDis[i + 1] - self.coorRealDis[i]) / (
                            self.time[i + 1] - self.time[i]) * (self.intTime - self.time[i]) + self.coorRealDis[i]
                    break
            self.is_calc_coorRealInitDis = True
        else:
            self.changeTimeType()
            self.coorRealInitDis = control.realinitvalue
            self.is_calc_coorRealInitDis = True

    def calc_coorRealInterDis(self, control):
        if self.is_calc_coorRealInterDis == True:
            pass
        else:
            print("cedian",self.cedianId)
            # print("self.time", self.time)
            # print("elf.coorRealDis", self.coorRealDis)
            # print("elf.endTime", self.endTime)

            self.calc_coorRealInitDis(control)
            for n in range(len(self.endTime)):
                for i in range(len(self.time) - 1):
                    if self.endTime[n] <= self.time[0]:
                        self.coorRealEndDis.append(0)
                        self.coorRealInterDis.append(0)
                        break
                    elif self.endTime[n] > self.time[len(self.time) - 1]:
                        self.coorRealEndDis.append(0)
                        self.coorRealInterDis.append(0)
                        break
                    elif self.time[i] < self.endTime[n] <= self.time[i + 1]:

                        coorRealEndDis = (self.coorRealDis[i + 1] - self.coorRealDis[i]) / (
                                self.time[i + 1] - self.time[i]) * (self.endTime[n] - self.time[i]) + self.coorRealDis[
                                             i]
                        self.coorRealEndDis.append(coorRealEndDis)
                        coorRealInteDis = coorRealEndDis - self.coorRealInitDis
                        self.coorRealInterDis.append(coorRealInteDis)
                        break

            self.coorRealEndDis = np.array(self.coorRealEndDis)
            self.coorRealInterDis = np.array(self.coorRealInterDis)

            self.is_calc_coorRealInterDis = True

    def changeNodeTimeType(self):
        if self.is_changeNodeTimeType == True:
            pass
        else:
            for i in range(len(self.calcTime)):
                if isinstance(self.calcTime[i], datetime.datetime):
                    self.calcTime[i] = float(self.calcTime[i].timestamp())
            self.is_changeNodeTimeType = True

    def calc_coorNodeInitDis(self, control):
        if self.is_calc_coorNodeInitDis == True:
            pass
        elif control.calcinitvalue == -1:
            self.changeNodeTimeType()
            if self.intTime < self.calcTime[0]:
                print("测点：", self.label, self.cedianId, "起始监测时间小于计算的初始填筑时间")
                self.coorCalcInitDis = self.coorCalcDis[0]
            elif self.intTime > self.calcTime[-1]:
                print("测点：", self.label, self.cedianId, "起始监测时间大于计算的最后步的时间")
                self.coorCalcInitDis = self.coorCalcDis[-1]
            else:
                for i in range(len(self.calcTime) - 1):
                    if self.calcTime[i] <= self.intTime < self.calcTime[i + 1]:
                        self.coorCalcInitDis = (self.coorCalcDis[i + 1] - self.coorCalcDis[i]) / (
                                self.calcTime[i + 1] - self.calcTime[i]) * (self.intTime - self.calcTime[i]) + \
                                               self.coorCalcDis[i]
                        break
            self.is_calc_coorNodeInitDis = True
        else:
            self.changeNodeTimeType()
            self.coorCalcInitDis = np.zeros(self.valuenum)
            self.is_calc_coorNodeInitDis = True

    def calc_coorNodeInterDis(self, control):
        if self.is_calc_coorNodeInterDis == True:
            pass
        else:
            self.calc_coorNodeInitDis(control)
            for n in range(len(self.endTime)):
                if self.endTime[n] <= self.calcTime[0]:
                    self.coorCalcInterDis.append(np.zeros(self.valuenum))
                    self.coorCalcEndDis.append(np.zeros(self.valuenum))
                    print("测点：", self.label, self.cedianId, "计算初始时间大于时刻", self.endTime[n])
                    continue
                elif self.endTime[n] > self.calcTime[len(self.calcTime) - 1]:
                    self.coorCalcInterDis.append(np.zeros(self.valuenum))
                    self.coorCalcEndDis.append(np.zeros(self.valuenum))
                    print("测点：", self.label, self.cedianId, "计算最终时间小于时刻", self.endTime[n])
                    continue

                for i in range(len(self.calcTime) - 1):
                    if self.calcTime[i] < self.endTime[n] <= self.calcTime[i + 1]:
                        coorCalcEndDis = (self.coorCalcDis[i + 1] - self.coorCalcDis[i]) / (
                                self.calcTime[i + 1] - self.calcTime[i]) * (self.endTime[n] - self.calcTime[i]) + \
                                         self.coorCalcDis[i]
                        self.coorCalcEndDis.append(coorCalcEndDis)
                        coorCalcInteDis = coorCalcEndDis - self.coorCalcInitDis
                        self.coorCalcInterDis.append(coorCalcInteDis)
                        break
            # print("测点：", self.label, self.cedianId)
            # print(self.coorCalcInterDis)
            self.coorCalcInterDis = np.array(self.coorCalcInterDis)
            self.coorCalcEndDis = np.array(self.coorCalcEndDis)
            self.is_calc_coorNodeInterDis = True


def get_value(cell, default):
    """
    检查单元格是否为空，如果为空则返回默认值，否则返回单元格的值
    """
    if pd.isna(cell):
        return default
    return cell


# def readControl(name, num):
#     numinit = 2
#
#     sheets = pd.read_excel(name, sheet_name=None, header=None)
#     control_sheet = sheets['control']
#     sheet_name = str(control_sheet.iloc[num, 0])
#     control_sheet_noheader = sheets[sheet_name]
#
#     method = int(control_sheet_noheader.iloc[0 + numinit, 1])
#     direction = int(control_sheet_noheader.iloc[1 + numinit, 1])
#     scale = float(control_sheet_noheader.iloc[2 + numinit, 1])
#     scale2 = float(control_sheet_noheader.iloc[3 + numinit, 1])
#     calcName = str(control_sheet_noheader.iloc[4 + numinit, 0])
#     control = Control(method, direction, scale, scale2)
#     control.working_condition = str(control_sheet_noheader.iloc[0, 1])
#
#     control.cadxdirection = int(get_value(control_sheet_noheader.iloc[5 + numinit, 1], control.cadxdirection))
#     control.cadydirection = int(get_value(control_sheet_noheader.iloc[6 + numinit, 1], control.cadydirection))
#     control.adddis = int(get_value(control_sheet_noheader.iloc[7 + numinit, 1], control.adddis))
#     control.realinitvalue = float(get_value(control_sheet_noheader.iloc[8 + numinit, 1], control.realinitvalue))
#     control.scale3 = float(get_value(control_sheet_noheader.iloc[9 + numinit, 1], control.scale3))
#     control.calcinitvalue = float(get_value(control_sheet_noheader.iloc[10 + numinit, 1], control.calcinitvalue))
#     control.cadxnotedis = int(get_value(control_sheet_noheader.iloc[11 + numinit, 1], control.cadxnotedis))
#     control.cadynotedis = int(get_value(control_sheet_noheader.iloc[12 + numinit, 1], control.cadynotedis))
#     control.contsize = int(get_value(control_sheet_noheader.iloc[13 + numinit, 1], control.contsize))
#     control.readNodeMethod = int(get_value(control_sheet_noheader.iloc[14 + numinit, 1], control.readNodeMethod))
#     control.initTime = get_value(control_sheet_noheader.iloc[15 + numinit, 1], control.initTime)
#
#     # if control.initTime!=0:
#     #     control.initTime =
#
#     endTimeNum = control_sheet_noheader.iloc[1, 3]
#     endTime = control_sheet_noheader.iloc[2:2 + endTimeNum, 3].values
#
#     control.total_num = int(control_sheet_noheader.iloc[0, 4])
#     stepPair = StepPair(int(control_sheet_noheader.iloc[0, 4]))
#
#     stepPair.time = control_sheet_noheader.iloc[1:stepPair.pairNum + 1, 5].values
#     stepPair.step = control_sheet_noheader.iloc[1:stepPair.pairNum + 1, 6].values
#
#     nodepair = NodePair(int(control_sheet.iloc[0, 1]))
#     nodepair.cedianLabel = control_sheet.iloc[0:nodepair.pairNum, 2].values
#     nodepair.cedianId = control_sheet.iloc[0:nodepair.pairNum, 3].values
#     nodepair.nodeId = control_sheet.iloc[0:nodepair.pairNum, 4].values
#     nodepair.cedianCoor = control_sheet.iloc[0:nodepair.pairNum, 5:8].values
#     nodepair.pair_type = get_value2(control_sheet.iloc[0:nodepair.pairNum, 8], nodepair.pair_type)
#     for i in range(len(nodepair.pair_type)):
#         if nodepair.pair_type[i]!="node" and nodepair.pair_type[i]!="ele":
#             nodepair.pair_type[i] = "node"
#
#
#     resortnode = None
#     is_resortnode = 0
#     if control_sheet_noheader.shape[1] > 9:
#         value = control_sheet_noheader.iloc[0, 9]
#         if not np.isnan(value):
#             is_resortnode = int(value)
#         else:
#             is_resortnode = 0
#
#     if is_resortnode == 1:
#         resortnode = []
#         num_rownode = int(control_sheet_noheader.iloc[1, 9])
#         for i in range(num_rownode):
#             num_sortnode = int(control_sheet_noheader.iloc[i + 2, 8])
#             resortnode.append(control_sheet_noheader.iloc[i + 2, 9:9 + num_sortnode])
#
#     return method, control, endTime, stepPair, nodepair, calcName, resortnode
def readControl(name, num):
    numinit = 2

    sheets = pd.read_excel(name, sheet_name=None, header=None)
    control_sheet = sheets['control']

    # 检查 control_sheet 是否有足够的行
    control_rows, control_cols = control_sheet.shape

    # 安全获取 sheet_name
    if num >= control_rows:
        raise ValueError(f"Row index {num} is out of bounds for control_sheet with {control_rows} rows")
    sheet_name = str(control_sheet.iloc[num, 0])

    # 确保 sheet_name 存在于 sheets 中
    if sheet_name not in sheets:
        raise ValueError(f"Sheet '{sheet_name}' not found in Excel file")

    control_sheet_noheader = sheets[sheet_name]
    noheader_rows, noheader_cols = control_sheet_noheader.shape

    # 安全获取基本控制参数
    method = _safe_get_value(control_sheet_noheader, 0 + numinit, 1, int)
    direction = _safe_get_value(control_sheet_noheader, 1 + numinit, 1, int)
    scale = _safe_get_value(control_sheet_noheader, 2 + numinit, 1, float)
    scale2 = _safe_get_value(control_sheet_noheader, 3 + numinit, 1, float)
    calcName = _safe_get_value(control_sheet_noheader, 4 + numinit, 0, str)

    control = Control(method, direction, scale, scale2)
    control.working_condition = _safe_get_value(control_sheet_noheader, 0, 1, str)

    # 安全获取其他控制参数
    control.cadxdirection = _safe_get_value(control_sheet_noheader, 5 + numinit, 1, int, control.cadxdirection)
    control.cadydirection = _safe_get_value(control_sheet_noheader, 6 + numinit, 1, int, control.cadydirection)
    control.adddis = _safe_get_value(control_sheet_noheader, 7 + numinit, 1, int, control.adddis)
    control.realinitvalue = _safe_get_value(control_sheet_noheader, 8 + numinit, 1, float, control.realinitvalue)
    control.scale3 = _safe_get_value(control_sheet_noheader, 9 + numinit, 1, float, control.scale3)
    control.calcinitvalue = _safe_get_value(control_sheet_noheader, 10 + numinit, 1, float, control.calcinitvalue)
    control.cadxnotedis = _safe_get_value(control_sheet_noheader, 11 + numinit, 1, int, control.cadxnotedis)
    control.cadynotedis = _safe_get_value(control_sheet_noheader, 12 + numinit, 1, int, control.cadynotedis)
    control.contsize = _safe_get_value(control_sheet_noheader, 13 + numinit, 1, int, control.contsize)
    control.readNodeMethod = _safe_get_value(control_sheet_noheader, 14 + numinit, 1, int, control.readNodeMethod)
    control.initTime = _safe_get_value(control_sheet_noheader, 15 + numinit, 1, lambda x: x, control.initTime)

    # 安全获取 endTime
    if 3 < noheader_cols and 2 < noheader_rows:
        endTimeNum = min(int(control_sheet_noheader.iloc[1, 3]), noheader_rows - 2)
        endTime = control_sheet_noheader.iloc[2:2 + endTimeNum, 3].values
    else:
        endTime = []

    # 安全获取 stepPair
    if 4 < noheader_cols and 0 < noheader_rows:
        control.total_num = int(control_sheet_noheader.iloc[0, 4])
        stepPair = StepPair(control.total_num)

        max_step_rows = min(stepPair.pairNum, noheader_rows - 1)
        if 5 < noheader_cols and 1 < noheader_rows:
            stepPair.time = control_sheet_noheader.iloc[1:1 + max_step_rows, 5].values
        else:
            stepPair.time = np.array([])

        if 6 < noheader_cols and 1 < noheader_rows:
            stepPair.step = control_sheet_noheader.iloc[1:1 + max_step_rows, 6].values
        else:
            stepPair.step = np.array([])
    else:
        control.total_num = 0
        stepPair = StepPair(0)
        stepPair.time = np.array([])
        stepPair.step = np.array([])

    # 安全获取 nodepair
    if 1 < control_cols and 0 < control_rows:
        max_pair_num = min(int(control_sheet.iloc[0, 1]), control_rows)
        nodepair = NodePair(max_pair_num)

        # 安全获取各列数据
        nodepair.cedianLabel = _safe_get_column(control_sheet, 0, max_pair_num, 2)
        nodepair.cedianId = _safe_get_column(control_sheet, 0, max_pair_num, 3)
        nodepair.nodeId = _safe_get_column(control_sheet, 0, max_pair_num, 4)
        nodepair.cedianCoor = _safe_get_range(control_sheet, 0, max_pair_num, 5, 8)

        # 安全获取 pair_type
        if 8 < control_cols:
            nodepair.pair_type = get_value2(control_sheet.iloc[0:max_pair_num, 8], nodepair.pair_type)
        else:
            nodepair.pair_type = [nodepair.pair_type] * max_pair_num

        # 验证 pair_type 值
        for i in range(len(nodepair.pair_type)):
            if nodepair.pair_type[i] != "node" and nodepair.pair_type[i] != "ele":
                nodepair.pair_type[i] = "node"
    else:
        nodepair = NodePair(0)
        nodepair.cedianLabel = np.array([])
        nodepair.cedianId = np.array([])
        nodepair.nodeId = np.array([])
        nodepair.cedianCoor = np.array([])
        nodepair.pair_type = []

    # 安全处理 resortnode
    resortnode = None
    is_resortnode = 0
    if noheader_cols > 9 and 0 < noheader_rows:
        value = control_sheet_noheader.iloc[0, 9]
        if not np.isnan(value):
            is_resortnode = int(value)
        else:
            is_resortnode = 0

    if is_resortnode == 1 and noheader_cols > 9 and 1 < noheader_rows:
        resortnode = []
        num_rownode = min(int(control_sheet_noheader.iloc[1, 9]), noheader_rows - 2)
        for i in range(num_rownode):
            if 8 < noheader_cols:
                num_sortnode = min(int(control_sheet_noheader.iloc[i + 2, 8]), noheader_cols - 9)
                if num_sortnode > 0:
                    resortnode.append(control_sheet_noheader.iloc[i + 2, 9:9 + num_sortnode])
                else:
                    resortnode.append([])
            else:
                resortnode.append([])

    return method, control, endTime, stepPair, nodepair, calcName, resortnode


# 辅助函数：安全获取单个单元格的值
def _safe_get_value(df, row, col, dtype, default=None):
    rows, cols = df.shape
    if row < rows and col < cols:
        value = df.iloc[row, col]
        if pd.isna(value):
            return default if default is not None else dtype()
        try:
            return dtype(value)
        except (ValueError, TypeError):
            return default if default is not None else dtype()
    else:
        return default if default is not None else dtype()


# 辅助函数：安全获取单列数据
def _safe_get_column(df, start_row, end_row, col):
    rows, cols = df.shape
    if col >= cols:
        return np.array([])
    safe_end = min(end_row, rows)
    if start_row >= safe_end:
        return np.array([])
    return df.iloc[start_row:safe_end, col].values


# 辅助函数：安全获取数据范围
def _safe_get_range(df, start_row, end_row, start_col, end_col):
    rows, cols = df.shape
    safe_end_row = min(end_row, rows)
    safe_end_col = min(end_col, cols)
    if start_row >= safe_end_row or start_col >= safe_end_col:
        return np.array([])
    return df.iloc[start_row:safe_end_row, start_col:safe_end_col].values

def readCedianInfor(name, method, endTime, stepPair, nodepair, control):
    # 读取 Excel 文件中的所有工作表
    sheets = pd.read_excel(name, sheet_name=None, header=None)

    # 获取第一个工作表的名称
    control_sheet_noheader = sheets[list(sheets.keys())[0]]

    sheetNum = control_sheet_noheader.iloc[0, 1]
    cedianLabel = control_sheet_noheader.iloc[0, 4]
    sheetName = []
    nodeId = []
    InitTime = []
    node = [[] for i in range(int(sheetNum))]

    for i in range(int(sheetNum)):
        sheetName.append(control_sheet_noheader.iloc[3 * i + 1, 0])
        nodeId.append(control_sheet_noheader.iloc[3 * i + 2].values)
        InitTime.append(control_sheet_noheader.iloc[3 * i + 3].values)
        if control.initTime != 0:
            for j in range(len(InitTime[i])):
                InitTime[i][j] = control.initTime

        for j in range(len(nodeId[i])):

            if pd.isna(nodeId[i][j]):
                continue
            else:
                node[i].append(Node(nodeId[i][j]))
                node[i][j].sheetName = sheetName[i]
                node[i][j].intTime = InitTime[i][j]
                node[i][j].endTime = endTime
                node[i][j].label = cedianLabel
                for k in range(len(nodepair.cedianId)):
                    if nodepair.cedianId[k] == node[i][j].cedianId and nodepair.cedianLabel[k] == node[i][j].label:
                        node[i][j].nodeId = nodepair.nodeId[k]
                        node[i][j].type = nodepair.pair_type[k]
                        node[i][j].coor = nodepair.cedianCoor[k]

    sheets2 = pd.read_excel(name, sheet_name=None)

    for i in range(len(sheetName)):
        control_sheet_noheader = sheets[sheetName[i]]
        control_sheet = sheets2[sheetName[i]]

        # 数据清洗
        control_sheet_fill = control_sheet.ffill(axis=0).bfill(axis=0)
        for j in range(len(node[i])):
            if control.readNodeMethod == 1:
                node[i][j].time = control_sheet_noheader.iloc[1:, 0].values
                node[i][j].coorRealDis = control_sheet_fill.iloc[:, j + 1].values
                node[i][j].coorRealDis_noclear = control_sheet.iloc[:, j + 1].values
            else:
                # node[i][j].time = control_sheet_noheader.iloc[1:, j * 2].values
                time_data = control_sheet_noheader.iloc[1:, j * 2].dropna()
                node[i][j].time = time_data.values
                node[i][j].coorRealDis = control_sheet_fill.iloc[:, j * 2 + 1].values
                node[i][j].coorRealDis_noclear = control_sheet.iloc[:, j * 2 + 1].values
            # print(node[i][j].time)
            # print(node[i][j].coorRealDis)
    for i in node:
        for j in i:
            j.calc_coorRealInterDis(control)

            j.originRealEndDis = np.tile(j.coor, (len(j.endTime), 1))
            j.originRealInterDis = np.tile(j.coor, (len(j.endTime), 1))

            for k in range(len(j.endTime)):
                if control.method == 1:
                    # print(j.originRealEndDis)
                    # print(j.coorRealEndDis)
                    # print(k)
                    # print(control.adddis)
                    # print(j.coor)
                    j.originRealEndDis[k, control.adddis] = j.coor[control.adddis] + j.coorRealEndDis[
                        k] * control.scale2

                    j.originRealInterDis[k, control.adddis] = j.coor[control.adddis] + j.coorRealInterDis[
                        k] * control.scale2

                    j.originRealEndDis_tostr.append(
                        str(j.originRealEndDis[k, control.cadxdirection]) + ',' + str(
                            j.originRealEndDis[k, control.cadydirection]))

                    j.originRealInterDis_tostr.append(
                        str(j.originRealInterDis[k, control.cadxdirection]) + ',' + str(
                            j.originRealInterDis[k, control.cadydirection]))

                    j.originRealEndDisNote_tostr.append(
                        "-text j ml " + str(
                            j.originRealEndDis[k, control.cadxdirection] + control.cadxnotedis) + ',' + str(
                            j.originRealEndDis[k, control.cadydirection] + control.cadynotedis) + " " + str(
                            control.contsize) + " 0 " + str(int(j.coorRealEndDis[k])))

                    j.originRealInterDisNote_tostr.append(
                        "-text j ml " + str(
                            j.originRealInterDis[k, control.cadxdirection] + control.cadxnotedis) + ',' + str(
                            j.originRealInterDis[k, control.cadydirection] + control.cadynotedis) + " " + str(
                            control.contsize) + " 0 " + str(int(j.coorRealInterDis[k])))

    return sheetName, node


def readnodeInfor(node, endTime, stepPair, nodepair, control, dim):
    for i in node:
        for j in i:
            nodeFileName = str(int(j.nodeId)) + '.'+ j.type
            try:
                # 读取数据文件
                data_list = []
                with open(nodeFileName, 'r') as file:
                    next(file)
                    for line in file:
                        row = [float(x) for x in line.strip().split()]
                        data_list.append(row)
                    data = np.array(data_list)
                # data = np.genfromtxt(nodeFileName, delimiter=',')
                # 检查数据是否为二维数组，如果是一维数组则列数为 1
                if data.ndim == 1:
                    columns = 1
                    data = data.reshape(1, -1)
                    j.coorCalcDis = data[:, 1:columns]
                else:
                    columns = data.shape[1]
                    j.coorCalcDis = data[:, 1:columns]
                j.calcStep = data[:, 0]
                j.valuenum = columns - 1
            except FileNotFoundError:
                print("错误：文件未找到，请检查文件路径和文件名。")
            except Exception as e:
                print(f"错误：发生了一个未知错误：{e}")

            # print("*************************************",control.direction)
            # print(control.scale)

            for k in j.calcStep:
                for l in range(len(stepPair.step)):
                    if stepPair.step[l] == k:
                        j.calcTime.append(stepPair.time[l])

            j.calc_coorNodeInterDis(control)
            j.originCalcEndDis = np.tile(j.coor, (len(j.endTime), 1))
            j.originCalcInterDis = np.tile(j.coor, (len(j.endTime), 1))

            for k in range(len(j.endTime)):
                if control.method == 1:
                    if len(j.coorCalcEndDis) <= 0:
                        continue
                    j.originCalcEndDis[k, control.adddis] = j.coor[control.adddis] + \
                                                            j.coorCalcEndDis[k, control.direction] * control.scale
                    j.originCalcInterDis[k, control.adddis] = j.coor[control.adddis] + \
                                                              j.coorCalcInterDis[k, control.direction] * control.scale
                    j.originCalcEndDis_tostr.append(
                        str(j.originCalcEndDis[k, control.cadxdirection]) + ',' + str(
                            j.originCalcEndDis[k, control.cadydirection]))
                    j.originCalcInterDis_tostr.append(
                        str(j.originCalcInterDis[k, control.cadxdirection]) + ',' + str(
                            j.originCalcInterDis[k, control.cadydirection]))

                    j.originCalcEndDisNote_tostr.append(
                        "-text j ml " + str(
                            j.originCalcEndDis[k, control.cadxdirection] - control.cadxnotedis) + ',' + str(
                            j.originCalcEndDis[k, control.cadydirection] - control.cadynotedis) + " " + str(
                            control.contsize) + " 0 " + str(
                            int(j.coorCalcEndDis[k, control.direction] * control.scale3)))
                    j.originCalcInterDisNote_tostr.append(
                        "-text j ml " + str(
                            j.originCalcInterDis[k, control.cadxdirection] - control.cadxnotedis) + ',' + str(
                            j.originCalcInterDis[k, control.cadydirection] - control.cadynotedis) + " " + str(
                            control.contsize) + " 0 " + str(
                            int(j.coorCalcInterDis[k, control.direction] * control.scale3)))

# def writeNodeInfor(name, sheetName, control, endTime, node, resortnode):
#     # 初始化数据存储列表
#     dataendtimedic = []
#     dataRealEndDis = []
#     dataRealInterDis = []
#     dataCalcEndDis = []
#     dataCalcInterDis = []
#     dataOriginRealEndDis_tostr = []
#     dataOriginRealInterDis_tostr = []
#     dataOriginCalcEndDis_tostr = []
#     dataOriginCalcInterDis_tostr = []
#     dataOriginRealEndDisNote_tostr = []
#     dataOriginRealInterDisNote_tostr = []
#     dataOriginCalcEndDisNote_tostr = []
#     dataOriginCalcInterDisNote_tostr = []
#
#     # 存储每个sheet的节点坐标数据（x、y、z单独存储）
#     dataNodeCoor = []
#
#     # 处理节点排序
#     if resortnode is not None:
#         node2 = []
#         for sub_list in resortnode:
#             sub_node2 = []
#             for sub_i in sub_list:
#                 for k in node:
#                     found_node = next((l for l in k if l.cedianId == sub_i), None)
#                     if found_node:
#                         sub_node2.append(found_node)
#                         break
#             node2.append(sub_node2)
#     else:
#         node2 = node
#
#     # 转换时间戳为datetime对象
#     for i in range(len(endTime)):
#         endTime[i] = datetime.datetime.fromtimestamp(endTime[i])
#
#     for i in range(len(node2)):
#         # 初始化数据字典
#         dataendtimedicson = {}
#         dataRealEndDisDic = {}
#         dataRealInterDisDic = {}
#         dataCalcEndDisDic = {}
#         dataCalcInterDisDic = {}
#         dataOriginRealEndDisDic_tostr = {}
#         dataOriginRealInterDisDic_tostr = {}
#         dataOriginCalcEndDisDic_tostr = {}
#         dataOriginCalcInterDisDic_tostr = {}
#         dataOriginRealEndDisNoteDic_tostr = {}
#         dataOriginRealInterDisNoteDic_tostr = {}
#         dataOriginCalcEndDisNoteDic_tostr = {}
#         dataOriginCalcInterDisNoteDic_tostr = {}
#
#         # 坐标数据字典（关键修改：x、y、z分开展示）
#         node_coor_dic = {}
#         for j in node2[i]:
#             # 提取坐标值（shape为(1,4)的numpy数组）
#             # 关键修改：展平为一维列表并拆分x、y、z
#             coor_1d = j.coor.flatten()  # 转为一维数组 [x, y, z, w]
#             x, y, z = coor_1d[0], coor_1d[1], coor_1d[2]  # 提取三个方向的坐标
#
#             # 存储格式：节点ID_x、节点ID_y、节点ID_z（每个方向单独一列）
#             node_coor_dic[f"{j.cedianId}_x"] = [x]
#             node_coor_dic[f"{j.cedianId}_y"] = [y]
#             node_coor_dic[f"{j.cedianId}_z"] = [z]
#
#             # 原有数据收集（保持不变）
#             dataRealEndDisDic[str(j.cedianId) + 'real'] = j.coorRealEndDis
#             dataRealInterDisDic[str(j.cedianId) + 'real'] = j.coorRealInterDis
#             dataOriginRealEndDisDic_tostr[str(j.cedianId) + 'real'] = j.originRealEndDis_tostr
#             dataOriginRealInterDisDic_tostr[str(j.cedianId) + 'real'] = j.originRealInterDis_tostr
#
#             dataOriginRealEndDisNoteDic_tostr[str(j.cedianId) + 'real'] = j.originRealEndDisNote_tostr
#             dataOriginRealInterDisNoteDic_tostr[str(j.cedianId) + 'real'] = j.originRealInterDisNote_tostr
#             if len(j.coorcalcEndDis) > 0:
#                 dataCalcEndDisDic[str(j.cedianId) + 'calc'] = j.coorcalcEndDis[:, control.direction] * control.scale3
#                 dataCalcInterDisDic[str(j.cedianId) + 'calc'] = j.coorCalcInterDis[:, control.direction] * control.scale3
#                 dataOriginCalcEndDisDic_tostr[str(j.cedianId) + 'calc'] = j.originCalcEndDis_tostr
#                 dataOriginCalcInterDisDic_tostr[str(j.cedianId) + 'calc'] = j.originCalcInterDis_tostr
#                 dataOriginCalcEndDisNoteDic_tostr[str(j.cedianId) + 'calc'] = j.originCalcEndDisNote_tostr
#                 dataOriginCalcInterDisNoteDic_tostr[str(j.cedianId) + 'calc'] = j.originCalcInterDisNote_tostr
#
#         # 坐标数据转为DataFrame
#         dataNodeCoor.append(pd.DataFrame(node_coor_dic))
#
#         # 其他数据转为DataFrame（保持不变）
#         dataendtimedicson[sheetName[i]] = endTime
#         dataendtimedic.append(pd.DataFrame(dataendtimedicson))
#
#         dataRealEndDis.append(pd.DataFrame(dataRealEndDisDic))
#         dataRealInterDis.append(pd.DataFrame(dataRealInterDisDic))
#
#         dataCalcEndDis.append(pd.DataFrame(dataCalcEndDisDic))
#         dataCalcInterDis.append(pd.DataFrame(dataCalcInterDisDic))
#
#         dataOriginRealEndDis_tostr.append(pd.DataFrame(dataOriginRealEndDisDic_tostr))
#         dataOriginRealInterDis_tostr.append(pd.DataFrame(dataOriginRealInterDisDic_tostr))
#
#         dataOriginCalcEndDis_tostr.append(pd.DataFrame(dataOriginCalcEndDisDic_tostr))
#         dataOriginCalcInterDis_tostr.append(pd.DataFrame(dataOriginCalcInterDisDic_tostr))
#
#         dataOriginRealEndDisNote_tostr.append(pd.DataFrame(dataOriginRealEndDisNoteDic_tostr))
#         dataOriginRealInterDisNote_tostr.append(pd.DataFrame(dataOriginRealInterDisNoteDic_tostr))
#
#         dataOriginCalcEndDisNote_tostr.append(pd.DataFrame(dataOriginCalcEndDisNoteDic_tostr))
#         dataOriginCalcInterDisNote_tostr.append(pd.DataFrame(dataOriginCalcInterDisNoteDic_tostr))
#
#     # 写入Excel文件
#     with pd.ExcelWriter(name, mode='w') as writer:
#         for i in range(len(dataRealEndDis)):
#             # 写入节点坐标（x、y、z各占一列）
#             dataNodeCoor[i].to_excel(writer, sheet_name=sheetName[i], startrow=0, startcol=1, index=False)
#
#             # 写入时间数据
#             dataendtimedic[i].to_excel(writer, sheet_name=sheetName[i], startrow=4, index=False)
#             dataendtimedic[i].to_excel(writer, sheet_name=sheetName[i], startrow=len(endTime) + 5, index=False)
#             dataendtimedic[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 2 + 4, index=False)
#             dataendtimedic[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 3 + 4, index=False)
#
#             # 写入监测数据
#             dataRealEndDis[i].to_excel(writer, sheet_name=sheetName[i], startrow=4, startcol=1, index=False)
#             dataRealInterDis[i].to_excel(writer, sheet_name=sheetName[i], startrow=len(endTime) + 5, startcol=1, index=False)
#
#             # 写入计算数据
#             dataCalcEndDis[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 2 + 4, startcol=1, index=False)
#             dataCalcInterDis[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 3 + 4, startcol=1, index=False)
#
#             # 写入CAD坐标字符串数据
#             dataOriginRealEndDis_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=4,
#                                                    startcol=len(node2[i]) + 2, index=False)
#             dataOriginRealInterDis_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=len(endTime) + 2,
#                                                      startcol=len(node2[i]) + 5, index=False)
#
#             dataOriginCalcEndDis_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 2 + 4,
#                                                    startcol=len(node2[i]) + 2, index=False)
#             dataOriginCalcInterDis_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 3 + 4,
#                                                      startcol=len(node2[i]) + 2, index=False)
#
#             # 写入CAD坐标注释数据
#             dataOriginRealEndDisNote_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=4,
#                                                        startcol=len(node2[i]) * 2 + 2, index=False)
#             dataOriginRealInterDisNote_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=len(endTime) + 5,
#                                                          startcol=len(node2[i]) * 2 + 2, index=False)
#
#             dataOriginCalcEndDisNote_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 2 + 4,
#                                                        startcol=len(node2[i]) * 2 + 2, index=False)
#             dataOriginCalcInterDisNote_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 3 + 4,
#                                                          startcol=len(node2[i]) * 2 + 2, index=False)

def writeNodeInfor(name, sheetName, control, endTime, node, resortnode):
    # 创建一个 ExcelWriter 对象
    dataendtimedic = []

    dataRealEndDis = []
    dataRealInterDis = []

    dataCalcEndDis = []
    dataCalcInterDis = []

    dataOriginRealEndDis_tostr = []
    dataOriginRealInterDis_tostr = []

    dataOriginCalcEndDis_tostr = []
    dataOriginCalcInterDis_tostr = []

    dataOriginRealEndDisNote_tostr = []
    dataOriginRealInterDisNote_tostr = []

    dataOriginCalcEndDisNote_tostr = []
    dataOriginCalcInterDisNote_tostr = []

    # 新增：存储每个sheet的节点坐标数据
    dataNodeCoor = []

    if resortnode is not None:
        node2 = []
        for sub_list in resortnode:
            sub_node2 = []
            for sub_i in sub_list:
                for k in node:
                    found_node = next((l for l in k if l.cedianId == sub_i), None)
                    if found_node:
                        sub_node2.append(found_node)
                        break
            node2.append(sub_node2)
    else:
        node2 = node

    for i in range(len(endTime)):
        endTime[i] = datetime.datetime.fromtimestamp(endTime[i])

    for i in range(len(node2)):
        dataendtimedicson = {}
        dataRealEndDisDic = {}
        dataRealInterDisDic = {}
        dataCalcEndDisDic = {}
        dataCalcInterDisDic = {}

        dataOriginRealEndDisDic_tostr = {}
        dataOriginRealInterDisDic_tostr = {}

        dataOriginCalcEndDisDic_tostr = {}
        dataOriginCalcInterDisDic_tostr = {}

        dataOriginRealEndDisNoteDic_tostr = {}
        dataOriginRealInterDisNoteDic_tostr = {}

        dataOriginCalcEndDisNoteDic_tostr = {}
        dataOriginCalcInterDisNoteDic_tostr = {}

        # 新增：收集当前sheet的节点坐标（coor是(1,4)的numpy数组，取其值）
        node_coor_dic = {}
        for j in node2[i]:
            # 提取坐标值（shape为(1,4)，转换为列表便于存储）
            coor_values = j.coor[0:].tolist()  # 结果如：[x, y, z, ...]
            # 键格式：节点ID + "_coor"，值为坐标列表
            node_coor_dic[f"{j.cedianId}_coor"] = coor_values
            # 原有逻辑：其他数据收集
            dataRealEndDisDic[str(j.cedianId) + 'real'] = j.coorRealEndDis
            dataRealInterDisDic[str(j.cedianId) + 'real'] = j.coorRealInterDis
            dataOriginRealEndDisDic_tostr[str(j.cedianId) + 'real'] = j.originRealEndDis_tostr
            dataOriginRealInterDisDic_tostr[str(j.cedianId) + 'real'] = j.originRealInterDis_tostr

            dataOriginRealEndDisNoteDic_tostr[str(j.cedianId) + 'real'] = j.originRealEndDisNote_tostr
            dataOriginRealInterDisNoteDic_tostr[str(j.cedianId) + 'real'] = j.originRealInterDisNote_tostr
            if len(j.coorCalcEndDis) > 0:
                dataCalcEndDisDic[str(j.cedianId) + 'calc'] = j.coorCalcEndDis[:, control.direction] * control.scale3
                dataCalcInterDisDic[str(j.cedianId) + 'calc'] = j.coorCalcInterDis[:, control.direction] * control.scale3
                dataOriginCalcEndDisDic_tostr[str(j.cedianId) + 'calc'] = j.originCalcEndDis_tostr
                dataOriginCalcInterDisDic_tostr[str(j.cedianId) + 'calc'] = j.originCalcInterDis_tostr
                dataOriginCalcEndDisNoteDic_tostr[str(j.cedianId) + 'calc'] = j.originCalcEndDisNote_tostr
                dataOriginCalcInterDisNoteDic_tostr[str(j.cedianId) + 'calc'] = j.originCalcInterDisNote_tostr

        # 新增：将坐标数据转为DataFrame并存储
        dataNodeCoor.append(pd.DataFrame(node_coor_dic))

        # 原有逻辑：其他数据转为DataFrame
        dataendtimedicson[sheetName[i]] = endTime
        dataendtimedic.append(pd.DataFrame(dataendtimedicson))

        dataRealEndDis.append(pd.DataFrame(dataRealEndDisDic))
        dataRealInterDis.append(pd.DataFrame(dataRealInterDisDic))

        dataCalcEndDis.append(pd.DataFrame(dataCalcEndDisDic))
        dataCalcInterDis.append(pd.DataFrame(dataCalcInterDisDic))

        dataOriginRealEndDis_tostr.append(pd.DataFrame(dataOriginRealEndDisDic_tostr))
        dataOriginRealInterDis_tostr.append(pd.DataFrame(dataOriginRealInterDisDic_tostr))

        dataOriginCalcEndDis_tostr.append(pd.DataFrame(dataOriginCalcEndDisDic_tostr))
        dataOriginCalcInterDis_tostr.append(pd.DataFrame(dataOriginCalcInterDisDic_tostr))

        dataOriginRealEndDisNote_tostr.append(pd.DataFrame(dataOriginRealEndDisNoteDic_tostr))
        dataOriginRealInterDisNote_tostr.append(pd.DataFrame(dataOriginRealInterDisNoteDic_tostr))

        dataOriginCalcEndDisNote_tostr.append(pd.DataFrame(dataOriginCalcEndDisNoteDic_tostr))
        dataOriginCalcInterDisNote_tostr.append(pd.DataFrame(dataOriginCalcInterDisNoteDic_tostr))

    with pd.ExcelWriter(name, mode='w') as writer:
        # 将 DataFrame 写入 Excel 文件的特定位置
        for i in range(len(dataRealEndDis)):
            # 新增：先写入节点坐标到第一行（startrow=0）
            dataNodeCoor[i].to_excel(writer, sheet_name=sheetName[i], startrow=0, startcol=1, index=False)

            # 原有数据写入：所有起始行+1（避免被坐标行覆盖）
            dataendtimedic[i].to_excel(writer, sheet_name=sheetName[i], startrow=4, index=False)  # 原startrow=0
            dataendtimedic[i].to_excel(writer, sheet_name=sheetName[i], startrow=len(endTime) + 5, index=False)  # 原startrow=len(endTime)+1
            dataendtimedic[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 2 + 4, index=False)  # 原startrow=(len(endTime)+1)*2
            dataendtimedic[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 3 + 4, index=False)  # 原startrow=(len(endTime)+1)*3

            dataRealEndDis[i].to_excel(writer, sheet_name=sheetName[i], startrow=4, startcol=1, index=False)  # 原startrow=0
            dataRealInterDis[i].to_excel(writer, sheet_name=sheetName[i], startrow=len(endTime) + 5, startcol=1, index=False)  # 原startrow=len(endTime)+1

            dataCalcEndDis[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 2 + 4, startcol=1, index=False)  # 原startrow=(len(endTime)+1)*2
            dataCalcInterDis[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 3 + 4, startcol=1, index=False)  # 原startrow=(len(endTime)+1)*3

            dataOriginRealEndDis_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=4,
                                                   startcol=len(node2[i]) + 2, index=False)  # 原startrow=0
            dataOriginRealInterDis_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=len(endTime) + 5,
                                                     startcol=len(node2[i]) + 2, index=False)  # 原startrow=len(endTime)+1

            dataOriginCalcEndDis_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 2 + 4,
                                                   startcol=len(node2[i]) + 2, index=False)  # 原startrow=(len(endTime)+1)*2
            dataOriginCalcInterDis_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 3 + 4,
                                                     startcol=len(node2[i]) + 2, index=False)  # 原startrow=(len(endTime)+1)*3

            dataOriginRealEndDisNote_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=4,
                                                       startcol=len(node2[i]) * 2 + 2, index=False)  # 原startrow=0
            dataOriginRealInterDisNote_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=len(endTime) + 5,
                                                         startcol=len(node2[i]) * 2 + 2, index=False)  # 原startrow=len(endTime)+1

            dataOriginCalcEndDisNote_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 2 + 4,
                                                       startcol=len(node2[i]) * 2 + 2, index=False)  # 原startrow=(len(endTime)+1)*2
            dataOriginCalcInterDisNote_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 3 + 4,
                                                         startcol=len(node2[i]) * 2 + 2, index=False)  # 原startrow=(len(endTime)+1)*3

# def writeNodeInfor(name, sheetName, control, endTime, node, resortnode):
#     # 创建一个 ExcelWriter 对象
#     dataendtimedic = []
#
#     dataRealEndDis = []
#     dataRealInterDis = []
#
#     dataCalcEndDis = []
#     dataCalcInterDis = []
#
#     dataOriginRealEndDis_tostr = []
#     dataOriginRealInterDis_tostr = []
#
#     dataOriginCalcEndDis_tostr = []
#     dataOriginCalcInterDis_tostr = []
#
#     dataOriginRealEndDisNote_tostr = []
#     dataOriginRealInterDisNote_tostr = []
#
#     dataOriginCalcEndDisNote_tostr = []
#     dataOriginCalcInterDisNote_tostr = []
#
#     if resortnode is not None:
#         node2 = []
#         for sub_list in resortnode:
#             sub_node2 = []
#             for sub_i in sub_list:
#                 for k in node:
#                     found_node = next((l for l in k if l.cedianId == sub_i), None)
#                     if found_node:
#                         sub_node2.append(found_node)
#                         break
#             node2.append(sub_node2)
#     else:
#         node2 = node
#
#     for i in range(len(endTime)):
#         endTime[i] = datetime.datetime.fromtimestamp(endTime[i])
#
#     for i in range(len(node2)):
#         dataendtimedicson = {}
#         dataRealEndDisDic = {}
#         dataRealInterDisDic = {}
#         dataCalcEndDisDic = {}
#         dataCalcInterDisDic = {}
#
#         dataOriginRealEndDisDic_tostr = {}
#         dataOriginRealInterDisDic_tostr = {}
#
#         dataOriginCalcEndDisDic_tostr = {}
#         dataOriginCalcInterDisDic_tostr = {}
#
#         dataOriginRealEndDisNoteDic_tostr = {}
#         dataOriginRealInterDisNoteDic_tostr = {}
#
#         dataOriginCalcEndDisNoteDic_tostr = {}
#         dataOriginCalcInterDisNoteDic_tostr = {}
#
#         for j in node2[i]:
#             # dataRealEndDisDic[str(j.cedianId) + 'real'] = j.coorRealEndDis * control.scale2
#             # dataRealInterDisDic[str(j.cedianId) + 'real'] = j.coorRealInterDis * control.scale2
#             dataRealEndDisDic[str(j.cedianId) + 'real'] = j.coorRealEndDis
#             dataRealInterDisDic[str(j.cedianId) + 'real'] = j.coorRealInterDis
#             dataOriginRealEndDisDic_tostr[str(j.cedianId) + 'real'] = j.originRealEndDis_tostr
#             dataOriginRealInterDisDic_tostr[str(j.cedianId) + 'real'] = j.originRealInterDis_tostr
#
#             dataOriginRealEndDisNoteDic_tostr[str(j.cedianId) + 'real'] = j.originRealEndDisNote_tostr
#             dataOriginRealInterDisNoteDic_tostr[str(j.cedianId) + 'real'] = j.originRealInterDisNote_tostr
#             if len(j.coorCalcEndDis) > 0:
#                 dataCalcEndDisDic[str(j.cedianId) + 'calc'] = j.coorCalcEndDis[:, control.direction] * control.scale3
#                 dataCalcInterDisDic[str(j.cedianId) + 'calc'] = j.coorCalcInterDis[:, control.direction] * control.scale3
#                 dataOriginCalcEndDisDic_tostr[str(j.cedianId) + 'calc'] = j.originCalcEndDis_tostr
#                 dataOriginCalcInterDisDic_tostr[str(j.cedianId) + 'calc'] = j.originCalcInterDis_tostr
#                 dataOriginCalcEndDisNoteDic_tostr[str(j.cedianId) + 'calc'] = j.originCalcEndDisNote_tostr
#                 dataOriginCalcInterDisNoteDic_tostr[str(j.cedianId) + 'calc'] = j.originCalcInterDisNote_tostr
#
#         # print("sheetName[i]",sheetName)
#         # print("i",i)
#         dataendtimedicson[sheetName[i]] = endTime
#         dataendtimedic.append(pd.DataFrame(dataendtimedicson))
#
#         dataRealEndDis.append(pd.DataFrame(dataRealEndDisDic))
#         dataRealInterDis.append(pd.DataFrame(dataRealInterDisDic))
#
#         dataCalcEndDis.append(pd.DataFrame(dataCalcEndDisDic))
#         dataCalcInterDis.append(pd.DataFrame(dataCalcInterDisDic))
#
#         dataOriginRealEndDis_tostr.append(pd.DataFrame(dataOriginRealEndDisDic_tostr))
#         dataOriginRealInterDis_tostr.append(pd.DataFrame(dataOriginRealInterDisDic_tostr))
#
#         dataOriginCalcEndDis_tostr.append(pd.DataFrame(dataOriginCalcEndDisDic_tostr))
#         dataOriginCalcInterDis_tostr.append(pd.DataFrame(dataOriginCalcInterDisDic_tostr))
#
#         dataOriginRealEndDisNote_tostr.append(pd.DataFrame(dataOriginRealEndDisNoteDic_tostr))
#         dataOriginRealInterDisNote_tostr.append(pd.DataFrame(dataOriginRealInterDisNoteDic_tostr))
#
#         dataOriginCalcEndDisNote_tostr.append(pd.DataFrame(dataOriginCalcEndDisNoteDic_tostr))
#         dataOriginCalcInterDisNote_tostr.append(pd.DataFrame(dataOriginCalcInterDisNoteDic_tostr))
#
#     with pd.ExcelWriter(name, mode='w') as writer:
#         # 将 DataFrame 写入 Excel 文件的特定位置
#         for i in range(len(dataRealEndDis)):
#             dataendtimedic[i].to_excel(writer, sheet_name=sheetName[i], index=False)
#             dataendtimedic[i].to_excel(writer, sheet_name=sheetName[i], startrow=len(endTime) + 1, index=False)
#             dataendtimedic[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 2, index=False)
#             dataendtimedic[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 3, index=False)
#
#             dataRealEndDis[i].to_excel(writer, sheet_name=sheetName[i], startrow=0, startcol=1, index=False)
#             dataRealInterDis[i].to_excel(writer, sheet_name=sheetName[i], startrow=len(endTime) + 1, startcol=1,
#                                          index=False)
#
#             dataCalcEndDis[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 2, startcol=1,
#                                        index=False)
#             dataCalcInterDis[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 3, startcol=1,
#                                          index=False)
#
#             dataOriginRealEndDis_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=0,
#                                                    startcol=len(node2[i]) + 2, index=False)
#             dataOriginRealInterDis_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=len(endTime) + 1,
#                                                      startcol=len(node2[i]) + 2,
#                                                      index=False)
#
#             dataOriginCalcEndDis_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 2,
#                                                    startcol=len(node2[i]) + 2,
#                                                    index=False)
#             dataOriginCalcInterDis_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 3,
#                                                      startcol=len(node2[i]) + 2,
#                                                      index=False)
#
#             dataOriginRealEndDisNote_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=0,
#                                                        startcol=len(node2[i]) * 2 + 2, index=False)
#             dataOriginRealInterDisNote_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=len(endTime) + 1,
#                                                          startcol=len(node2[i]) * 2 + 2,
#                                                          index=False)
#
#             dataOriginCalcEndDisNote_tostr[i].to_excel(writer, sheet_name=sheetName[i], startrow=(len(endTime) + 1) * 2,
#                                                        startcol=len(node2[i]) * 2 + 2,
#                                                        index=False)
#             dataOriginCalcInterDisNote_tostr[i].to_excel(writer, sheet_name=sheetName[i],
#                                                          startrow=(len(endTime) + 1) * 3,
#                                                          startcol=len(node2[i]) * 2 + 2,
#                                                          index=False)


def writeNodeInforT(name):
    import pandas as pd

    # 读取 Excel 文件
    excel_file = pd.ExcelFile(name)

    # 获取 Excel 文件中的所有工作表名称
    sheet_names = excel_file.sheet_names

    # 创建一个空的 DataFrame 用于存储转置后的数据
    transposed_data = []

    # 遍历每个工作表
    for sheet_name in sheet_names:
        # 读取工作表数据，不将首行作为列名
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)

        # 转置工作表数据
        transposed_df = df.transpose()

        # 将转置后的数据添加到新 DataFrame 中
        transposed_data.append(transposed_df)

    # 将转置后的数据保存到新的 Excel 文件中
    with pd.ExcelWriter('Trans' + name, mode='w') as writer:
        for i in range(len(sheet_names)):
            transposed_data[i].to_excel(writer, sheet_name=sheet_names[i], index=False)


def writeNodeInfor2(name, name2, sheetName, control, endTime, node):
    sheets = pd.read_excel(name2, sheet_name=None)
    # 创建一个 ExcelWriter 对象
    data_real_time = []
    data_calc_time = [[] for i in range(len(node))]

    dataRealInterDis = []
    dataCalcInterDis = [[] for i in range(len(node))]

    for i in range(len(node)):
        data_real_time_dic = {}

        dataRealInterDisDic = {}

        for k in range(len(node[i][0].time)):
            if isinstance(node[i][0].time[k], float) and pd.notna(node[i][0].time[k]):
                node[i][0].time[k] = datetime.datetime.fromtimestamp(node[i][0].time[k])

        for j in node[i]:
            data_calc_time_dic = {}
            dataCalcInterDisDic = {}

            for k in range(len(j.calcTime)):
                j.calcTime[k] = datetime.datetime.fromtimestamp(j.calcTime[k])

            data_calc_time_dic[str(j.cedianId) + 'time'] = j.calcTime

            dataRealInterDisDic[str(j.label) + str(j.cedianId)] = j.coorRealDis - j.coorRealInitDis
            for k in range(len(j.coorRealDis_noclear)):
                if np.isnan(j.coorRealDis_noclear[k]):
                    dataRealInterDisDic[str(j.label) + str(j.cedianId)][k] = np.nan

            if control.working_condition == 'nan':

                dataCalcInterDisDic[str(j.label) + str(j.cedianId) + 'calc'] = (j.coorCalcDis[:, control.direction] -
                                                                                j.coorCalcInitDis[
                                                                                    control.direction]) * control.scale3
            else:
                dataCalcInterDisDic[str(j.label) + str(j.cedianId) + control.working_condition] = (j.coorCalcDis[:,
                                                                                                   control.direction] -
                                                                                                   j.coorCalcInitDis[
                                                                                                       control.direction]) * control.scale3

            data_calc_time[i].append(pd.DataFrame(data_calc_time_dic))
            dataCalcInterDis[i].append(pd.DataFrame(dataCalcInterDisDic))

        data_real_time_dic['time'] = node[i][0].time
        data_real_time.append(pd.DataFrame(data_real_time_dic))
        dataRealInterDis.append(pd.DataFrame(dataRealInterDisDic))

    with pd.ExcelWriter(name, mode='w') as writer:
        # 将 DataFrame 写入 Excel 文件的特定位置

        for i in range(len(node)):
            data_real_time[i].to_excel(writer, sheet_name=sheetName[i], startrow=0, startcol=0,
                                       index=False)
            dataRealInterDis[i].to_excel(writer, sheet_name=sheetName[i], startrow=0,
                                         startcol=1, index=False)
            for j in range(len(node[i])):
                data_calc_time[i][j].to_excel(writer, sheet_name=sheetName[i], startrow=0,
                                              startcol=len(node[i]) + 2 + j * 2, index=False)
                dataCalcInterDis[i][j].to_excel(writer, sheet_name=sheetName[i], startrow=0,
                                                startcol=len(node[i]) + 2 + j * 2 + 1, index=False)


def writeNodeInfor3(name, name2, sheetName, control, endTime, node):
    sheets = pd.read_excel(name2, sheet_name=None)
    # 创建一个 ExcelWriter 对象
    data_real_time = [[] for i in range(len(node))]
    data_calc_time = [[] for i in range(len(node))]

    dataRealInterDis = [[] for i in range(len(node))]
    dataCalcInterDis = [[] for i in range(len(node))]

    for i in range(len(node)):

        for j in node[i]:
            data_calc_time_dic = {}
            dataCalcInterDisDic = {}

            data_real_time_dic = {}
            dataRealInterDisDic = {}

            for k in range(len(j.calcTime)):
                j.calcTime[k] = datetime.datetime.fromtimestamp(j.calcTime[k])
            for k in range(len(j.time)):
                if j.time[k] is not np.nan:
                    j.time[k] = datetime.datetime.fromtimestamp(j.time[k])

            data_calc_time_dic[str(j.cedianId) + 'time'] = j.calcTime
            data_real_time_dic[str(j.cedianId) + 'time'] = j.time
            # print(j.cedianId)
            dataRealInterDisDic[str(j.label) + str(j.cedianId)] = j.coorRealDis - j.coorRealInitDis
            for k in range(len(j.coorRealDis_noclear)):
                if np.isnan(j.coorRealDis_noclear[k]):
                    dataRealInterDisDic[str(j.label) + str(j.cedianId)][k] = np.nan

            if control.working_condition == 'nan':

                dataCalcInterDisDic[str(j.label) + str(j.cedianId) + 'calc'] = (j.coorCalcDis[:,
                                                                                control.direction] -
                                                                                j.coorCalcInitDis[
                                                                                    control.direction]) * control.scale3
            else:
                dataCalcInterDisDic[str(j.label) + str(j.cedianId) + control.working_condition] = (j.coorCalcDis[:,
                                                                                                   control.direction] -
                                                                                                   j.coorCalcInitDis[
                                                                                                       control.direction]) * control.scale3

            data_calc_time[i].append(pd.DataFrame(data_calc_time_dic))
            dataCalcInterDis[i].append(pd.DataFrame(dataCalcInterDisDic))

            data_real_time[i].append(pd.DataFrame(data_real_time_dic))
            dataRealInterDis[i].append(pd.DataFrame(dataRealInterDisDic))

    with pd.ExcelWriter(name, mode='w') as writer:
        # 将 DataFrame 写入 Excel 文件的特定位置
        for i in range(len(node)):
            for j in range(len(node[i])):
                data_real_time[i][j].to_excel(writer, sheet_name=sheetName[i], startrow=0, startcol=j * 2,
                                              index=False)
                dataRealInterDis[i][j].to_excel(writer, sheet_name=sheetName[i], startrow=0,
                                                startcol=j * 2 + 1, index=False)
            for j in range(len(node[i])):
                data_calc_time[i][j].to_excel(writer, sheet_name=sheetName[i], startrow=0,
                                              startcol=len(node[i]) * 2 + 2 + j * 2, index=False)
                dataCalcInterDis[i][j].to_excel(writer, sheet_name=sheetName[i], startrow=0,
                                                startcol=len(node[i]) * 2 + 2 + j * 2 + 1, index=False)


class PostFanYanCalc():
    def test(self, filename, num, dim):
        method, control, endTime, stepPair, nodepair, calcName, resortnode = readControl(filename, num)
        sheetName, node = readCedianInfor(calcName, method, endTime, stepPair, nodepair, control)
        readnodeInfor(node, endTime, stepPair, nodepair, control, dim)
        writeNodeInfor('out' + calcName, sheetName, control, endTime, node, resortnode)
        writeNodeInforT('out' + calcName)
        if control.readNodeMethod == 1:
            writeNodeInfor2('out2' + calcName, calcName, sheetName, control, endTime, node)
        else:
            writeNodeInfor3('out2' + calcName, calcName, sheetName, control, endTime, node)

    def calc(self, filename, num, dim):
        filename = filename

        for i in range(num):
            self.test(filename, i + 1, dim)
            print("done the excel of:", i + 1)
