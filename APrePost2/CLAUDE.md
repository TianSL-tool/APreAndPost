# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 命令 / Commands

```powershell
# 使用正确的虚拟环境（.venv 指向不存在的 Python 3.12，用 venvnew）
. ..\venvnew\Scripts\Activate.ps1

# 安装（开发模式）
python -m pip install -e .

# 运行
python run.py

# 测试
python -m unittest discover -s tests -v
```

## 架构 / Architecture

两套代码并存，**APrePost2 是独立重写版**，不导入旧工程：

- **旧工程**（根目录）：`APyPreAndPost.py` → `mainwindow/` + `pre_group/` + `post/` + `Node/` + `Element/`
- **APrePost2**（`APrePost2/`）：`run.py` → `aprepost2/` 包，分层架构

### APrePost2 分层

```
ui/          ← QMainWindow + QTreeWidget 任务目录，TaskDialog 动态表单
services/    ← 14 个纯函数服务，返回 OperationResult，不依赖 Qt
domain/      ← Node / BaseElement 子类 / Mesh 数据类
io/          ← 流式网格读写、编码检测、原子替换写出
```

**控制反转**：`ui/task_catalog.py` 中的 `TaskSpec` 声明式定义每个任务的参数表单和 handler，UI 层不知道具体业务逻辑。

### 添加新功能的步骤

1. 在 `services/` 中实现纯函数，接收文件路径 + 参数，返回 `OperationResult`
2. 在 `ui/task_catalog.py` 的 `TASKS` 元组中添加一个 `TaskSpec`（key / category / title / fields / handler）
3. 如需新的输入控件类型，在 `ui/task_dialog.py` 中扩展

### 关键约束

- **原子写入**：所有修改网格的服务必须先写临时文件，成功后再 `os.replace` 到目标路径
- **禁止输入输出同路径**：通过 `services/common.py` 的 `checked_paths()` 统一校验
- **网格格式**：文本文件，分 `node ... end node` 和 `element ... end element` 两段
- **控制文件兼容**：与旧工程保持相同的控制文件格式约定（见 README.md）
