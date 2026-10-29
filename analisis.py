import csv
import os
import matplotlib
matplotlib.use('Agg')  # Sin ventana, solo guarda imágenes
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

# ============================================================
# 1. LEER DATOS
# ============================================================
def leer_csv(nombre):
    with open(nombre, 'r') as f:
        return list(csv.DictReader(f))

accidentes = leer_csv('accidentes.csv')
hospitales = leer_csv('hospitales.csv')

# Convertir tipos numéricos
def to_int(v):
    if v is None or v == '':
        return None
    try:
        return int(v)
    except:
        return None

for a in accidentes:
    for k in ['t_accidente', 't_despacho', 't_llegada', 't_retorno']:
        a[k] = to_int(a[k])

for h in hospitales:
    for k in ['Stock Inicial', 'Stock Final']:
        h[k] = to_int(h[k])

# ============================================================
# 2. CALCULAR INDICADORES
# ============================================================
# Solo accidentes con tiempo de respuesta medible (despacho y llegada)
validos = [a for a in accidentes if a['t_despacho'] is not None and a['t_llegada'] is not None]

tiempos_respuesta = [a['t_llegada'] - a['t_despacho'] for a in validos]
tiempos_totales = [a['t_llegada'] - a['t_accidente'] for a in validos]

print("\n=== INDICADORES ===")
print(f"Total accidentes registrados: {len(accidentes)}")
print(f"Accidentes cerrados (con respuesta): {len(validos)}")
print(f"Accidentes en espera (sin ambulancia): {sum(1 for a in accidentes if a['estado']=='espera')}")

if tiempos_respuesta:
    print(f"\nTiempo de respuesta (despacho → llegada):")
    print(f"  Mediana: {np.median(tiempos_respuesta):.0f} s")
    print(f"  Media:   {np.mean(tiempos_respuesta):.0f} s")
    print(f"  P90:     {np.percentile(tiempos_respuesta, 90):.0f} s")
    print(f"  Mín:     {min(tiempos_respuesta)} s")
    print(f"  Máx:     {max(tiempos_respuesta)} s")

if tiempos_totales:
    print(f"\nTiempo total (accidente → llegada):")
    print(f"  Mediana: {np.median(tiempos_totales):.0f} s")
    print(f"  Media:   {np.mean(tiempos_totales):.0f} s")
    print(f"  P90:     {np.percentile(tiempos_totales, 90):.0f} s")

# Retornos a hospital distinto
retornos_distintos = sum(1 for a in accidentes if a['h_origen'] and a['h_retorno'] and a['h_origen'] != a['h_retorno'] and a['estado']=='cerrado')
total_cerrados = sum(1 for a in accidentes if a['estado']=='cerrado')
print(f"\nRetornos a hospital distinto: {retornos_distintos}/{total_cerrados} ({100*retornos_distintos/max(total_cerrados,1):.1f}%)")

# Despachos y retornos por hospital
despachos_por_hosp = defaultdict(int)
retornos_por_hosp = defaultdict(int)
for a in accidentes:
    if a['h_origen']:
        despachos_por_hosp[a['h_origen']] += 1
    if a['h_retorno'] and a['estado'] == 'cerrado':
        retornos_por_hosp[a['h_retorno']] += 1

print("\n=== USO POR HOSPITAL ===")
print(f"{'Hospital':<15} {'Stock Ini':<10} {'Stock Fin':<10} {'Despachos':<10} {'Retornos':<10} {'Utilización'}")
for h in hospitales:
    hid = h['Hospital']
    util = ""
    if hid in ['VCM', 'IESS_JCA', 'MILITAR', 'MUNI_PAT', 'MUNI_VALLE']:
        # Utilización = tiempo ocupado / (3h * stock inicial)
        # Aproximación: contar cuántos despachos salieron
        d = despachos_por_hosp.get(hid, 0)
        if h['Stock Inicial'] > 0:
            # Cada despacho ocupa ~600s en promedio
            util = f"{(d*600)/(3*3600*h['Stock Inicial'])*100:.1f}%"
        else:
            util = "n/a"
    print(f"{hid:<15} {h['Stock Inicial']:<10} {h['Stock Final']:<10} {despachos_por_hosp.get(hid,0):<10} {retornos_por_hosp.get(hid,0):<10} {util}")

