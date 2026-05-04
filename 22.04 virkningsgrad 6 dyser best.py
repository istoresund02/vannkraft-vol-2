#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 22 09:14:13 2026

@author: idastoresund
"""

import numpy as np
import matplotlib.pyplot as plt

# ==============================
# GRUNNDATA
# ==============================

rho = 1000        # kg/m^3
g = 9.81          # m/s^2

P_rated = 63e6    # W (63 MW)
H_brutto = 655    # m

n_nozzles = 6
Q_max = 10.7      # m3/s

# ==============================
# FALLTAP (KALIBRERT FRA EXCEL)
# ==============================

# Excel: h_loss ≈ 5.2 m ved Q = 11 m3/s
k_loss = 5.2 / 11.0**2

def h_loss(Q):
    """Kvadratisk falltap (hydraulisk korrekt)"""
    return k_loss * Q**2

def H_netto(Q):
    return H_brutto - h_loss(Q)

# ==============================
# BEREGN MAKS VIRKINGSGRAD
# ==============================

H_dim = H_netto(Q_max)

# Virkningsgrad beregnet optimal når (Q per dyse) = Q optimal per dyse) 

eta_max = ( P_rated / (rho * g * H_dim * Q_max))

# Lagt til en mer realistisk pelton form ved virkningsgrad
def pelton_eta(Q, Q_opt, eta_max):
    x = Q / Q_opt
    if x < 0.6:
        return eta_max * (0.6 * x)       # kraftig tap
    elif x < 1.1:
        return eta_max * (1 - 0.04*(x-1)**2) # platå
    else:
        return eta_max * (0.96 - 0.15*(x-1.1))


print(f"Maks virkningsgrad η_max = {eta_max:.3f}")

# ==============================
# OPTIMAL VANNFØRING PER DYSE
# ==============================

# Beregner optimal vannføring per dyse (6 dyser) = ca. 1,78 m^3/s

Q_opt_nozzle = ( P_rated / (n_nozzles * rho * g * H_dim * eta_max))

sigma = 0.6  # bredde på delbelastningskurve

# ==============================
# TOTAL VANNFØRING
# ==============================

Q = np.linspace(0.2, Q_max, 500)
eta_total = np.zeros_like(Q)
power_MW = np.zeros_like(Q)

# ==============================
# MODELL MED DYSE-AKTIVERING
# ==============================

for i, Qtot in enumerate(Q):

    active_nozzles = min(
        int(np.ceil(Qtot / Q_opt_nozzle)),
        n_nozzles
    )

    Q_per_nozzle = Qtot / active_nozzles

    # Delbelastningsvirkningsgrad (Pelton)
    eta = eta_max * np.exp(
        - ((Q_per_nozzle - Q_opt_nozzle) / sigma)**2
    )

    eta_total[i] = eta * 100

    P_W = rho * g * H_netto(Qtot) * Qtot * eta
    power_MW[i] = P_W / 1e6

# ==============================
# PLOT
# ==============================

fig, ax1 = plt.subplots(figsize=(10, 6))

ax1.plot(Q, power_MW, label="Effekt (MW)", linewidth=2)
ax1.set_xlabel("Total vannføring Q (m³/s)")
ax1.set_ylabel("Effekt (MW)")
ax1.grid(True)

ax2 = ax1.twinx()
ax2.plot(Q, eta_total, "--", label="Virkningsgrad (%)", linewidth=2)
ax2.set_ylabel("Virkningsgrad (%)")

# Marker dysegrenser
for k in range(1, n_nozzles):
    ax1.axvline(k * Q_opt_nozzle, color="gray", linestyle="dotted")

# Legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="lower right")

plt.title("Pelton-turbin – Effekt og virkningsgrad vs vannføring")
plt.tight_layout()
plt.show()
