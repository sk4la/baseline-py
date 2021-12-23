import json
from uuid import uuid4
"""
def recurse_graph(path, content, graph):
    folders = path.split("/")
    folders = [f for f in folders if f]
    head = folders[0]
    subfolders = folders[1:]
    if not subfolders:
        graph[head] = content
    else:
        if head not in graph:
            graph[head] = {}
        recurse_graph("/".join(subfolders), content, graph[head])

def build_graph(paths):
    graph = {}
    for path, content in paths:
        recurse_graph(path, content, graph)
    return graph
"""
def build_graph(paths):
    nodes = set()
    edges = []
    for path, content in paths:
        folders = [ f for f in path.split("/") if f]
        #nodes.update(folders)
        for i in range(len(folders) - 1):
            if not folders[:i]:
                continue
            head = "-".join(folders[:i])
            tail = "-".join(folders[:i+1])
            nodes.add(head)
            nodes.add(tail)

            edges.append({"data": {
                "id": uuid4().hex,
                "source": head,
                "target": tail
            }})
    nodes = [{ "data": { "id": n } } for n in nodes]
    return nodes + edges

if __name__ == "__main__":
    paths = []
    with open("data.json", "r") as f:
        for line in f.readlines():
            json_line = json.loads(line)
            if json_line["signature"]["kind"] == "file":
                paths.append((json_line["fs"]["path"], json_line["fs"]["name"]))
    
    g = build_graph(paths)  
    with open("graph_cytoscape.json", "w+") as f:
        f.write(f"var g = {json.dumps(g)}\n")
