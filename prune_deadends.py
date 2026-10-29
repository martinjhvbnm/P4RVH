import sys
import xml.etree.ElementTree as ET

if len(sys.argv) < 2:
    print("Uso: python3 prune_deadends.py <red_input.net.xml>")
    sys.exit(1)

net_file = sys.argv[1]
tree = ET.parse(net_file)
root = tree.getroot()

incoming = {}
outgoing = {}

for edge in root.findall('edge'):
    if edge.get('function') in ['internal', 'connector']:
        continue
    edge_id = edge.get('id')
    from_node = edge.get('from')
    to_node = edge.get('to')
    
    if from_node:
        outgoing.setdefault(from_node, []).append(edge_id)
    if to_node:
        incoming.setdefault(to_node, []).append(edge_id)

deadends = []
for edge in root.findall('edge'):
    if edge.get('function') in ['internal', 'connector']:
        continue
    edge_id = edge.get('id')
    from_node = edge.get('from')
    to_node = edge.get('to')
    
    if (from_node in incoming and len(incoming[from_node]) == 0) or \
       (to_node in outgoing and len(outgoing[to_node]) == 0):
        deadends.append(edge_id)

with open("deadends.txt", "w") as f:
    f.write(",".join(deadends))

print(f"Se identificaron {len(deadends)} aristas ciegas guardadas en deadends.txt")
