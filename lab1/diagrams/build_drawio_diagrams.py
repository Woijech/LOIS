from __future__ import annotations

import base64
import re
import json
import subprocess
import urllib.parse
import uuid
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass, field
from html import escape
from pathlib import Path


DIAGRAM_DIR = Path(__file__).resolve().parent
DRAWIO_DIR = DIAGRAM_DIR / "drawio"
GRAPHML_DIR = DIAGRAM_DIR / "graphml"
SCALE = 72.0
MARGIN = 32.0


@dataclass
class Node:
    name: str
    x: float
    y: float
    width: float
    height: float
    label: str
    shape: str


@dataclass
class Edge:
    source: str
    target: str
    points: list[tuple[float, float]]
    label: str = ""


@dataclass
class Graph:
    name: str
    width: float
    height: float
    nodes: list[Node]
    edges: list[Edge]


@dataclass
class UmlClass:
    name: str
    members: list[str] = field(default_factory=list)
    is_abstract: bool = False


def xml_id(*parts: str) -> str:
    raw = "::".join(parts)
    return "id-" + uuid.uuid5(uuid.NAMESPACE_URL, raw).hex


def text_value(value: str) -> str:
    return escape(value, quote=False).replace("\\n", "<br>").replace("\n", "<br>")


def parse_float(value: str) -> float:
    return float(value)


def read_startdot(path: Path) -> tuple[str, str] | None:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("@startdot "):
        return None
    output_name = lines[0].split(maxsplit=1)[1]
    return output_name, "\n".join(lines[1:-1]) + "\n"


