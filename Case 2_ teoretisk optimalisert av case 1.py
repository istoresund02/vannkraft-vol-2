#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 13:42:24 2026

@author: idastoresund
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --------------------------------------------------
# CASE 1 – FAKTISK DRIFTSMØNSTER
# --------------------------------------------------

df = pd.read_excel("Sildvik_Produksjon_Pris_2024-2.xlsx", engine="openpyxl")

df["Datetime"] = pd.to_datetime(df["Datetime"])
df["MWh"] = pd.to_numeric(df["MWh"], errors="coerce")
df["Price_ore_kWh"] = pd.to_numeric(df["Price_ore_kWh"], errors="coerce")

df = df.dropna(subset=["Datetime", "MWh", "Price_ore_kWh"]).copy()
df = df.sort_values("Datetime").reset_index(drop=True)

# --------------------------------------------------
# Beregn effekt og vannføring (faktisk)
# --------------------------------------------------

rho = 1000
g = 9.81
H = 680
eta = 0.90

df["P_MW"] = df["MWh"]            # MWh per time = MW
df["Power_W"] = df["P_MW"] * 1e6
df["Q_m3s"] = df["Power_W"] / (eta * rho * g * H)

# --------------------------------------------------
# Nøkkeltall Case 1
# --------------------------------------------------

total_energy = df["MWh"].sum()
total_income = (df["MWh"] * df["Price_ore_kWh"] * 1000 / 100).sum()
drift_hours = (df["MWh"] > 0).sum()
starts = ((df["MWh"] > 0) & (df["MWh"].shift(1, fill_value=0) == 0)).sum()
avg_power_when_running = df.loc[df["MWh"] > 0, "P_MW"].mean()

print("=== NØKKELTALL CASE 1 – FAKTISK ===")
print(f"Total energi: {total_energy:.1f} MWh")
print(f"Total inntekt: {total_income:,.0f} kr")
print(f"Driftstimer: {drift_hours}")
print(f"Antall oppstarter: {starts}")
print(f"Gjennomsnittlig effekt i drift: {avg_power_when_running:.2f} MW")

# --------------------------------------------------
# PLOTS CASE 1
# --------------------------------------------------

plt.figure(figsize=(14, 5))
plt.plot(df["Datetime"], df["P_MW"], label="Faktisk produksjon (MW)")
plt.ylabel("Effekt (MW)")
plt.title("Case 1 – faktisk produksjonsmønster")
plt.grid(True, alpha=0.3)
plt.legend()
plt.show()


# ==================================================
# CASE 2 – TEORETISK OPTIMAL DRIFT (PRISBASERT)
# ==================================================
# Antakelser:
# - Ingen start/stopp-kostnader
# - Ingen rampingbegrensninger
# - Ingen minimumslast
# - Produksjon enten 0 eller maks
# - Produksjon kun i timer med høy pris
# ==================================================

df_case2 = df.copy()

# Maks observert effekt brukes som teoretisk kapasitet
P_max = df_case2["P_MW"].max()

# Prisgrense: øverste 25 % av prisene
price_threshold = np.percentile(df_case2["Price_ore_kWh"], 75)

# Teoretisk produksjon (bang–bang)
df_case2["P_MW_theoretical"] = np.where(
    df_case2["Price_ore_kWh"] >= price_threshold,
    P_max,
    0.0
)

# Energi (1 time per steg)
df_case2["MWh_theoretical"] = df_case2["P_MW_theoretical"]

# Beregn vannføring for teoretisk drift
df_case2["Power_W_theoretical"] = df_case2["P_MW_theoretical"] * 1e6
df_case2["Q_m3s_theoretical"] = (
    df_case2["Power_W_theoretical"] / (eta * rho * g * H)
)

# --------------------------------------------------
# Nøkkeltall Case 2
# --------------------------------------------------

total_energy_2 = df_case2["MWh_theoretical"].sum()
total_income_2 = (
    df_case2["MWh_theoretical"]
    * df_case2["Price_ore_kWh"]
    * 1000 / 100
).sum()

drift_hours_2 = (df_case2["P_MW_theoretical"] > 0).sum()
starts_2 = (
    (df_case2["P_MW_theoretical"] > 0) &
    (df_case2["P_MW_theoretical"].shift(1, fill_value=0) == 0)
).sum()

print("\n=== NØKKELTALL CASE 2 – TEORETISK OPTIMAL ===")
print(f"Total energi: {total_energy_2:.1f} MWh")
print(f"Total inntekt: {total_income_2:,.0f} kr")
print(f"Driftstimer: {drift_hours_2}")
print(f"Antall oppstarter: {starts_2}")
print(f"Maks effekt brukt: {P_max:.2f} MW")
print(f"Prisgrense (75‑percentil): {price_threshold:.2f} øre/kWh")

# --------------------------------------------------
# SAMMENLIGNINGSPLOT
# --------------------------------------------------

plt.figure(figsize=(14, 5))
plt.plot(df["Datetime"], df["P_MW"],
         label="Faktisk drift (Case 1)", alpha=0.6)
plt.plot(df_case2["Datetime"], df_case2["P_MW_theoretical"],
         label="Teoretisk optimal drift (Case 2)", linewidth=2)
plt.ylabel("Effekt (MW)")
plt.title("Faktisk vs teoretisk optimal drift")
plt.grid(True, alpha=0.3)
plt.legend()
plt.show()
