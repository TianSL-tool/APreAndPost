import numpy as np

from Element.BaseElement import Element

class SlipElement2D(Element):
    def __init__(self, e_id, t_id, c_id, m_id, d_id, f_id):
        super().__init__(e_id, t_id, c_id, m_id, d_id, f_id)

    def write_to_file(self, file):
        point_str = [str(point.node_id) for point in self.points]
        formatted_info = [
            f"{self.e_id:10d}",
            f"{self.t_id:10d}",
            f"{self.c_id:10d}",
            f"{self.m_id:10d}",
            f"{self.d_id:10d}",
            f"{self.f_id:10d}"
        ] + [f"{int(p):10d}" for p in point_str]
        file.write(' '.join(formatted_info) + '\n')

    def get_write_string(self):
        point_str = [str(point.node_id) for point in self.points]
        formatted_info = [
            f"{self.e_id:10d}",
            f"{self.t_id:10d}",
            f"{self.c_id:10d}",
            f"{self.m_id:10d}",
            f"{self.d_id:10d}",
            f"{self.f_id:10d}"
        ] + [f"{int(p):10d}" for p in point_str]
        return ' '.join(formatted_info)

    def write_ele_Schedule(self):
        elem_output_file = f"{self.e_id}.ele"
        with open(elem_output_file, 'w') as elem_file:
            if self.stresses or self.strains:
                elem_file.write("Stresses and Strains:\n")
                step_iter = self.steps if self.stresses else self.steps if self.strains else []
                for step in step_iter:
                    stress = self.stresses[self.steps.index(step)] if self.stresses else [""] * 6
                    strain = self.strains[self.steps.index(step)] if self.strains else [""] * 6
                    elem_file.write(f"{str(step)}\t")
                    elem_file.write(f"{' '.join(map(str, stress))}\t")
                    elem_file.write(f"{' '.join(map(str, strain))}\t")


    def get_maxandmin_stressandstrain(self):
        stresses = -np.array(self.stresses).reshape(-1, 2, 1)
        s11 = stresses[:, 0, 0]
        s22 = stresses[:, 1, 0]

        stress_vars = [s11, s22]
        for var in stress_vars:
            min_val = np.min(var)
            max_val = np.max(var)
            self.min_stress.append(min_val)
            self.max_stress.append(max_val)

        strain = -np.array(self.strains).reshape(-1, 2, 1)
        st11 = strain[:, 0, 0]
        st22 = strain[:, 1, 0]

        strain_vars = [st11, st22]
        for var in strain_vars:
            min_val = np.min(var)
            max_val = np.max(var)
            self.min_strain.append(min_val)
            self.max_strain.append(max_val)
    def calculate_stress_strain_variables(self, podu=0, initial_stress=1, initial_strain=1):
        self.get_maxandmin_stressandstrain()

    def write_ele_Schedule(self,podu=0.0):
        elem_output_file = f"{self.e_id}.ele"
        with open(elem_output_file, 'w') as elem_file:
            if self.stresses or self.strains:
                elem_file.write("step\tShearStresse\tNormalStresse2\tShearDisp\tNormalDisp\n")
                step_iter = self.steps if self.stresses else self.steps if self.strains else []
                for step in step_iter:
                    stress = self.stresses[self.steps.index(step)] if self.stresses else [""] * 2
                    strain = self.strains[self.steps.index(step)] if self.strains else [""] * 2
                    elem_file.write(f"{str(step)}\t")
                    elem_file.write(f"{' '.join(map(str, stress))}\t")
                    elem_file.write(f"{' '.join(map(str, strain))}\n")



    def write_step(self,step,element_file):
        if step in self.steps:
            index = self.steps.index(step)
            element_file.write(f"Element {self.e_id}:\t")
            element_file.write(f"center\t")
            element_file.write(f"{' '.join(map(str, self.center))}\t")
            element_file.write(f"Stress\t")
            element_file.write(f"{' '.join(map(str, self.stresses[index]))}\t")
            element_file.write(f"Strain\t")
            element_file.write(f"{' '.join(map(str, self.strains[index]))}\n")


    def write_max_step(self,element_file):
        element_file.write(f"Element {self.e_id}:\t")
        element_file.write(f"center_coor\t")
        element_file.write(f"{' '.join(map(str, self.center))}\t")
        element_file.write(f"maxStress\t")
        element_file.write(f"{' '.join(map(str, self.max_stress))}\t")
        element_file.write(f"minStress\t")
        element_file.write(f"{' '.join(map(str, self.min_stress))}\t")
        element_file.write(f"maxStrain\t")
        element_file.write(f"{' '.join(map(str, self.max_strain))}\t")
        element_file.write(f"minStrain\t")
        element_file.write(f"{' '.join(map(str, self.min_strain))}\n")


