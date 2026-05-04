#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 16:21:30 2026

@author: idastoresund
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Case 3 – Prisoptimalisert drift
Sammenlikning med og uten ekstra 30 MW turbin
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ============================================================
# 1) LAST DATA
# ============================================================

df = pd.read_excel("Sildvik_Produksjon_Pris_2024-2.xlsx", engine="openpyxl")
df["Datetime"] = pd.to_datetime(df["Datetime"])

prices = df["Price_ore_kWh"].to_numpy()
times = df["Datetime"].to_numpy()
nT = len(df)

print("Antall timer:", nT)
print(df.head())

# ============================================================
# 2) MAGASIN OG TILSIG
# ============================================================

Vmax = 94.5e6
Vmin = 0.5e6
V0 = 0.80 * Vmax

# NVE 
annual_inflow_m3 = 158.998  # m³/år fra NVE REGINE

fordeling = np.array([0.3,0.3,0.4,1.5,2.5,1.4,
                      0.7,0.7,1.0,1.4,1.2,0.6])

dager = np.array([31,29,31,30,31,30,31,31,30,31,30,31])
timer = dager * 24

# Fordel årsvolumet på måneder
maanedsvolum = annual_inflow_m3 * fordeling / fordeling.sum()

# m³/time per måned
tilsig_per_h = maanedsvolum / timer

# Timeserie med tilsig
inflow_hourly = np.repeat(tilsig_per_h, timer)[:nT]

# ============================================================
# 3) FYSISKE PARAMETERE
# ============================================================

rho = 1000
g = 9.81
H_brutto = 655

Q_main_max = 10.7
P_extra_max = 30.0

Q_loss_points = np.array([11.0, 16.5, 22.0])
h_loss_points = np.array([5.2, 10.5, 14.3])
k_loss = 5.2 / 11.0**2

def h_loss(Q):
    if Q < 11:
        return k_loss * Q**2
    return np.interp(Q, Q_loss_points, h_loss_points)

def H_netto(Q):
    return H_brutto - h_loss(Q)

# ============================================================
# 4) VIRKNINGSGRAD
# ============================================================

def eta_main(Q):
    if Q <= 0:
        return 0.0
    q_rel = Q / Q_main_max
    if q_rel < 0.25:
        return 0.0
    elif q_rel < 0.50:
        return 0.65 + (q_rel - 0.30) * (0.88 - 0.65) / 0.20
    elif q_rel < 0.90:
        return 0.85 + 0.07 * (1 - ((q_rel - 0.70)/0.20)**2)
    else:
        return 0.88

def eta_extra(P):
    return 0.92 if P > 0 else 0.0

# ============================================================
# 5) EFFEKT
# ============================================================

def power_MW(Q_main, P_extra):
    Hn = H_netto(Q_main)
    P_main = rho * g * Q_main * Hn * eta_main(Q_main) / 1e6
    P_extra = min(P_extra, P_extra_max)
    return P_main + P_extra, P_main, P_extra, Hn

# ============================================================
# VANNVERDI
# ============================================================

def water_value(V, Vmax, Vmin):
    fill = (V - Vmin) / (Vmax - Vmin)
    fill = max(0.0, min(1.0, fill))
    return 0.1 + 2.0 * (1 - fill)**2

# ============================================================
# 6) OPTIMALISERING
# ============================================================

Q_candidates = np.linspace(0, Q_main_max, 200)

Q_out = np.zeros(nT)
P_out = np.zeros(nT)
P_main_out = np.zeros(nT)
P_extra_out = np.zeros(nT)
Hn_out = np.zeros(nT)
revenue_out = np.zeros(nT)
V = np.zeros(nT)
V[0] = V0

max_delta_Q = 1.0
Q_min = 5.0
P_min = 45.0
startup_cost = 1_000_000
ramp_penalty = 60_000

