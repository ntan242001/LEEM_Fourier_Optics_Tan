from sympy.solvers import solve
from sympy import Symbol
import numpy as np
import matplotlib.pyplot as plt
from joblib import Parallel, delayed

# A function to choose different LEEM parameters
def choose_LEEM_type(LEEM_type_str):
    global E, E_0, C_c, C_cc, C_3c, C_3, C_5, alpha_ap, alpha_ill, \
        delta_E, M_L, lamda, lamda_0, q_ill, q_ap, LEEM_type, E_0_series
    LEEM_type = LEEM_type_str   
    
    if LEEM_type != "Energy dependent":
        if LEEM_type == "IBM AC":
            E = 15010  # eV  Nominal Energy After Acceleration
            E_0 = 10  # eV  Starting Energy
            C_c = 0  # m   Second Rank Chromatic Aberration Coefficient
            C_cc = 27.9 # m   Third Rank Chromatic Aberration Coefficient
            C_3c = -67.4 # m   Forth Rank Chromatic Aberration Coefficient
            C_3 = 0  # m   Spherical Aberration Coefficient
            C_5 = 92.8
        
            alpha_ap = 7.37e-3  # rad Aperture angle
            alpha_ill = 0.1e-3  # rad Illumination Divergence Angle
        
            delta_E = 0.25  # eV  Energy Spread
            M_L = 0.653  # Lateral Magnification
            print("IBM AC chosen.")
    
        elif LEEM_type =="IBM NAC":
            E = 15010  # eV  Nominal Energy After Acceleration
            E_0 = 10  # eV  Starting Energy
            C_c = -0.075  # m  Second Rank Chromatic Aberration Coefficient
            C_cc = 23.09 # m   Third Rank Chromatic Aberration Coefficient
            C_3c = -59.37  # m   Forth Rank Chromatic Aberration Coefficient
            C_3 = 0.345  # m  Third Order Spherical Aberration Coefficient
            C_5 = 39.4  # m  Fifth Order Spherical Aberration Coefficient
            
            alpha_ap = 2.34e-3  # rad Aperture angle
            alpha_ill = 0.1e-3  # rad Illumination Divergence Angle
            
            delta_E = 0.25  # eV  Energy Spread
            M_L = 0.653  # Lateral Magnification
            print("IBM NAC chosen.")
        
        lamda = 6.6261e-34 / np.sqrt(2 * 1.6022e-19 * 9.1095e-31 * E)
        lamda_0 = 6.6261e-34 / np.sqrt(2 * 1.6022e-19 * 9.1095e-31 * E_0)
    
        q_ap = alpha_ap / lamda
        q_ill = alpha_ill / lamda
        
    elif LEEM_type == "Energy dependent":
        E = 15010  # eV  Nominal Energy After Acceleration
        E_0_series = np.linspace(10, 100, 91)
        alpha_ill = 0.1e-3  # rad Illumination divergence angle
        
        delta_E = 0.25  # eV  Energy Spread
        M_L = 0.653  # Lateral Magnification
        
        lamda = 6.6261e-34 / np.sqrt(2 * 1.6022e-19 * 9.1095e-31 * E) #in metre
        q_ill = alpha_ill / lamda
        print("Energy dependent simulation chosen.")

choose_LEEM_type("IBM AC")

# A function to set different defocus values
def choose_defocus(defocus_type):
    global delta_z
    if defocus_type == "In-focus":
        delta_z = 0
        print("In-focus chosen.")
    elif defocus_type == "Scherzer defocus":
        delta_z = np.sqrt(3/2*C_3*lamda)
        print("Scherzer defocus chosen.")
    elif defocus_type == "A Phi Scherzer defocus":
        delta_z = np.sqrt(9/64*C_5*lamda**2)
        print("A Phi Scherzer defocus chosen.")

choose_defocus("In-focus")

print("Simulation start.")

# Creating a 1:1/sqrt(2) amplitude object whose phase is uniformly set to 0
object_size = 400               # simulating object size in nm
simulating_steps = 1 + 2**13  # total simulating steps
# An array of points in the x space
x_array = (np.linspace(-object_size/2, object_size/2, simulating_steps) + object_size/simulating_steps)*1e-9

object_phase = np.zeros_like(x_array)

object_amplitude = np.ones_like(x_array)

for counter, element in enumerate(x_array):
    if element > 0:
        object_amplitude[counter] = 1/np.sqrt(2)

# Object function
object_function = np.multiply(object_amplitude, np.exp(1j * object_phase))
# The object image is reversed through the lens
object_function = object_function[::-1]    

# Initialising the series of function I(x) at different values of E_0
matrixI = np.zeros_like(x_array, dtype=complex)