def run_dot_json(dot_source: str) -> dict:
    result = subprocess.run(
        ["dot", "-Tjson"],
        input=dot_source,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return json.loads(result.stdout)


def parse_dot_json(name: str, data: dict) -> Graph:
    x0, y0, x1, y1 = (parse_float(part) for part in data["bb"].split(","))
    width = (x1 - x0) / SCALE
    height = (y1 - y0) / SCALE
    nodes: list[Node] = []
    edges: list[Edge] = []
    gvid_to_name: dict[int, str] = {}

    for obj in data.get("objects", []):
        obj_name = obj["name"]
        gvid_to_name[int(obj["_gvid"])] = obj_name
        x, y = (parse_float(part) / SCALE for part in obj["pos"].split(","))
        nodes.append(
            Node(
                name=obj_name,
                x=x,
                y=y,
                width=parse_float(obj["width"]),
                height=parse_float(obj["height"]),
                label=obj.get("label", obj_name),
                shape=obj.get("shape", "box"),
            )
        )

    for item in data.get("edges", []):
        draw_points: list[tuple[float, float]] = []
        for draw_command in item.get("_draw_", []):
            if draw_command.get("op") == "b":
                draw_points = [
                    (parse_float(str(x)) / SCALE, parse_float(str(y)) / SCALE)
                    for x, y in draw_command["points"]
                ]
                break
        edges.append(
            Edge(
                source=gvid_to_name[int(item["tail"])],
                target=gvid_to_name[int(item["head"])],
                points=draw_points,
                label=item.get("label", ""),
            )
        )

    return Graph(name=name, width=width, height=height, nodes=nodes, edges=edges)


def mx_style_for_shape(shape: str, font_size: int = 12) -> str:
    base = (
        "whiteSpace=wrap;html=1;strokeColor=#000000;fillColor=#ffffff;"
        f"fontFamily=Times New Roman;fontSize={font_size};"
    )
    if shape == "oval":
        return "ellipse;" + base
    if shape == "diamond":
        return "rhombus;" + base
    if shape == "parallelogram":
        return "shape=parallelogram;perimeter=parallelogramPerimeter;" + base
    return "rounded=0;" + base


def to_drawio_point(graph: Graph, point: tuple[float, float]) -> tuple[float, float]:
    x, y = point
    return (x * SCALE + MARGIN, (graph.height - y) * SCALE + MARGIN)


def add_geometry(
    parent: ET.Element,
    *,
    x: float | None = None,
    y: float | None = None,
    width: float | None = None,
    height: float | None = None,
    relative: str | None = None,
) -> ET.Element:
    attrs = {"as": "geometry"}
    if x is not None:
        attrs["x"] = f"{x:.2f}"
    if y is not None:
        attrs["y"] = f"{y:.2f}"
    if width is not None:
        attrs["width"] = f"{width:.2f}"
    if height is not None:
        attrs["height"] = f"{height:.2f}"
    if relative is not None:
        attrs["relative"] = relative
    return ET.SubElement(parent, "mxGeometry", attrs)


def add_point(parent: ET.Element, point: tuple[float, float], name: str | None = None) -> None:
    attrs = {"x": f"{point[0]:.2f}", "y": f"{point[1]:.2f}"}
    if name is not None:
        attrs["as"] = name
    ET.SubElement(parent, "mxPoint", attrs)


def build_mx_graph_model(name: str) -> tuple[ET.Element, ET.Element]:
    model = ET.Element(
        "mxGraphModel",
        {
            "dx": "1422",
            "dy": "794",
            "grid": "1",
            "gridSize": "10",
            "guides": "1",
            "tooltips": "1",
            "connect": "1",
            "arrows": "1",
            "fold": "1",
            "page": "1",
            "pageScale": "1",
            "pageWidth": "1169",
            "pageHeight": "827",
            "math": "0",
            "shadow": "0",
        },
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    return model, root


def write_drawio(name: str, model: ET.Element, output_path: Path) -> None:
    write_drawio_file([(name, model)], output_path)


def encode_diagram_model(model: ET.Element) -> str:
    xml = ET.tostring(model, encoding="unicode", short_empty_elements=True)
    quoted = urllib.parse.quote(xml, safe="~()*!.'")
    compressor = zlib.compressobj(level=9, wbits=-15)
    compressed = compressor.compress(quoted.encode("utf-8")) + compressor.flush()
    return base64.b64encode(compressed).decode("ascii")


def decode_diagram_model(encoded: str) -> ET.Element:
    compressed = base64.b64decode(encoded)
    quoted = zlib.decompress(compressed, wbits=-15).decode("utf-8")
    xml = urllib.parse.unquote(quoted)
    return ET.fromstring(xml)


def write_drawio_file(pages: list[tuple[str, ET.Element]], output_path: Path) -> None:
    mxfile = ET.Element(
        "mxfile",
        {
            "host": "app.diagrams.net",
            "modified": "2026-05-05T00:00:00.000Z",
            "agent": "LOIS diagram generator",
            "version": "24.7.17",
            "type": "device",
        },
    )

    for name, model in pages:
        diagram = ET.SubElement(mxfile, "diagram", {"id": xml_id(name, "diagram"), "name": name})
        diagram.text = encode_diagram_model(model)

    tree = ET.ElementTree(mxfile)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)


def graphml_shape(shape: str) -> str:
    if shape == "oval":
        return "ellipse"
    if shape == "diamond":
        return "diamond"
    if shape == "parallelogram":
        return "parallelogram"
    return "rectangle"


def graph_to_graphml(graph: Graph, output_path: Path) -> None:
    ns = {
        "": "http://graphml.graphdrawing.org/xmlns",
        "y": "http://www.yworks.com/xml/graphml",
    }
    for prefix, uri in ns.items():
        ET.register_namespace(prefix, uri)

    graphml = ET.Element(
        "graphml",
        {
            "xmlns": ns[""],
        },
    )
    ET.SubElement(graphml, "key", {"id": "d0", "for": "node", "yfiles.type": "nodegraphics"})
    ET.SubElement(graphml, "key", {"id": "d1", "for": "edge", "yfiles.type": "edgegraphics"})
    root_graph = ET.SubElement(graphml, "graph", {"id": graph.name, "edgedefault": "directed"})
    node_ids = {node.name: f"n{index}" for index, node in enumerate(graph.nodes)}

    for node in graph.nodes:
        width = node.width * SCALE
        height = node.height * SCALE
        x = (node.x - node.width / 2) * SCALE + MARGIN
        y = (graph.height - node.y - node.height / 2) * SCALE + MARGIN
        graphml_node = ET.SubElement(root_graph, "node", {"id": node_ids[node.name]})
        data = ET.SubElement(graphml_node, "data", {"key": "d0"})
        shape_node = ET.SubElement(data, f"{{{ns['y']}}}ShapeNode")
        ET.SubElement(
            shape_node,
            f"{{{ns['y']}}}Geometry",
            {"x": f"{x:.2f}", "y": f"{y:.2f}", "width": f"{width:.2f}", "height": f"{height:.2f}"},
        )
        ET.SubElement(shape_node, f"{{{ns['y']}}}Fill", {"color": "#FFFFFF", "transparent": "false"})
        ET.SubElement(
            shape_node,
            f"{{{ns['y']}}}BorderStyle",
            {"color": "#000000", "type": "line", "width": "1.2"},
        )
        label = ET.SubElement(
            shape_node,
            f"{{{ns['y']}}}NodeLabel",
            {
                "alignment": "center",
                "fontFamily": "Times New Roman",
                "fontSize": "12",
                "textColor": "#000000",
            },
        )
        label.text = node.label.replace("\\n", "\n")
        ET.SubElement(shape_node, f"{{{ns['y']}}}Shape", {"type": graphml_shape(node.shape)})

    for index, edge in enumerate(graph.edges):
        graphml_edge = ET.SubElement(
            root_graph,
            "edge",
            {"id": f"e{index}", "source": node_ids[edge.source], "target": node_ids[edge.target]},
        )
        data = ET.SubElement(graphml_edge, "data", {"key": "d1"})
        polyline = ET.SubElement(data, f"{{{ns['y']}}}PolyLineEdge")
        ET.SubElement(polyline, f"{{{ns['y']}}}LineStyle", {"color": "#000000", "type": "line", "width": "1.1"})
        ET.SubElement(polyline, f"{{{ns['y']}}}Arrows", {"source": "none", "target": "standard"})
        if edge.points:
            path = ET.SubElement(polyline, f"{{{ns['y']}}}Path", {"sx": "0.0", "sy": "0.0", "tx": "0.0", "ty": "0.0"})
            for point in edge.points[1:-1]:
                x, y = to_drawio_point(graph, point)
                ET.SubElement(path, f"{{{ns['y']}}}Point", {"x": f"{x:.2f}", "y": f"{y:.2f}"})
        if edge.label:
            edge_label = ET.SubElement(
                polyline,
                f"{{{ns['y']}}}EdgeLabel",
                {"fontFamily": "Times New Roman", "fontSize": "11", "textColor": "#000000"},
            )
            edge_label.text = edge.label
        ET.SubElement(polyline, f"{{{ns['y']}}}BendStyle", {"smoothed": "false"})

    tree = ET.ElementTree(graphml)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)


