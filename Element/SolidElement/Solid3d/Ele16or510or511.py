import numpy as np
import pyvista as pv

from Element.SolidElement.Solid3d.SolidElement3d import SolidElement3D


class ElementType16or510or511(SolidElement3D):
    def __init__(self, e_id, t_id, c_id, m_id, d_id, f_id):
        super().__init__(e_id, t_id, c_id, m_id, d_id, f_id)