'''
def FO1D(E_0, E_0_index):
    kappa = np.sqrt(E/E_0)
    # Third Order Spherical Aberration Coefficient in metre
    C_3 = 0.0327 * np.sqrt(kappa) + 0.1681  
    # Fifth Order Spherical Aberration Coefficient in metre
    C_5 = 0
    # Second Rank Chromatic Aberration Coefficient in metre
    C_c = -0.0154 * np.sqrt(kappa) + 0.0173
    # Third Rank Chromatic Aberration Coefficient in metre
    C_3c = 0
    # Fourth Rank Chromatic Aberration Coefficient in metre
    C_cc = 0
# Finding the value of q_ap that gives the best resolution 
q_ap = Symbol('q_ap', real = True)
q_ap = solve(1/6*C_5* lamda**5 * q_ap**6 + 1/4*C_3*lamda**3 * q_ap**2+ - 1/2*delta_z*lamda*q_ap**2 - 1/4, q_ap)
for sol in q_ap:
    if sol <= 0:
        q_ap.remove(sol)        
q_ap = min(q_ap)
'''    

# The Fourier Transform of the Object Wave Function
F_object_function = np.fft.fft(object_function, simulating_steps) * (1 / simulating_steps)
# Shifting this to the centre at 0
F_object_function = np.fft.fftshift(F_object_function)
# An array of points in the q space, in SI unit
q = 1 / (simulating_steps* (x_array[1] - x_array[0])) * np.arange(0, simulating_steps, 1)
# Shifting the q array to centre at 0 
q = q - np.max(q) / 2


# Taking into account the effect of the contrast aperture    
a = np.sum(np.abs(q) <= q_ap)
if len(q) > a:
    min_index = int(np.ceil(simulating_steps / 2 + 1 - (a - 1) / 2))
    max_index = int(np.floor(simulating_steps / 2 + 1 + (a + 1) / 2))
    q = q[min_index:max_index]
    F_object_function = F_object_function[min_index:max_index]
    
# Arrays for the calculation of the double integration 
Q, QQ = np.meshgrid(q, q)
F_obj_q, F_obj_qq = np.meshgrid(F_object_function, np.conj(F_object_function))

# The modifying function of zeroth-order
R_0 = np.exp(1j*2*np.pi*(C_3*lamda**3 * (Q**4 - QQ**4)/4 + C_5*lamda**5 *(
    Q**6 - QQ**6)/6 - delta_z*lamda*(Q**2 - QQ**2)/2))

# The envelop function by source extension
E_s = np.exp(-np.pi**2/(4*np.log(2)) * q_ill**2 * (C_3*lamda**3 *(
    Q**3 - QQ**3) + C_5*lamda**5 * (Q**5 - QQ**5) - delta_z*lamda*(Q - QQ))**2)

# The envelop function by energy spread
E_cc = (1 - 1j * np.pi/(4*np.log(2)) * C_cc*(delta_E/E)**2 * lamda * (Q**2 - QQ**2))**(-1/2)
E_ct = E_cc * np.exp(-E_cc**2 * np.pi**2/(16*np.log(2)) * (delta_E/E)**2 * (C_c * lamda * (Q**2 - QQ**2) + 1/2*C_3c*lamda**3 * (Q**4 - QQ**4))**2)

AR = np.multiply(np.multiply(np.multiply(np.multiply(F_obj_q, F_obj_qq), R_0), E_s), E_ct)
for i in range(len(q)):
    for j in range(i + 1, len(q)):
        matrixI[:] = matrixI[:] + 2 * (
                AR[j][i] * np.exp(1j * 2 * np.pi * (Q[j][i] - QQ[j][i]) * x_array)).real
    

matrixI[:] = matrixI[:] + np.trace(AR) * np.ones_like(x_array)


matrixI = np.abs(matrixI)

print('Simulation finished.')

'''
# Calculating resolution
I_max = max(matrixI)
I_min = min(matrixI)

I_84 = I_min + (I_max - I_min)*84/100
I_16 = I_min + (I_max - I_min)*16/100

I_84_index = matrixI.where(np.abs(matrixI - I_84) == min(np.abs(matrixI - I_84)))
x_84 = x_array(I_84_index)

I_16_index = matrixI.where(np.abs(matrixI - I_16) == min(np.abs(matrixI - I_16)))
x_16 = x_array(I_16_index)

resolution = x_84 - x_16

print(resolution)
'''


# plotting the points 
plt.plot(x_array, matrixI)

#plt.xlim(-10e-9, 10e-9)


#plt.axvline(x= x_84)
#plt.axvline(x= x_16)

# naming the x axis
plt.xlabel('Position x (m)')
# naming the y axis
plt.ylabel('Instensity')
  
# giving a title to my graph
plt.title('I(x)')

plt.show()