for t in range(nT):

    if t > 0:
        V[t] = min(V[t-1] + inflow_hourly[t], Vmax)

    prev_Q = Q_out[t-1] if t > 0 else 0.0

    best_value = -1e12

    for Q in Q_candidates:
        for P_extra in [0.0, P_extra_max]:

            if Q > 0 and Q < Q_min:
                continue
            if V[t] - Q*3600 < Vmin:
                continue
            if prev_Q > 0 and abs(Q-prev_Q) > max_delta_Q:
                continue

            P_total, P_main, P_extra_used, Hn = power_MW(Q, P_extra)

            if Q > 0 and P_total < P_min:
                continue

            income = prices[t] * 1000 * P_total
            water_cost = water_value(V[t], Vmax, Vmin) * Q * 3600
            value = income - water_cost

            value -= ramp_penalty * abs(Q - prev_Q)
            if prev_Q == 0 and Q > 0:
                value -= startup_cost

            if value > best_value:
                best_value = value
                best_Q = Q
                best_P = P_total
                best_P_main = P_main
                best_P_extra = P_extra_used
                best_Hn = Hn



    Q_out[t] = best_Q
    P_out[t] = best_P
    P_main_out[t] = best_P_main
    P_extra_out[t] = best_P_extra
    Hn_out[t] = best_Hn
    revenue_out[t] = best_value

    V[t] -= best_Q * 3600
    V[t] = max(V[t], Vmin)

# ============================================================
# 7) RESULTATTABELL
# ============================================================

results = pd.DataFrame({
    "Datetime": times,
    "P_MW": P_out,
    "P_main_MW": P_main_out,
    "P_extra_MW": P_extra_out,
    "Q_m3s": Q_out,
    "Magasin_m3": V
})

# ============================================================
# 8) NØKKELTALL – MED / UTEN EKSTRA TURBIN
# ============================================================

energy_no = results["P_main_MW"].sum()
income_no = (results["P_main_MW"] * prices * 1000 / 100).sum()
drift_no = (results["P_main_MW"] > 0).sum()
starts_no = ((results["P_main_MW"] > 0) &
             (results["P_main_MW"].shift(1, fill_value=0) == 0)).sum()
avg_no = results.loc[results["P_main_MW"] > 0, "P_main_MW"].mean()

energy_yes = results["P_MW"].sum()
income_yes = (results["P_MW"] * prices * 1000 / 100).sum()
drift_yes = (results["P_MW"] > 0).sum()
starts_yes = ((results["P_MW"] > 0) &
              (results["P_MW"].shift(1, fill_value=0) == 0)).sum()
avg_yes = results.loc[results["P_MW"] > 0, "P_MW"].mean()

print("\n=== CASE 3 – UTEN EKSTRA TURBIN ===")
print(f"Total energi: {energy_no:,.1f} MWh")
print(f"Total inntekt: {income_no:,.0f} kr")
print(f"Driftstimer: {drift_no}")
print(f"Oppstarter: {starts_no}")
print(f"Gjennomsnittlig effekt i drift: {avg_no:.2f} MW")

print("\n=== CASE 3 – MED EKSTRA TURBIN ===")
print(f"Total energi: {energy_yes:,.1f} MWh")
print(f"Total inntekt: {income_yes:,.0f} kr")
print(f"Driftstimer: {drift_yes}")
print(f"Oppstarter: {starts_yes}")
print(f"Gjennomsnittlig effekt i drift: {avg_yes:.2f} MW")

print("\n=== GEVINST EKSTRA TURBIN ===")
print(f"Ekstra energi: {energy_yes-energy_no:,.1f} MWh")
print(f"Ekstra inntekt: {income_yes-income_no:,.0f} kr")

# ============================================================
# 9) PLOTS
# ============================================================

plt.figure(figsize=(14,5))
plt.plot(results["Datetime"], results["P_main_MW"], label="Uten ekstra turbin")
plt.plot(results["Datetime"], results["P_MW"], label="Med ekstra turbin")
plt.ylabel("Effekt (MW)")
plt.title("Case 3 – Produksjon med og uten ekstra turbin")
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()

weekly = results.set_index("Datetime")[["P_main_MW","P_MW"]].resample("W").mean()

plt.figure(figsize=(14,5))
plt.plot(weekly.index, weekly["P_main_MW"], label="Uten ekstra turbin")
plt.plot(weekly.index, weekly["P_MW"], label="Med ekstra turbin")
plt.ylabel("MW")
plt.title("Case 3 – Ukemidlet produksjon")
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()

