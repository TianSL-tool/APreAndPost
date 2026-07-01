from Element.SlipElement.Slip2d.Ele4 import ElementType4
from Element.SlipElement.Slip3d.Ele21 import ElementType21
from Element.SlipElement.Slip3d.Ele22 import ElementType22
from Element.SlipElement.Slip3d.Ele223 import ElementType223
from Element.SlipElement.Slip3d.Ele224 import ElementType224
from Element.SlipElement.Slip3d.Ele60 import ElementType60
from Element.SolidElement.Solid2d.Ele1 import ElementType1
from Element.SolidElement.Solid2d.Ele44 import ElementType44
from Element.SolidElement.Solid2d.Ele444 import ElementType444
from Element.SolidElement.Solid3d.Ele16or510or511 import ElementType16or510or511
from Element.SolidElement.Solid3d.Ele30or190or191 import ElementType30or190or191
from Element.SolidElement.Solid3d.Ele57or59 import ElementType57or59
from Element.SolidElement.Solid3d.Ele18or170or171 import ElementType18or170or171
from Element.SolidElement.Solid3d.Ele6 import ElementType6
from Element.SolidElement.Solid3d.Ele508 import ElementType508
from Element.SlipElement.Slip3d.Ele9 import ElementType9



class ElementFactory:
    @staticmethod
    def create_element(e_id, t_id, c_id, m_id, d_id, f_id):
        # 这里可以根据 t_id 或者其他条件创建不同类型的元素

        # 三维多边形接触面
        if t_id == 60 or t_id == 601 or t_id == 602:
            return ElementType60(e_id, t_id, c_id, m_id, d_id, f_id)
        # 三维常规接触面单元及其变体
        elif t_id == 9 or t_id == 902 or t_id == 903:
            # print("e_id:",e_id)
            return ElementType9(e_id, t_id, c_id, m_id, d_id, f_id)
        elif t_id == 21:
            # print("e_id:",e_id)
            return ElementType21(e_id, t_id, c_id, m_id, d_id, f_id)
        elif t_id == 22:
            # print("e_id:",e_id)
            return ElementType22(e_id, t_id, c_id, m_id, d_id, f_id)
        elif t_id == 223:
            # print("e_id:",e_id)
            return ElementType223(e_id, t_id, c_id, m_id, d_id, f_id)
        elif t_id == 224:
            # print("e_id:",e_id)
            return ElementType224(e_id, t_id, c_id, m_id, d_id, f_id)

        # 比例边界实体单元及其变体
        elif t_id == 53 or t_id == 57 or t_id == 59 or t_id == 80 or t_id == 800:
            return ElementType57or59(e_id, t_id, c_id, m_id, d_id, f_id)
        # 三维常规实体单元及其变体
        elif t_id == 6 or t_id == 61 or t_id == 5 or t_id == 500 or t_id == 23:
            return ElementType6(e_id, t_id, c_id, m_id, d_id, f_id)
        # 二维常规实体单元及其变体
        elif t_id == 1 or t_id == 2 or t_id == 222:
            return ElementType1(e_id, t_id, c_id, m_id, d_id, f_id)
        # 二常规维接触面单元及其变体
        elif t_id == 4 or t_id == 700 or t_id == 777:
            return ElementType4(e_id, t_id, c_id, m_id, d_id, f_id)
        # 二维多边形接触面单元及其变体
        elif t_id == 44 or t_id == 47 or t_id == 470:
            return ElementType44(e_id, t_id, c_id, m_id, d_id, f_id)
        elif  t_id == 443 or t_id == 444 or t_id == 644:
            return ElementType444(e_id, t_id, c_id, m_id, d_id, f_id)
        # 可以添加更多的条件分支来创建其他类型的元素
        elif  t_id == 18 or t_id == 170 or t_id == 171:
            return ElementType18or170or171(e_id, t_id, c_id, m_id, d_id, f_id)
        elif  t_id == 16 or t_id == 510 or t_id == 511:
            return ElementType16or510or511(e_id, t_id, c_id, m_id, d_id, f_id)
        elif  t_id == 20 or t_id == 190 or t_id == 191:
            return ElementType30or190or191(e_id, t_id, c_id, m_id, d_id, f_id)
        elif t_id == 508 or t_id == 805 or t_id == 807:
            return ElementType508(e_id, t_id, c_id, m_id, d_id, f_id)
        else:
            raise ValueError(f"Unsupported element type: {t_id}")