# ============================================================
# 3. GRÁFICO (A): Tiempo de respuesta por accidente
# ============================================================
fig, ax = plt.subplots(figsize=(12, 6))
ids = [a['id'] for a in validos]
valores = [a['t_llegada'] - a['t_despacho'] for a in validos]
colores = ['#2E86AB' if a['estado']=='cerrado' else '#E63946' for a in validos]

bars = ax.bar(range(len(valores)), valores, color=colores, edgecolor='black')
ax.set_xticks(range(len(valores)))
ax.set_xticklabels([f"{a['id']}\n{a['t_accidente']//60}min" for a in validos], rotation=45, ha='right', fontsize=8)
ax.set_ylabel('Tiempo de respuesta (s)', fontsize=11)
ax.set_xlabel('Accidente (ID y minuto de ocurrencia)', fontsize=11)
ax.set_title('Tiempo de respuesta de la ambulancia · 15 accidentes en 3 h', fontsize=13, fontweight='bold')

# Líneas de mediana y p90
mediana = np.median(valores)
p90 = np.percentile(valores, 90)
ax.axhline(mediana, color='gray', linestyle='--', linewidth=1.5, label=f'Mediana {mediana:.0f}s')
ax.axhline(p90, color='red', linestyle=':', linewidth=1.5, label=f'P90 {p90:.0f}s')

# Etiquetas de hospital de origen
for i, a in enumerate(validos):
    if a['h_origen']:
        ax.text(i, valores[i] + 20, a['h_origen'][:6], ha='center', fontsize=7, rotation=90)

ax.legend(loc='upper left')
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('RA_fig_a_tiempo_respuesta.png', dpi=100)
plt.close()
print("\n✅ Gráfico (a) guardado: RA_fig_a_tiempo_respuesta.png")

# ============================================================
# 4. GRÁFICO (B): Stock, despachos y retornos por hospital
# ============================================================
fig, ax = plt.subplots(figsize=(12, 6))
nombres = [h['Hospital'] for h in hospitales]
x = np.arange(len(nombres))
width = 0.25

stock_ini = [h['Stock Inicial'] for h in hospitales]
stock_fin = [h['Stock Final'] for h in hospitales]
desp = [despachos_por_hosp.get(h['Hospital'], 0) for h in hospitales]
ret = [retornos_por_hosp.get(h['Hospital'], 0) for h in hospitales]

ax.bar(x - width, stock_ini, width, label='Stock inicial', color='#A8DADC', edgecolor='black')
ax.bar(x, desp, width, label='Despachos', color='#1D3557', edgecolor='black')
ax.bar(x + width, ret, width, label='Retornos', color='#457B9D', edgecolor='black')

ax.set_xticks(x)
ax.set_xticklabels(nombres, rotation=45, ha='right', fontsize=9)
ax.set_ylabel('Cantidad de ambulancias', fontsize=11)
ax.set_title('Uso de ambulancias por hospital · stock, despachos y retornos (3 h)', fontsize=13, fontweight='bold')
ax.legend()
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('RA_fig_b_uso_hospital.png', dpi=100)
plt.close()
print("✅ Gráfico (b) guardado: RA_fig_b_uso_hospital.png")

# ============================================================
# 5. GRÁFICO (C): Evolución del stock por hospital
# ============================================================
# Como no guardamos stock.csv, hacemos un gráfico simplificado de stock inicial vs final
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

ax1 = axes[0]
ax1.bar(range(len(nombres)), stock_ini, color='#A8DADC', edgecolor='black', label='Inicial')
ax1.bar(range(len(nombres)), stock_fin, color='#1D3557', edgecolor='black', alpha=0.7, label='Final')
ax1.set_xticks(range(len(nombres)))
ax1.set_xticklabels(nombres, rotation=45, ha='right', fontsize=8)
ax1.set_ylabel('Ambulancias', fontsize=11)
ax1.set_title('Stock inicial vs final', fontsize=12, fontweight='bold')
ax1.legend()
ax1.grid(axis='y', alpha=0.3)

