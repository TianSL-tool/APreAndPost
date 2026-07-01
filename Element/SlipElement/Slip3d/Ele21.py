import numpy as np
import pyvista as pv

from Element.SlipElement.Slip3d.SlipElement3d import SlipElement3D


class ElementType21(SlipElement3D):
    def __init__(self, e_id, t_id, c_id, m_id, d_id, f_id):
        super().__init__(e_id, t_id, c_id, m_id, d_id, f_id)
