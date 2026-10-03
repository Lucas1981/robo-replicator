import math
import re
from dataclasses import dataclass
from xml.etree import ElementTree as ET

from app.services.robot_config import BEZIER_SAMPLES

SVG_NS = "http://www.w3.org/2000/svg"


class SvgParseError(ValueError):
    """Raised when SVG path data cannot be parsed."""


@dataclass(frozen=True)
class ParsedSvg:
    width: float
    height: float
    paths: list[list[tuple[float, float]]]


def parse_svg_paths(svg_bytes: bytes) -> ParsedSvg:
    try:
        root = ET.fromstring(svg_bytes)
    except ET.ParseError as exc:
        raise SvgParseError("Invalid SVG XML.") from exc

    width, height = _viewbox_size(root)
    path_elements = root.findall(f".//{{{SVG_NS}}}path")
    if not path_elements:
        path_elements = root.findall(".//path")

    paths: list[list[tuple[float, float]]] = []
    for element in path_elements:
        path_data = element.get("d")
        if not path_data:
            continue
        points = _path_data_to_polyline(path_data.strip())
        if len(points) >= 2:
            paths.append(points)

    if not paths:
        raise SvgParseError("SVG contains no drawable path elements.")

    return ParsedSvg(width=width, height=height, paths=paths)


def _viewbox_size(root: ET.Element) -> tuple[float, float]:
    viewbox = root.get("viewBox")
    if viewbox:
        parts = [float(value) for value in viewbox.replace(",", " ").split()]
        if len(parts) == 4:
            return parts[2], parts[3]

    width = float(root.get("width", "0"))
    height = float(root.get("height", "0"))
    if width <= 0 or height <= 0:
        raise SvgParseError("SVG is missing a usable viewBox or width/height.")
    return width, height


def _path_data_to_polyline(path_data: str) -> list[tuple[float, float]]:
    tokens = _tokenize_path_data(path_data)
    points: list[tuple[float, float]] = []
    current = (0.0, 0.0)
    subpath_start = (0.0, 0.0)
    index = 0
    active_command = "M"

    while index < len(tokens):
        token = tokens[index]
        if token in "MLCQZmlcqz":
            active_command = token.upper()
            index += 1
            if active_command == "Z":
                if points and points[-1] != subpath_start:
                    points.append(subpath_start)
                current = subpath_start
            continue

        if active_command == "M":
            current, subpath_start, index = _read_point(tokens, index)
            points.append(current)
            active_command = "L"
        elif active_command == "L":
            current, _, index = _read_point(tokens, index)
            points.append(current)
        elif active_command == "C":
            if index + 5 >= len(tokens):
                raise SvgParseError("Incomplete cubic Bézier command in path data.")
            control_1 = (float(tokens[index]), float(tokens[index + 1]))
            control_2 = (float(tokens[index + 2]), float(tokens[index + 3]))
            end = (float(tokens[index + 4]), float(tokens[index + 5]))
            index += 6
            points.extend(_sample_cubic(current, control_1, control_2, end)[1:])
            current = end
        elif active_command == "Q":
            if index + 3 >= len(tokens):
                raise SvgParseError("Incomplete quadratic Bézier command in path data.")
            control = (float(tokens[index]), float(tokens[index + 1]))
            end = (float(tokens[index + 2]), float(tokens[index + 3]))
            index += 4
            points.extend(_sample_quadratic(current, control, end)[1:])
            current = end
        else:
            raise SvgParseError(f"Unsupported SVG path command: {active_command}")

    deduped: list[tuple[float, float]] = []
    for point in points:
        if not deduped or point != deduped[-1]:
            deduped.append(point)
    return deduped


def _tokenize_path_data(path_data: str) -> list[str]:
    return re.findall(r"[MLCQZmlcqz]|-?\d*\.?\d+(?:[eE][-+]?\d+)?", path_data)


def _read_point(
    tokens: list[str], index: int
) -> tuple[tuple[float, float], tuple[float, float], int]:
    if index + 1 >= len(tokens):
        raise SvgParseError("Incomplete coordinate pair in path data.")
    point = (float(tokens[index]), float(tokens[index + 1]))
    return point, point, index + 2


def _sample_cubic(
    start: tuple[float, float],
    control_1: tuple[float, float],
    control_2: tuple[float, float],
    end: tuple[float, float],
) -> list[tuple[float, float]]:
    samples = max(BEZIER_SAMPLES, 2)
    return [_cubic_point(start, control_1, control_2, end, step / (samples - 1)) for step in range(samples)]


def _sample_quadratic(
    start: tuple[float, float],
    control: tuple[float, float],
    end: tuple[float, float],
) -> list[tuple[float, float]]:
    samples = max(BEZIER_SAMPLES, 2)
    return [_quadratic_point(start, control, end, step / (samples - 1)) for step in range(samples)]


def _cubic_point(
    start: tuple[float, float],
    control_1: tuple[float, float],
    control_2: tuple[float, float],
    end: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    u = 1.0 - t
    x = (
        u**3 * start[0]
        + 3 * u**2 * t * control_1[0]
        + 3 * u * t**2 * control_2[0]
        + t**3 * end[0]
    )
    y = (
        u**3 * start[1]
        + 3 * u**2 * t * control_1[1]
        + 3 * u * t**2 * control_2[1]
        + t**3 * end[1]
    )
    return x, y


def _quadratic_point(
    start: tuple[float, float],
    control: tuple[float, float],
    end: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    u = 1.0 - t
    x = u**2 * start[0] + 2 * u * t * control[0] + t**2 * end[0]
    y = u**2 * start[1] + 2 * u * t * control[1] + t**2 * end[1]
    return x, y


def path_length(points: list[tuple[float, float]]) -> float:
    total = 0.0
    for start, end in zip(points, points[1:]):
        total += math.hypot(end[0] - start[0], end[1] - start[1])
    return total
