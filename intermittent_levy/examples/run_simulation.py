# run_simulation.py

import numpy as np
import matplotlib.pyplot as plt
from intermittent_levy.processes import intermittent3
from intermittent_levy.moments import mom2_serg_log, mom4_serg_log
from intermittent_levy.optimization import (
    to_optimize_mom4_and_2_serg_log,
    # Include other optimization functions as needed
)
from intermittent_levy.classification import form_groups
from intermittent_levy.utils import adjusted_r_square
from scipy import optimize

# Initialize parameters
Nr_iterations = 1  # Set to 1 for testing
tau_list = np.arange(1, 20)  # Define your tau_list appropriately

# Lists to store results
int_params = []
list_X_traj = []
list_Y_traj = []
r_squared_int = []
opt_list_int_params = []
int_fit_list_mom2 = []
int_fit_list_mom4 = []
gen_dx4_log_list = []
gen_dx2_log_list = []

# Begin simulation loop
for itera in range(Nr_iterations):
    print(f"Iteration {itera + 1}/{Nr_iterations}")

    # Simulation parameters
    N = 300000
    integration_factor = 3
    g_tau = 1
    gv_list = [8, 50]
    gD_list = [0.02, 1]
    glambdaB_list = [0.02, 1]
    glambdaD_list = [0.0005, 0.02]

    # Randomly select parameters
    g_v0 = np.random.uniform(gv_list[0], gv_list[1])
    g_D = np.random.uniform(gD_list[0], gD_list[1])
    g_lambda_B = np.random.uniform(glambdaB_list[0], glambdaB_list[1])
    g_lambda_D = np.random.uniform(glambdaD_list[0], glambdaD_list[1])

    # Simulate intermittent process
    xsynth, ysynth = intermittent3(
        N * integration_factor,
        g_tau / integration_factor,
        g_v0,
        g_D,
        g_lambda_B,
        g_lambda_D
    )

    # Store parameters and trajectories
    int_params.append([g_v0, g_D, g_lambda_B, g_lambda_D])
    list_X_traj.append(xsynth)
    list_Y_traj.append(ysynth)

    # Compute moments
    dx2 = []
    dx4 = []
    for tau in tau_list:
        lldx = np.diff(xsynth[::int(tau)])
        lldy = np.diff(ysynth[::int(tau)])
        dx2.append(np.mean(lldx**2 + lldy**2))
        dx4.append(np.mean((lldx**2 + lldy**2)**2))

    dx2_log = np.log(dx2)
    dx4_log = np.log(dx4)

    # Classification
    dS = np.sqrt(np.diff(xsynth)**2 + np.diff(ysynth)**2)
    raw_threshold_array = np.linspace(np.min(dS[dS > 0]), np.max(dS), 20)
    threshold_array = raw_threshold_array / np.max(dS)
    detection, detectionfisher, lkmin, lfishermin = form_groups(
        dS, threshold_array, graph=False, x_label='v', title='title', x_axis_format='%.2f'
    )
    lthreshold = raw_threshold_array[np.argmin(detection)]
    binary_vector = (dS > lthreshold).astype(int)
    Nfix = len(binary_vector) - np.sum(binary_vector)
    Nsacc = np.sum(binary_vector)
    Ntransi = int(np.sum(np.abs(np.diff(binary_vector))) / 2)
    est_lambda_B = -np.log(1 - Ntransi / Nsacc)
    est_lambda_D = -np.log(1 - Ntransi / Nfix)
    g_v0_est = np.mean(dS[binary_vector == 1])
    g_D_est = np.mean(dS[binary_vector == 0]) / 1.8

    # Optimization setup
    rranges = [
        (g_v0_est / 10, g_v0_est * 10),
        (g_D_est / 10, g_D_est * 10),
        (est_lambda_B / 10, est_lambda_B * 10),
        (est_lambda_D / 10, est_lambda_D * 10)
    ]
    args = (tau_list, dx2_log, dx4_log)

    # Optimization
    result = optimize.dual_annealing(
        to_optimize_mom4_and_2_serg_log,
        bounds=rranges,
        args=args
    )
    best_params = result.x
    opt_list_int_params.append(best_params)

    # Compute fitted moments
    int_fit_2 = mom2_serg_log(tau_list, *best_params)
    int_fit_4 = mom4_serg_log(tau_list, *best_params)

    # Calculate adjusted R-squared
    r2_mom2 = adjusted_r_square(dx2_log, int_fit_2, degrees_freedom=4)
    r2_mom4 = adjusted_r_square(dx4_log, int_fit_4, degrees_freedom=4)
    r_squared_int.append([r2_mom4, r2_mom2])

    int_fit_list_mom2.append(int_fit_2)
    int_fit_list_mom4.append(int_fit_4)
    gen_dx4_log_list.append(dx4_log)
    gen_dx2_log_list.append(dx2_log)

    # Plot the results
    plt.figure(figsize=(10, 5))
    plt.subplot(1, 2, 1)
    plt.plot(np.log(tau_list), dx2_log, 'o', label='Empirical log M2')
    plt.plot(np.log(tau_list), int_fit_2, '-', label='Fitted log M2')
    plt.xlabel('log(tau)')
    plt.ylabel('log M2')
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(np.log(tau_list), dx4_log, 'o', label='Empirical log M4')
    plt.plot(np.log(tau_list), int_fit_4, '-', label='Fitted log M4')
    plt.xlabel('log(tau)')
    plt.ylabel('log M4')
    plt.legend()

    plt.tight_layout()
    plt.show()

# Save results if needed
# np.savetxt('int_generated_params.txt', int_params)