# Panel derecho: utilización (aproximada)
ax2 = axes[1]
utils = []
labels = []
for h in hospitales:
    hid = h['Hospital']
    if hid in ['VCM', 'IESS_JCA', 'MILITAR', 'MUNI_PAT', 'MUNI_VALLE']:
        d = despachos_por_hosp.get(hid, 0)
        if h['Stock Inicial'] > 0:
            u = (d * 600) / (3 * 3600 * h['Stock Inicial']) * 100
            utils.append(u)
            labels.append(hid)
ax2.barh(range(len(utils)), utils, color='#E63946', edgecolor='black')
ax2.set_yticks(range(len(utils)))
ax2.set_yticklabels(labels, fontsize=9)
ax2.set_xlabel('Utilización (%)', fontsize=11)
ax2.set_title('Utilización de hospitales públicos', fontsize=12, fontweight='bold')
ax2.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig('RA_fig_c_stock_tiempo.png', dpi=100)
plt.close()
print("✅ Gráfico (c) guardado: RA_fig_c_stock_tiempo.png")

# ============================================================
# 6. GRÁFICO (D): Mapa con hospitales y accidentes
# ============================================================
HOSPITALES_COORD = {
    "VCM": (-78.992923, -2.911098),
    "IESS_JCA": (-78.970118, -2.898698),
    "MILITAR": (-79.003968, -2.903146),
    "MUNI_PAT": (-78.982263, -2.866103),
    "MUNI_VALLE": (-78.961959, -2.919522),
    "MONTE_SINAI": (-79.007373, -2.908606),
    "DEL_RIO": (-78.960796, -2.892939)
}

fig, ax = plt.subplots(figsize=(12, 10))

# Dibujar hospitales
for hid, (lon, lat) in HOSPITALES_COORD.items():
    color = 'blue' if hid in ['VCM', 'IESS_JCA', 'MILITAR', 'MUNI_PAT', 'MUNI_VALLE'] else 'purple'
    ax.scatter(lon, lat, s=200, c=color, marker='H', edgecolor='black', zorder=5, label=hid if hid in ['VCM', 'IESS_JCA'] else None)
    ax.annotate(hid, (lon, lat), xytext=(5, 5), textcoords='offset points', fontsize=8, fontweight='bold')

# Dibujar accidentes (usando coordenadas del hospital de origen como proxy)
for a in accidentes:
    if a['h_origen'] in HOSPITALES_COORD:
        lon, lat = HOSPITALES_COORD[a['h_origen']]
        color = 'red' if a['estado'] == 'espera' else 'orange'
        ax.scatter(lon + np.random.uniform(-0.005, 0.005), lat + np.random.uniform(-0.005, 0.005), 
                   s=80, c=color, marker='X', edgecolor='black', zorder=4)

# Líneas de retorno
for a in accidentes:
    if a['h_origen'] in HOSPITALES_COORD and a['h_retorno'] in HOSPITALES_COORD:
        x1, y1 = HOSPITALES_COORD[a['h_origen']]
        x2, y2 = HOSPITALES_COORD[a['h_retorno']]
        ax.plot([x1, x2], [y1, y2], 'g--', alpha=0.3, linewidth=1)

ax.set_xlabel('Longitud', fontsize=11)
ax.set_ylabel('Latitud', fontsize=11)
ax.set_title('Mapa de Cuenca · hospitales, accidentes y rutas de retorno', fontsize=13, fontweight='bold')
ax.grid(alpha=0.3)
ax.legend(loc='lower right')
plt.tight_layout()
plt.savefig('RA_fig_d_mapa.png', dpi=100)
plt.close()
print("✅ Gráfico (d) guardado: RA_fig_d_mapa.png")

print("\n=== TODOS LOS GRÁFICOS GENERADOS ===")
print("  RA_fig_a_tiempo_respuesta.png")
print("  RA_fig_b_uso_hospital.png")
print("  RA_fig_c_stock_tiempo.png")
print("  RA_fig_d_mapa.png")
