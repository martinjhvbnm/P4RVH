#!/bin/bash
mkdir -p osm
LON_MIN=-79.030
LAT_MIN=-2.930
LON_MAX=-78.950
LAT_MAX=-2.860

N=5
DLON=$(python3 -c "print(($LON_MAX - ($LON_MIN))/$N)")
DLAT=$(python3 -c "print(($LAT_MAX - ($LAT_MIN))/$N)")

echo "Descargando teselas OSM de Cuenca..."
for i in $(seq 0 $((N-1))); do
    for j in $(seq 0 $((N-1))); do
        MIN_X=$(python3 -c "print($LON_MIN + $i*$DLON)")
        MAX_X=$(python3 -c "print($LON_MIN + ($i+1)*$DLON)")
        MIN_Y=$(python3 -c "print($LAT_MIN + $j*$DLAT)")
        MAX_Y=$(python3 -c "print($LAT_MIN + ($j+1)*$DLAT)")
        
        FILE="osm/tile_${i}_${j}.osm"
        echo "Descargando $FILE ..."
        curl -s "https://overpass-api.de/api/interpreter?data=(node($MIN_Y,$MIN_X,$MAX_Y,$MAX_X);<;);out%20meta;" -o "$FILE"
        sleep 2
    done
done
echo "Descarga completada."
