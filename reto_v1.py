import sys
import os
sys.path.append(os.path.join(os.environ.get("SUMO_HOME", "/usr/share/sumo"), "tools"))

import traci
import random
from collections import deque
import csv

SEED = 42
random.seed(SEED)
rng = random.Random(SEED)

HOSPITALES = {
    "VCM": {"tipo": "público", "lon": -78.992923, "lat": -2.911098},
    "IESS_JCA": {"tipo": "público", "lon": -78.970118, "lat": -2.898698},
    "MILITAR": {"tipo": "público", "lon": -79.003968, "lat": -2.903146},
    "MUNI_PAT": {"tipo": "público", "lon": -78.982263, "lat": -2.866103},
    "MUNI_VALLE": {"tipo": "público", "lon": -78.961959, "lat": -2.919522},
    "MONTE_SINAI": {"tipo": "privado", "lon": -79.007373, "lat": -2.908606},
    "DEL_RIO": {"tipo": "privado", "lon": -78.960796, "lat": -2.892939}
}

class Hospital:
    def __init__(self, hid, info):
        self.hid = hid
        self.tipo = info["tipo"]
        self.lon = info["lon"]
        self.lat = info["lat"]
        self.edge = ""
        self.pos = 0.0
        self.cola = deque()
        self.stock_ini = 0

    def ubicar(self):
        res = traci.simulation.convertRoad(self.lon, self.lat, isGeo=True, vClass="emergency")
        self.edge = res[0]
        self.pos = res[1]
        
        self.stock_ini = rng.randint(1, 3) if self.tipo == "público" else rng.randint(0, 1)
        for i in range(self.stock_ini):
            self.cola.append(f"{self.hid}_U{i+1:02d}")

# --- INICIO ---
traci.start(["sumo", "-c", "reto.sumocfg"]) 

hospitales_dict = {}
print("\n--- TABLA DE HOSPITALES Y FLOTA INICIAL ---")
for hid, info in HOSPITALES.items():
    h = Hospital(hid, info)
    h.ubicar()
    hospitales_dict[hid] = h
    print(f"{h.hid:<12} | Stock: {list(h.cola)}")

# FASE 3: Agenda de 15 accidentes (5 por hora)
agenda_accidentes = []
for hora in range(3):
    for _ in range(5):
        t = (hora * 3600) + rng.randint(300, 3300)
        agenda_accidentes.append(t)
agenda_accidentes.sort()
print(f"Agenda: {len(agenda_accidentes)} accidentes programados (5/hora)")

accidentes = [] 
colisiones_vistas = set()
ambulancias_activas = {}
motos_sueltas = {}  # moto_id -> {"t_creacion": step, "t_acc": instante_programado}

step = 0
end_time = 12600