def graph_to_drawio(graph: Graph) -> ET.Element:
    model, root = build_mx_graph_model(graph.name)
    node_ids: dict[str, str] = {}

    for node in graph.nodes:
        node_id = xml_id(graph.name, "node", node.name)
        node_ids[node.name] = node_id
        width = node.width * SCALE
        height = node.height * SCALE
        x = (node.x - node.width / 2) * SCALE + MARGIN
        y = (graph.height - node.y - node.height / 2) * SCALE + MARGIN
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": node_id,
                "value": text_value(node.label),
                "style": mx_style_for_shape(node.shape),
                "vertex": "1",
                "parent": "1",
            },
        )
        add_geometry(cell, x=x, y=y, width=width, height=height)

    for index, edge in enumerate(graph.edges, start=1):
        edge_id = xml_id(graph.name, "edge", str(index), edge.source, edge.target)
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": edge_id,
                "value": text_value(edge.label),
                "style": (
                    "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;"
                    "jettySize=auto;html=1;endArrow=block;endFill=1;"
                    "strokeColor=#000000;fontFamily=Times New Roman;fontSize=11;"
                ),
                "edge": "1",
                "parent": "1",
                "source": node_ids[edge.source],
                "target": node_ids[edge.target],
            },
        )
        geometry = add_geometry(cell, relative="1")
        if edge.points:
            converted = [to_drawio_point(graph, point) for point in edge.points]
            add_point(geometry, converted[0], "sourcePoint")
            waypoints = ET.SubElement(geometry, "Array", {"as": "points"})
            for point in converted[1:-1]:
                add_point(waypoints, point)
            add_point(geometry, converted[-1], "targetPoint")

    return model


