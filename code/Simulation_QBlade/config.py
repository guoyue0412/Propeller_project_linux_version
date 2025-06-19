import os
import numpy as np
import pandas as pd

#locate the parameters excel loaction
current_dir = os.getcwd()#QBlade_code\Airfoil_data\code\Simulation_QBlade
parametersFolder_path = os.path.join(current_dir,"simulation_parameters")#QBlade_code\Airfoil_data\code\Simulation_QBlade\simulation_parameters
parameters_path = os.path.join(parametersFolder_path,"Parameters.xlsx")#paramters excel path

#get the .dll file's path
grandparent_dir = os.path.abspath(os.path.join(current_dir,"../.."))#This is QBlade_code folder
QBlade_Software_folder = os.path.join(grandparent_dir,"QBladeCE_2.0.8.6")#This is QBladeCE_2.0.6.4 folder
QBlade_SIL_folder = os.path.join(QBlade_Software_folder,"SIL_Interface")#This is SIL_Interface folder
QBlade_dll = os.path.join(QBlade_Software_folder,"libQBladeCE_2.0.8.6.so.1.0.0")#This is libQBladeCE_2.0.8.6.so.1.0.0 file


#get the QBR file's path. This is a template file
QBlade_file_folder = os.path.join(grandparent_dir,"QBlade_data")#This is TP_data folder
QBR_file_folder = os.path.join(QBlade_file_folder,"QBR_file")#This is QBR_file folder
QBR_file = os.path.join(QBR_file_folder,"Base_file.qpr")#if some parameters are needed to change,we can change this file

#get the sim folder's path
SIM_file_folder = os.path.join(QBlade_file_folder,"QBlade_sim")#This is QBlade_sim folder
base_sim_file = os.path.join(SIM_file_folder,"Base_simulation.sim")

#the location of the template bld file
New_Blade_TurbFolder = os.path.join(SIM_file_folder,"Baseline_Blade_Turb")
Aero_folder = os.path.join(New_Blade_TurbFolder,"Aero")
bld_file_path = os.path.join(Aero_folder,"Baseline_Blade.bld")

# get the geometry of baseline 
geometry_file = os.path.join(parametersFolder_path,"APC107E_geometry.xlsx")#load the data of baseline geometry from excel

# Batch generating the sim files based on the excel
# locate the parameters excel loaction
parameters_path = os.path.join(parametersFolder_path,"Parameters.xlsx")#paramters excel path

# hyper parameters for simulaton
number_of_timesteps = 1000



# file_path
file_path = {"dll_file":QBlade_dll, "QBR_file":QBR_file, "SIM_folder":SIM_file_folder, "base_sim":base_sim_file, "base_line":geometry_file,
             "QBR_file_folder":QBlade_file_folder,"bld_file_path":bld_file_path,"simulation_parameter_path":parameters_path}

# baseline geometry_data
geometry_baseline = pd.read_excel(geometry_file,header=1)
geometry_baseline = geometry_baseline.iloc[:,:3]
geometry_baseline.iloc[:,0:2] = geometry_baseline.iloc[:,0:2] * 0.127
geometry_baseline = np.array(geometry_baseline)