print("\n--- INICIANDO SIMULACIÓN ---")
while step < end_time:
    traci.simulationStep()

    # 1. PROVOCAR ACCIDENTES
    if agenda_accidentes and step >= agenda_accidentes[0]:
        t_acc = agenda_accidentes.pop(0)
        buses = [v for v in traci.vehicle.getIDList() if traci.vehicle.getTypeID(v) == "bus" 
                 and traci.vehicle.getSpeed(v) > 4.0 and not traci.vehicle.getRoadID(v).startswith(":")]
        
        if buses:
            bus_id = rng.choice(buses)
            pos_bus = traci.vehicle.getLanePosition(bus_id)
            pos_moto = max(0.0, pos_bus - 45.0)
            ruta_bus = traci.vehicle.getRoute(bus_id)
            ruta_moto = ruta_bus[traci.vehicle.getRouteIndex(bus_id):]
            
            moto_id = f"moto_imp_{t_acc}"
            traci.route.add(f"ruta_{moto_id}", ruta_moto)
            traci.vehicle.add(moto_id, f"ruta_{moto_id}", typeID="moto", departPos=pos_moto, departSpeed=22.0)
            
            traci.vehicle.setSpeedMode(moto_id, 0)
            traci.vehicle.setLaneChangeMode(moto_id, 0)
            traci.vehicle.setSpeed(moto_id, 22.0)
            motos_sueltas[moto_id] = {"t_creacion": step, "t_acc": t_acc}
            print(f"[t={step}] IMPRUDENTE: moto persigue a bus {bus_id}")
        else:
            agenda_accidentes.insert(0, step + 5)

    # CONTROL DE MOTOS SUELTAS: Si no choca en 90s, REPROGRAMAR (manual Fase 3)
    for m_id, info_moto in list(motos_sueltas.items()):
        if m_id in traci.vehicle.getIDList():
            if step - info_moto["t_creacion"] > 90:
                traci.vehicle.remove(m_id)
                nuevo_t = info_moto["t_acc"] + 60
                if nuevo_t < end_time - 200:
                    agenda_accidentes.append(nuevo_t)
                    agenda_accidentes.sort()
                    print(f"[t={step}] La moto {m_id} no chocó; se reprograma a t={nuevo_t}")
                del motos_sueltas[m_id]
        else:
            if step - info_moto["t_creacion"] > 300:
                del motos_sueltas[m_id]

    # 2. DETECTAR COLISIONES
    for col in traci.simulation.getCollisions():
        tipos = {col.colliderType, col.victimType}
        if "bus" in tipos and "moto" in tipos:
            par_normalizado = tuple(sorted([col.collider, col.victim]))
            if par_normalizado in colisiones_vistas:
                continue
            colisiones_vistas.add(par_normalizado)
            
            bus_id = col.collider if col.colliderType == "bus" else col.victim
            moto_id = col.victim if col.colliderType == "bus" else col.collider
            
            if moto_id in motos_sueltas:
                del motos_sueltas[moto_id]
            
            acc_id = f"ACC_{len(accidentes)+1:02d}"
            print(f"[t={step}] ACCIDENTE {acc_id}: {bus_id} x {moto_id}")
            
            for v in [bus_id, moto_id]:
                if v in traci.vehicle.getIDList():
                    traci.vehicle.setSpeedMode(v, 31)
                    traci.vehicle.setSpeed(v, 0)
                    traci.vehicle.setColor(v, (255, 0, 0, 255))

            accidentes.append({
                "id": acc_id, "t_accidente": step, "t_despacho": None, "t_llegada": None, 
                "t_retorno": None, "bus": bus_id, "moto": moto_id, "h_origen": None, 
                "h_retorno": None, "estado": "espera", "amb_id": None, "t_siguiente_intento": step,
                "t_llegada_criterio": None
            })

    # 3. DESPACHO
    for acc in accidentes:
        if acc["estado"] == "espera" and step >= acc["t_siguiente_intento"]:
            mejor_hospital = None
            mejor_tiempo = float('inf')
            
            for hid, h in hospitales_dict.items():
                if h.cola:
                    if rng.random() < 0.25:
                        continue 
                    
                    if acc["bus"] not in traci.vehicle.getIDList():
                        acc["estado"] = "cancelado"
                        if acc["moto"] in traci.vehicle.getIDList():
                            traci.vehicle.remove(acc["moto"])
                        break
                        
                    ruta = traci.simulation.findRoute(h.edge, traci.vehicle.getRoadID(acc["bus"]), vType="ambulance")
                    if ruta.edges and ruta.travelTime < mejor_tiempo:
                        mejor_tiempo = ruta.travelTime
                        mejor_hospital = h
            
            if mejor_hospital:
                unidad = mejor_hospital.cola.popleft()
                amb_id = f"amb_{unidad}_{acc['id']}"
                ruta = traci.simulation.findRoute(mejor_hospital.edge, traci.vehicle.getRoadID(acc["bus"]), vType="ambulance")
                traci.route.add(f"ruta_{amb_id}", ruta.edges)
                traci.vehicle.add(amb_id, f"ruta_{amb_id}", typeID="ambulance", departPos=mejor_hospital.pos)
                
                acc["estado"] = "en_camino"
                acc["t_despacho"] = step
                acc["h_origen"] = mejor_hospital.hid
                acc["amb_id"] = amb_id
                ambulancias_activas[amb_id] = acc
                print(f"[t={step}] DESPACHO {acc['id']} desde {mejor_hospital.hid} | ETA: {ruta.travelTime:.0f}s")
            elif acc["estado"] == "espera":
                acc["t_siguiente_intento"] = step + 30

    # 4. LLEGADA Y ATENCIÓN
    for amb_id, acc in list(ambulancias_activas.items()):
        if amb_id not in traci.vehicle.getIDList():
            continue
            
        if acc["estado"] == "en_camino":
            if acc["bus"] not in traci.vehicle.getIDList():
                acc["estado"] = "cancelado"
                if acc["moto"] in traci.vehicle.getIDList():
                    traci.vehicle.remove(acc["moto"])
                continue
            
            if step % 30 == 0:
                try:
                    nueva_arista = traci.vehicle.getRoadID(acc["bus"])
                    if nueva_arista and not nueva_arista.startswith(":"):
                        traci.vehicle.changeTarget(amb_id, nueva_arista)
                except:
                    pass
                
            # Cálculo de distancia con CLAMPEO de posiciones (evita "Position on lane invalid")
            try:
                road_amb = traci.vehicle.getRoadID(amb_id)
                road_bus = traci.vehicle.getRoadID(acc["bus"])
                
                if road_amb.startswith(":") or road_bus.startswith(":"):
                    x1, y1 = traci.vehicle.getPosition(amb_id)
                    x2, y2 = traci.vehicle.getPosition(acc["bus"])
                    dist = ((x1-x2)**2 + (y1-y2)**2) ** 0.5
                else:
                    lane_amb = traci.vehicle.getLaneID(amb_id)
                    lane_bus = traci.vehicle.getLaneID(acc["bus"])
                    pos_amb = traci.vehicle.getLanePosition(amb_id)
                    pos_bus = traci.vehicle.getLanePosition(acc["bus"])
                    if lane_amb:
                        pos_amb = max(0.0, min(pos_amb, traci.lane.getLength(lane_amb)))
                    if lane_bus:
                        pos_bus = max(0.0, min(pos_bus, traci.lane.getLength(lane_bus)))
                    
                    dist = traci.simulation.getDistanceRoad(road_amb, pos_amb, road_bus, pos_bus, isDriving=True)
            except Exception:
                try:
                    x1, y1 = traci.vehicle.getPosition(amb_id)
                    x2, y2 = traci.vehicle.getPosition(acc["bus"])
                    dist = ((x1-x2)**2 + (y1-y2)**2) ** 0.5
                except:
                    dist = 99999
            
            llegó = False
            if 0 <= dist <= 50:
                llegó = True
            elif road_amb == road_bus:
                llegó = True
            elif 0 <= dist <= 300 and traci.vehicle.getSpeed(amb_id) < 0.1:
                if acc["t_llegada_criterio"] is None:
                    acc["t_llegada_criterio"] = step
                elif step - acc["t_llegada_criterio"] >= 30:
                    llegó = True
            else:
                acc["t_llegada_criterio"] = None
            
            if llegó:
                acc["estado"] = "atendiendo"
                acc["t_llegada"] = step
                traci.vehicle.setSpeed(amb_id, 0)
                print(f"[t={step}] LLEGADA {acc['id']} | Respuesta: {step - acc['t_despacho']}s")

        elif acc["estado"] == "atendiendo":
            if step - acc["t_llegada"] >= 120:
                for v in [acc["bus"], acc["moto"]]:
                    if v in traci.vehicle.getIDList():
                        traci.vehicle.remove(v)
                
                mejor_h = None
                mejor_t = float('inf')
                for h in hospitales_dict.values():
                    ruta = traci.simulation.findRoute(traci.vehicle.getRoadID(amb_id), h.edge, vType="ambulance")
                    if ruta.edges and ruta.travelTime < mejor_t:
                        mejor_t = ruta.travelTime
                        mejor_h = h
                
                traci.vehicle.setSpeedMode(amb_id, 31)
                traci.vehicle.setLaneChangeMode(amb_id, 1621) 
                traci.vehicle.setSpeed(amb_id, -1)
                traci.vehicle.changeTarget(amb_id, mejor_h.edge)
                
                acc["estado"] = "retorno"
                acc["h_retorno"] = mejor_h.hid
                print(f"[t={step}] RETORNO {acc['id']} hacia {mejor_h.hid}")

    # 5. CIERRE DE MISIÓN
    arrived = traci.simulation.getArrivedIDList()
    for amb_id in arrived:
        if amb_id in ambulancias_activas:
            acc = ambulancias_activas.pop(amb_id)
            
            if acc["h_retorno"] is None:
                print(f"[t={step}] ADVERTENCIA: {amb_id} llegó sin destino; se cancela.")
                acc["estado"] = "cancelado"
                continue
                
            h_destino = hospitales_dict[acc["h_retorno"]]
            partes = amb_id.split("_")
            unidad_id = None
            for i, p in enumerate(partes):
                if p in HOSPITALES:
                    unidad_id = f"{p}_{partes[i+1]}" if i+1 < len(partes) else p
                    break
            if unidad_id is None:
                unidad_id = f"{h_destino.hid}_U01"
            
            h_destino.cola.append(unidad_id) 
            acc["t_retorno"] = step
            acc["estado"] = "cerrado"
            print(f"[t={step}] DISPONIBLE: Ambulancia {unidad_id} en {h_destino.hid}")

    step += 1

# --- FASE 5: GUARDAR ---
print("\n--- GUARDANDO RESULTADOS ---")
fieldnames_acc = ["id", "t_accidente", "t_despacho", "t_llegada", "t_retorno", 
                  "bus", "moto", "h_origen", "h_retorno", "estado", "amb_id", 
                  "t_siguiente_intento", "t_llegada_criterio"]
with open("accidentes.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames_acc)
    writer.writeheader()
    writer.writerows(accidentes)

with open("hospitales.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Hospital", "Tipo", "Stock Inicial", "Stock Final"])
    for h in hospitales_dict.values():
        writer.writerow([h.hid, h.tipo, h.stock_ini, len(h.cola)])

traci.close()
print("Simulación terminada. Archivos CSV generados.")
