# @Time    : 2025/03/04
# @Author  : github.com/guoyue0412



import numpy as np
import re
import os
from QBladeLibrary import QBladeLibrary
import pandas as pd
from scipy.interpolate import BSpline
import ctypes
import pickle
from tqdm import tqdm

from typing import Optional,Union,List,Dict # for | Optional


class SIMULATION:
    """
    This is simulation function class based on QBlade.one simulation or batch simulation for certain geometry Blade.
    
    Parameters
    --------------------
    str_to_byte : function
        the funct we want to transform str into byte file_path

    simulation_parameters : list(2D)
        define the running conditions (RPM,WIND_SPEED,ANGLE)

    file_path : dict
        dll,sim,qbr and so on file path
            QBladeCE_2.0.6.dll file
            QBR_file (the template file for simulation)
            QBR_file folder
            QBlade_sim folder
            QBlade_sim file (the template simulation parameters file)
            QBlade_bld file (the propeller geometry file)
            simulation_parameters_excel(generating the simulation_parameters_tuple)
    
    geometry_baseline : numpy

    geometry_current : numpy

    Attributes
    --------------------
    one_simulation_data : dataframe(pandas)
        force 、torque and so on for each time step

    all_simulation_data : dict
        key - value
            RPM****_Wind***_Angle** : one_simulation_data (all conditions)
            geometry_data : chord,twist,r of each section
    """
    def __init__(self,file_path,geometry_baseline,device_type='GPU',number_of_timesteps=1000):

        self.file_path: dict[str, str] = file_path
        self.simulation_parameters: list[list[tuple[str, str]]] = []
        self.one_simulation_data: pd.DataFrame = pd.DataFrame()
        self.all_simulation_data: Dict[str, Union[pd.DataFrame, np.ndarray]] = {}
        self.number_of_timesteps: int = number_of_timesteps
        # default : the geometry is baseline
        self.all_simulation_data['geometry'] = geometry_baseline

        # geometry
        self.geometry_baseline = geometry_baseline
        self.current_propeller = pd.DataFrame()
        # define some parameters
        self.airDensity: float = 1.225
        self.R: float = 0.127 #radius of propeller

        # Automatically call the sim file generation function
        self.generating_simulation_parameters_tuple(self.file_path["simulation_parameter_path"])# get the simulation parameters tuple
        self.generating_sim_file()
        
        # simulation device
        if (device_type == 'GPU'):
            self.device: int = 1
        if (device_type == 'CPU'):
            self.device: int = 0


    # func for invaid str file_path
    def str_to_byte(self, file_path: str) -> ctypes.Array:
        """
        Function:
            Transform the file_path into a binary (byte) buffer for QBlade DLL interface.

        Parameters:
            file_path : str
                The file path to be converted to a byte buffer.

        Returns:
            ctypes.Array
                A ctypes byte buffer that can be passed to the QBlade DLL interface.
        """
        file_path_byte: ctypes.Array = ctypes.create_string_buffer(file_path.encode("utf-8"))
        return file_path_byte



    def generating_simulation_parameters_tuple(self, simulation_paremeters_path: str) -> None:
        """
        Function:
            Generate the simulation parameter tuples of the propeller based on input Excel file.

        Parameters:
            simulation_paremeters_path : str
                Path to the Excel file that defines simulation conditions (wind speed, RPM, angle).

        Returns:
            None
        """
        parameters_simulation: pd.DataFrame = pd.read_excel(simulation_paremeters_path)
        
        WINDSPEED: np.ndarray = parameters_simulation['windSpeed'].to_numpy()
        RPM: np.ndarray = parameters_simulation['RPM'].to_numpy()
        ANGLE: np.ndarray = parameters_simulation['windAngle'].to_numpy()

        for rpm, wind_speed, flow_angle in zip(RPM, WINDSPEED, ANGLE):
            one_simulation_tuple: list[tuple[str, str]] = [
                ("OBJECTNAME", f'RPM{rpm}_Wind{wind_speed}_Angle{flow_angle}'),
                ("RPMPRESCRIBED", str(rpm)),
                ("MEANINF", str(wind_speed)),
                ("VERTANGLE", str(flow_angle))
            ]
            self.simulation_parameters.append(one_simulation_tuple)



    def generating_sim_file(self) -> None:
        """
        Function:
            Generate multiple .sim files based on simulation parameters,
            and overwrite existing simulation files (except templates) in the SIM_folder.

        Parameters:
            None

        Returns:
            None
        """
        # Delete old .sim files in the SIM folder (except for template files)
        for filename in os.listdir(self.file_path["SIM_folder"]):
            if filename in {"Base_simulation.sim", "New_Blade_Turb", "Baseline_Blade_Turb"}:
                continue
            file_path_: str = os.path.join(self.file_path["SIM_folder"], filename)
            try:
                if os.path.isfile(file_path_):
                    if not os.access(file_path_, os.W_OK):
                        os.chmod(file_path_, 0o777)
                    os.remove(file_path_)
                    print(f"delete: {file_path_}")
            except PermissionError as e:
                print(f"PermissionError can't Delete File: {file_path_}, error: {e}")
            except Exception as e:
                print(f"Error can't Delete File: {file_path_}, error: {e}")

        # Generate new .sim files based on simulation parameters
        num: int = len(self.simulation_parameters)
        for i in range(num):
            paired_tuple: list[tuple[str, str]] = self.simulation_parameters[i]
            newfile_name: str = paired_tuple[0][1]
            output_file_name: str = f"{newfile_name}.sim"
            output_file: str = os.path.join(self.file_path["SIM_folder"], output_file_name)

            try:
                with open(self.file_path['base_sim'], 'r') as file:
                    lines: list[str] = file.readlines()
                    if lines is None:
                        return

                    pattern: str = r"^\s*(\S+)\s+(\S+)\s+(-\s+.+)"
                    modified_lines: list[str] = []
                    first_width: int = 40
                    second_width: int = 18
                    third_width: int = 50

                    for line in lines:
                        match = re.match(pattern, line)
                        if match:
                            first_col, second_col, comment = match.groups()
                            modified: bool = False

                            for search_content, new_value in paired_tuple:
                                if second_col == search_content:
                                    first_col = new_value
                                    modified = True
                                    break
                            if modified:
                                if search_content == "RPMPRESCRIBED":
                                    space_num: int = 4
                                    new_line: str = f"    {first_col:<{first_width - space_num}} {second_col:<{second_width}} {comment:<{third_width}}\n"
                                else:
                                    new_line: str = f"{first_col:<{first_width}} {second_col:<{second_width}} {comment:<{third_width}}\n"
                                modified_lines.append(new_line)
                            else:
                                modified_lines.append(line)
                        else:
                            modified_lines.append(line)

                try:
                    with open(output_file, 'w') as file:
                        file.writelines(modified_lines)
                    print(f"File saved successfully to {output_file}")
                except Exception as e:
                    print(f"Error saving file: {e}")

            except FileNotFoundError:
                print(f"Error: File {repr(self.file_path['base_sim'])} not found.")
                return None

            

    def run_one_simulation(
    self,
    RPM: Optional[float] = None,
    WIND_SPEED: Optional[float] = None,
    ANGLE: Optional[float] = None,
    SIM_file_path: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Function:
            Run a simulation for a given condition (RPM, WIND_SPEED, ANGLE) or a specified .sim file.
            Result is stored in self.one_simulation_data and also appended to self.all_simulation_data.

        Parameters:
            RPM : float | None
                Rotation per minute (optional if SIM_file_path is provided).
            WIND_SPEED : float | None
                Free-stream wind speed in m/s.
            ANGLE : float | None
                Wind incidence angle in degrees.
            SIM_file_path : str | None
                Full path to .sim file to be loaded directly (optional).

        Returns:
            pd.DataFrame
                The result of the simulation (includes time, thrust, power, efficiency, etc.).
        """
        if SIM_file_path is None:
            paired_tuple: list[tuple[str, str]] = [
                ("OBJECTNAME", f'RPM{RPM}_Wind{WIND_SPEED}_Angle{ANGLE}'),
                ("RPMPRESCRIBED", str(RPM)),
                ("MEANINF", str(WIND_SPEED)),
                ("VERTANGLE", str(ANGLE))
            ]
            output_file: str = self.file_path['base_sim']
            try:
                with open(self.file_path['base_sim'], 'r') as file:
                    lines: list[str] = file.readlines()
                    if lines is None:
                        return

                    pattern: str = r"^\s*(\S+)\s+(\S+)\s+(-\s+.+)"
                    modified_lines: list[str] = []
                    first_width: int = 40
                    second_width: int = 18
                    third_width: int = 50

                    for line in lines:
                        match = re.match(pattern, line)
                        if match:
                            first_col, second_col, comment = match.groups()
                            modified: bool = False

                            for search_content, new_value in paired_tuple:
                                if second_col == search_content:
                                    first_col = new_value
                                    modified = True
                                    break

                            if modified:
                                if search_content == "RPMPRESCRIBED":
                                    space_num: int = 4
                                    new_line: str = f"    {first_col:<{first_width - space_num}} {second_col:<{second_width}} {comment:<{third_width}}\n"
                                else:
                                    new_line: str = f"{first_col:<{first_width}} {second_col:<{second_width}} {comment:<{third_width}}\n"
                                modified_lines.append(new_line)
                            else:
                                modified_lines.append(line)
                        else:
                            modified_lines.append(line)

                try:
                    with open(output_file, 'w') as file:
                        file.writelines(modified_lines)
                    # print(f"File saved successfully to {output_file}")
                except Exception as e:
                    print(f"Error saving file: {e}")
            except FileNotFoundError:
                print(f"Error: File {repr(self.file_path['base_sim'])} not found.")
                return pd.DataFrame()  # Empty result fallback

            
        # Load and run simulation using QBlade DLL(Windows)/SO(Linux)
        QBLADE = QBladeLibrary(self.file_path["dll_file"])  # type: ignore
        QBLADE.createInstance(self.device, 32)
        path: str = SIM_file_path if SIM_file_path is not None else self.file_path['base_sim']
        path_b = path.encode()
        QBLADE.loadSimDefinition(path_b)
        # QBLADE.loadProject(self.str_to_byte(self.file_path["QBR_file"]))
        QBLADE.initializeSimulation()
        

        number_of_timesteps: int = self.number_of_timesteps
        # 数据采集字段（每步从 QBlade SIL 取一次）：
        # - Thrust/Power/Torque：旋翼坐标主推力/功率/扭矩（标量）
        # - Thrust_y/_z：Hub global frame Y/Z 方向力（兼容老数据）
        # - Fx/Fy/Fz：Hub global frame 三轴力（Fy/Fz 与 Thrust_y/_z 数值相同，
        #   保留命名清晰）
        # - Mx/My/Mz：Hub global frame 三轴力矩（用于配平 + 全姿态分析）
        data_keys: list[str] = [
            "Time", "Thrust", "Power", "Torque",
            "Thrust_y", "Thrust_z",
            "Fx", "Fy", "Fz",
            "Mx", "My", "Mz",
        ]
        data_values: dict[str, list[float]] = {key: [] for key in data_keys}

        data_num: int = number_of_timesteps - 120

        # 数据有效性兜底：advanceTurbineSimulation 返回 False 表示 QBlade
        # 内部发散（典型为 "NaN values occured during wake calculations! Aborting..."），
        # 此后继续 getCustomData 会拿到 0 / NaN，污染训练集。
        # 参考 SIL sampleScript：发散立即 break，并把本工况标记为无效。
        sim_aborted_at: int = -1  # >=0 表示在该 step 发散
        for i in tqdm(range(number_of_timesteps), desc="Simulating Propeller", unit="step", ncols=100):
            success = QBLADE.advanceTurbineSimulation()
            if not success:
                sim_aborted_at = i
                print(f"\n[ABORT] 仿真在 step {i} 发散（NaN 或 inf），停止本工况并标记无效")
                break
            if i >= data_num:
                gd = QBLADE.getCustomData_at_num  # 局部别名缩短下面 12 次调用
                data_values["Time"].append(float(gd(b"Time [s]", 0, 0)))
                data_values["Thrust"].append(float(gd(b"Aerodynamic Thrust [N]", 0, 0)))
                data_values["Power"].append(float(gd(b"Aerodynamic Power [W]", 0, 0)))
                data_values["Torque"].append(float(gd(b"Aerodynamic Torque [Nm]", 0, 0)))
                # 兼容老字段：Hub global Y/Z 方向力
                data_values["Thrust_y"].append(float(gd(b"Aerodynamic Force in Hub Y_g Direction [N]", 0, 0)))
                data_values["Thrust_z"].append(float(gd(b"Aerodynamic Force in Hub Z_g Direction [N]", 0, 0)))
                # 新增：Hub global frame 三轴力
                data_values["Fx"].append(float(gd(b"Aerodynamic Force in Hub X_g Direction [N]", 0, 0)))
                data_values["Fy"].append(float(gd(b"Aerodynamic Force in Hub Y_g Direction [N]", 0, 0)))
                data_values["Fz"].append(float(gd(b"Aerodynamic Force in Hub Z_g Direction [N]", 0, 0)))
                # 新增：Hub global frame 三轴力矩
                data_values["Mx"].append(float(gd(b"Aerodynamic Moment in Hub X_g Direction [Nm]", 0, 0)))
                data_values["My"].append(float(gd(b"Aerodynamic Moment in Hub Y_g Direction [Nm]", 0, 0)))
                data_values["Mz"].append(float(gd(b"Aerodynamic Moment in Hub Z_g Direction [Nm]", 0, 0)))

        # 仿真发散时：直接抛弃本工况，不写入 all_simulation_data，
        # 避免半截无效数据混入训练集。上层 run_all_simulation 据此跳过即可。
        if sim_aborted_at >= 0 or len(data_values["Time"]) == 0:
            QBLADE.closeInstance()
            del QBLADE
            label_for_log = os.path.splitext(os.path.basename(path))[0]
            print(f"[SKIP] 工况 {label_for_log} 因发散未保存（abort step={sim_aborted_at}, 收集步数={len(data_values['Time'])}）")
            self.one_simulation_data = pd.DataFrame()
            return self.one_simulation_data

        # Convert results to DataFrame
        df: pd.DataFrame = pd.DataFrame(data_values)

        # Extract RPM/WIND/ANGLE info
        if SIM_file_path is not None:
            pattern = r"RPM(\d+)_Wind(\d+)_Angle(\d+)"
            match = re.search(pattern, SIM_file_path)
            if match:
                df["RPM"] = float(match.group(1))
                df["WIND_SPEED"] = float(match.group(2))
                df["ANGLE"] = float(match.group(3))
            else:
                print("No match found.")
        else:
            df["RPM"] = float(RPM)
            df["WIND_SPEED"] = float(WIND_SPEED)
            df["ANGLE"] = float(ANGLE)

        # Post-process simulation data
        # × -1 是为了把 QBlade 输出的拉力定义（向下为正）翻成无人机推力（向上为正）
        df["THRUST"] = df["Thrust"].mean() * -1
        df["POWER"] = df["Power"].mean() * -1
        df["TORQUE"] = df["Torque"].mean() * -1
        df["THRUST_Y"] = df["Thrust_y"].mean() * -1
        df["THRUST_Z"] = df["Thrust_z"].mean() * -1
        # 新增聚合：三轴力 + 三轴力矩（Hub global frame）
        df["FX"] = df["Fx"].mean() * -1
        df["FY"] = df["Fy"].mean() * -1
        df["FZ"] = df["Fz"].mean() * -1
        df["MX"] = df["Mx"].mean() * -1
        df["MY"] = df["My"].mean() * -1
        df["MZ"] = df["Mz"].mean() * -1

        df["Ct"] = df["THRUST"] / (self.airDensity * ((df["RPM"] / 60) ** 2) * ((2 * self.R) ** 4))
        # df["Cp"] = df["POWER"] * 1000 / (self.airDensity * ((df["RPM"] / 60) ** 3) * ((2 * self.R) ** 5))
        df["Cp"] = df["POWER"] / (self.airDensity * ((df["RPM"] / 60) ** 3) * ((2 * self.R) ** 5))

        if df["WIND_SPEED"].iloc[0] != 0:
            df["eta"] = (df["WIND_SPEED"] / (df["RPM"] * 2 * self.R)) * (df["Ct"] / df["Cp"])
        else:
            df["eta"] = 0

        # 兜底校验：聚合后量级仍异常（NaN/inf/接近 0 推力）→ 拒收
        if not np.isfinite(df["THRUST"].iloc[0]) or abs(df["THRUST"].iloc[0]) < 1e-6:
            QBLADE.closeInstance(); del QBLADE
            print(f"[SKIP] 工况 {os.path.splitext(os.path.basename(path))[0]} THRUST 异常（{df['THRUST'].iloc[0]:.3e}），不保存")
            self.one_simulation_data = pd.DataFrame()
            return self.one_simulation_data

        self.one_simulation_data = df
        filename = os.path.splitext(path)[0]
        label = os.path.splitext(os.path.basename(filename))[0]
        self.all_simulation_data[label] = df

        # Store QBlade project
        goal_qbr_file_name: str = os.path.splitext(path)[0] + ".qpr"
        goal_qbr_file_path: str = os.path.join(self.file_path["QBR_file_folder"], goal_qbr_file_name)
        QBLADE.storeProject(self.str_to_byte(goal_qbr_file_path))

        # Unloading the qblade library
        QBLADE.closeInstance()
        print(f'RPM{RPM}_Wind{WIND_SPEED}_Angle{ANGLE}')
        del QBLADE

        return self.one_simulation_data # one_simulation data detailed for README.md


    def run_all_simulation(self) -> None:
        """
        Function:
            Batch run all `.sim` files (excluding the base template) in the SIM_folder.
            Results are appended to self.all_simulation_data.

        Parameters:
            None

        Returns:
            None
        """
        all_sim_files: List[str] = []

        for root, dirs, files in os.walk(self.file_path["SIM_folder"]):
            for file in files:
                if file.endswith(".sim") and file != "Base_simulation.sim":
                    sim_path: str = os.path.join(root, file)
                    all_sim_files.append(sim_path)

        for sim_file_path in all_sim_files:
            print(os.path.splitext(sim_file_path)[0])
            self.run_one_simulation(SIM_file_path=sim_file_path)


    def change_propeller_geometry(
    self,
    section_data: Optional[np.ndarray] = None,
    control_point: Optional[np.ndarray] = None
    ) -> None:
        """
        Function:
            Change the geometry of the propeller.
            If no parameters are passed, the geometry defaults to the baseline propeller.

        Parameters:
            section_data : Optional[np.ndarray]
                Chord and twist data (n_sections x 3), default is None.

            control_point : Optional[np.ndarray]
                8-element control vector. First 4 are twist, last 4 are chord.
        """
        # Use baseline geometry if nothing is provided
        if section_data is None and control_point is None:
            self.current_propeller = self.geometry_baseline
        elif section_data is not None:
            self.current_propeller = section_data

        # Reconstruct geometry from control points using B-spline interpolation
        if control_point is not None:
            chord_points: np.ndarray = control_point[0:4]
            twist_points: np.ndarray = control_point[4:]

            degree: int = 3
            knots: np.ndarray = np.concatenate(([0] * degree, [0.3984874, 0.89904882], [1] * degree))
            twist_knots: np.ndarray = np.concatenate(([0] * degree, [0.2, 0.89904882], [1] * degree))

            chord_bspline = BSpline(knots, chord_points, degree)
            twist_bspline = BSpline(twist_knots, twist_points, degree)

            x_norm = self.geometry_baseline[:, 0] / 0.127
            chord_spline: np.ndarray = chord_bspline(x_norm)
            twist_spline: np.ndarray = twist_bspline(x_norm)

            self.current_propeller = np.vstack((
                self.geometry_baseline[:, 0],  # r for 22 sections
                chord_spline, # chord for 22 sections
                twist_spline # twsit for 22 sections
            )).T

        # Modify .bld file
        try:
            with open(self.file_path["bld_file_path"], 'r') as file:
                lines: list[str] = file.readlines()

            pos_width, chord_width, twist_width, remaining_width = 19, 19, 19, 200
            pattern_pos = r"^([+-]?\d*\.\d*(?:[eE][+-]?\d+)?)\s+([+-]?\d*\.\d*(?:[eE][+-]?\d+)?)\s+([+-]?\d*\.\d*(?:[eE][+-]?\d+)?)\s+(.*)$"
            modified_lines: list[str] = []

            for line in lines:
                match_pos = re.match(pattern_pos, line)
                if match_pos:
                    pos_col, chord_col, twist_col, remaining = match_pos.groups()
                    modified = False
                    for row in self.current_propeller:
                        pos, chord, twist = row
                        if abs(float(pos_col) - pos) <= 1e-4:
                            chord_col = abs(chord)
                            twist_col = abs(twist)
                            modified = True
                            break
                    if modified:
                        new_line = f"{float(pos_col):<{pos_width}.5f} {float(chord_col):<{chord_width}.5f} {float(twist_col):<{twist_width}.5f} {remaining:<{remaining_width}}\n"
                        # print(new_line)
                        modified_lines.append(new_line)
                    else:
                        modified_lines.append(line)
                else:
                    modified_lines.append(line)
        except FileNotFoundError:
            print(f"Error: File {repr(self.file_path['bld_file_path'])} not found.")
            return

        # Save modified .bld file
        try:
            with open(self.file_path["bld_file_path"], 'w') as file:
                file.writelines(modified_lines)
            # print(f"File saved successfully to {repr(self.file_path['bld_file_path'])}")
        except Exception as e:
            print(f"Error saving file: {e}")

        # Save simulation results as dict in pickle file
        geometry_file: str = "geometry_simulation_dict.pkl"
        if os.path.exists(geometry_file):
            with open(geometry_file, 'rb') as file:
                try:
                    geometry_simulation_dict: dict = pickle.load(file)
                except EOFError:
                    geometry_simulation_dict = {}
        else:
            geometry_simulation_dict = {}

        if geometry_simulation_dict:
            last_key = next(reversed(geometry_simulation_dict))
            geometry_num = int(last_key.split("_")[-1]) + 1
        else:
            geometry_num = 0

        geometry_simulation_dict[f'geometry_{geometry_num}'] = self.all_simulation_data

        with open(geometry_file, 'wb') as file:
            pickle.dump(geometry_simulation_dict, file)

        print(f"File saved successfully to {geometry_file}")
        
        # save the current propeller simulation data as a dictionary file(pkl)
        with open(f"propeller_simulation_data_for_one.pkl", 'wb') as file:
            pickle.dump(self.all_simulation_data, file)
            
        # clear the simulation data for certain propeller geometry
        self.all_simulation_data.clear()
        # default : the geometry is baseline
        self.all_simulation_data['geometry'] = self.current_propeller