def parse_uml_classes(path: Path) -> tuple[dict[str, UmlClass], list[tuple[str, str, str, str]]]:
    classes: dict[str, UmlClass] = {}
    relationships: list[tuple[str, str, str, str]] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0

    while index < len(lines):
        line = lines[index].strip()
        if not line or line.startswith("@") or line.startswith("skinparam") or line == "hide circle":
            index += 1
            continue

        block_match = re.match(r"(?:(abstract)\s+)?class\s+(\w+)\s*\{", line)
        single_match = re.match(r"(?:(abstract)\s+)?class\s+(\w+)$", line)
        rel_match = re.match(r"(\w+)\s+([.-]+(?:\|?>|>))\s+(\w+)(?:\s*:\s*(.+))?$", line)

        if block_match:
            is_abstract = bool(block_match.group(1))
            name = block_match.group(2)
            members: list[str] = []
            index += 1
            while index < len(lines) and lines[index].strip() != "}":
                member = lines[index].strip()
                if member:
                    members.append(member)
                index += 1
            classes[name] = UmlClass(name=name, members=members, is_abstract=is_abstract)
        elif single_match:
            is_abstract = bool(single_match.group(1))
            name = single_match.group(2)
            classes[name] = UmlClass(name=name, is_abstract=is_abstract)
        elif rel_match:
            source, arrow, target, label = rel_match.groups()
            relationships.append((source, arrow, target, label or ""))
            classes.setdefault(source, UmlClass(name=source))
            classes.setdefault(target, UmlClass(name=target))

        index += 1

    return classes, relationships


def class_label(uml_class: UmlClass) -> str:
    title = (
        f"<i>{escape(uml_class.name, quote=False)}</i>"
        if uml_class.is_abstract
        else f"<b>{escape(uml_class.name, quote=False)}</b>"
    )
    if not uml_class.members:
        return title
    members = "<br>".join(escape(member, quote=False) for member in uml_class.members)
    return f"{title}<hr><div align=\"left\">{members}</div>"


def class_dimensions(uml_class: UmlClass) -> tuple[float, float]:
    lines = [uml_class.name, *uml_class.members]
    longest = max((len(line) for line in lines), default=12)
    width = min(max(longest * 7.0 + 36.0, 130.0), 310.0)
    height = 38.0 + max(len(uml_class.members), 1) * 18.0
    return width, height


def class_positions(classes: dict[str, UmlClass]) -> dict[str, tuple[float, float]]:
    columns = [
        ["ValueError", "FormulaError", "LexerError", "ParserError"],
        ["TokenType", "Token", "Lexer", "Parser"],
        ["Expression", "Identifier", "BooleanConstant", "UnaryExpression", "BinaryExpression"],
    ]
    positions: dict[str, tuple[float, float]] = {}
    x_values = [40.0, 390.0, 780.0]

    for x, names in zip(x_values, columns, strict=False):
        y = 40.0
        for name in names:
            if name not in classes:
                continue
            positions[name] = (x, y)
            _, height = class_dimensions(classes[name])
            y += height + 34.0

    extra_y = 40.0
    for name in classes:
        if name not in positions:
            positions[name] = (1120.0, extra_y)
            _, height = class_dimensions(classes[name])
            extra_y += height + 34.0

    return positions


