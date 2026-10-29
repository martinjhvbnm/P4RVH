# P4RVH
Martín Bravo
# Reto: Accidentes bus-moto y despacho de ambulancias en Cuenca

**Estudiante:** Martín Bravo  
**Asignatura:** Redes Vehiculares y Heterogéneas  
**Docente:** Ph.D. Pablo Barbecho  
**Universidad de Cuenca** Septiembre 2026 – Febrero 2027

---

## Descripción

Gemelo digital de emergencias sobre SUMO + TraCI. Durante 3 horas simuladas circulan autos, buses y motos sin teleporting. Se provocan 15 accidentes bus-moto (5 por hora) mediante `speedMode(0)`. El script detecta cada choque, despacha la ambulancia del hospital más cercano en tiempo que tenga unidad disponible y la devuelve al hospital más cercano al accidente.

## Contenido del repositorio

| Archivo | Descripción |
|---|---|
| `cuenca_ciudad.net.xml` | Red de arterias de Cuenca |
| `vtypes.add.xml` | Tipos de vehículo (auto, bus, moto, ambulance) |
| `fondo_*.rou.xml` | Rutas de tráfico de fondo (3 h) |
| `reto.sumocfg` | Configuración sin teleporting |
| `reto_ambulancias.py` | Script principal TraCI |
| `analisis.py` | Estadísticas y gráficos |
| `resultados/` | CSVs, gráficos, log y resumen de la corrida |

## Cómo ejecutar

```bash
python3 reto_ambulancias.py > eventos.log 2>&1
python3 analisis.py > resumen.txt 2>&1
