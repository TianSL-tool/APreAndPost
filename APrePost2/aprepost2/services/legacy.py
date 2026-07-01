"""0.1 版适配器名称的兼容入口。

本模块不再导入原工程代码；保留旧函数名仅用于兼容早期 APrePost2 调用。
"""

from aprepost2.services.inversion import inversion_postprocess
from aprepost2.services.mesh_cutting import cut_mesh
from aprepost2.services.result_reader import read_hdf5_results

clip_mesh_legacy = cut_mesh
read_hdf5_results_legacy = read_hdf5_results
inversion_postprocess_legacy = inversion_postprocess