def uml_arrow_style(arrow: str) -> str:
    base = "html=1;rounded=0;strokeColor=#000000;fontFamily=Times New Roman;fontSize=11;"
    if "|>" in arrow:
        return base + "endArrow=block;endFill=0;"
    if arrow.startswith(".."):
        return base + "dashed=1;endArrow=classic;endFill=1;"
    return base + "endArrow=classic;endFill=1;"


def class_diagram_to_drawio(path: Path) -> ET.Element:
    classes, relationships = parse_uml_classes(path)
    positions = class_positions(classes)
    model, root = build_mx_graph_model("_class_diagram")
    ids: dict[str, str] = {}

    for name, uml_class in classes.items():
        class_id = xml_id("_class_diagram", "class", name)
        ids[name] = class_id
        x, y = positions[name]
        width, height = class_dimensions(uml_class)
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": class_id,
                "value": class_label(uml_class),
                "style": (
                    "rounded=0;whiteSpace=wrap;html=1;strokeColor=#000000;"
                    "fillColor=#ffffff;fontFamily=Times New Roman;fontSize=12;"
                    "align=center;verticalAlign=top;spacing=8;"
                ),
                "vertex": "1",
                "parent": "1",
            },
        )
        add_geometry(cell, x=x, y=y, width=width, height=height)

    for index, (source, arrow, target, label) in enumerate(relationships, start=1):
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": xml_id("_class_diagram", "relationship", str(index), source, target),
                "value": text_value(label),
                "style": uml_arrow_style(arrow),
                "edge": "1",
                "parent": "1",
                "source": ids[source],
                "target": ids[target],
            },
        )
        add_geometry(cell, relative="1")

    return model


def class_diagram_to_graph(path: Path) -> Graph:
    classes, relationships = parse_uml_classes(path)
    positions = class_positions(classes)
    nodes: list[Node] = []
    edges: list[Edge] = []

    for name, uml_class in classes.items():
        width, height = class_dimensions(uml_class)
        x, y = positions[name]
        label_lines = [name, *uml_class.members]
        nodes.append(
            Node(
                name=name,
                x=(x + width / 2) / SCALE,
                y=(y + height / 2) / SCALE,
                width=width / SCALE,
                height=height / SCALE,
                label="\n".join(label_lines),
                shape="box",
            )
        )

    for source, _arrow, target, label in relationships:
        edges.append(Edge(source=source, target=target, points=[], label=label))

    max_x = max((positions[node.name][0] + class_dimensions(classes[node.name])[0] for node in nodes), default=0)
    max_y = max((positions[node.name][1] + class_dimensions(classes[node.name])[1] for node in nodes), default=0)
    return Graph(
        name="_class_diagram",
        width=(max_x + MARGIN) / SCALE,
        height=(max_y + MARGIN) / SCALE,
        nodes=nodes,
        edges=edges,
    )


def build_all() -> None:
    DRAWIO_DIR.mkdir(exist_ok=True)
    GRAPHML_DIR.mkdir(exist_ok=True)
    pages: list[tuple[str, ET.Element]] = []

    for path in sorted(DIAGRAM_DIR.glob("*.puml")):
        dot_data = read_startdot(path)
        if dot_data is None:
            continue
        output_name, dot_source = dot_data
        graph = parse_dot_json(output_name, run_dot_json(dot_source))
        model = graph_to_drawio(graph)
        pages.append((output_name, model))
        write_drawio(output_name, model, DRAWIO_DIR / f"{output_name}.drawio")
        graph_to_graphml(graph, GRAPHML_DIR / f"{output_name}.graphml")

    class_path = DIAGRAM_DIR / "_class_diagram.puml"
    if class_path.exists():
        model = class_diagram_to_drawio(class_path)
        pages.append(("_class_diagram", model))
        write_drawio("_class_diagram", model, DRAWIO_DIR / "_class_diagram.drawio")
        graph_to_graphml(class_diagram_to_graph(class_path), GRAPHML_DIR / "_class_diagram.graphml")

    write_drawio_file(pages, DRAWIO_DIR / "all_diagrams.drawio")


if __name__ == "__main__":
    build_all()
