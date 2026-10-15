#!/usr/bin/env pvpython
r"""Render selected .vtk or XML unstructured-grid .vtu files to PNG images.

Run with ParaView's Python interpreter (not ordinary Python):
  pvpython visualize_vtk_by_paraview.py --vtkfile "./vtk/*.vtk"
  pvpython visualize_vtk_by_paraview.py --vtkfile ./vtk/a.vtk ./vtk/b.vtk --field S1 \
      --association CELLS --view xy --range 0 100 --output-dir ./images
  pvpython visualize_vtk_by_paraview.py --config visualize_vtk.json

JSON config keys match long option names without "--" (including "output-dir"
and "range"). Example:
  {"vtkfile": ["POST_VISL/*.vtk"], "output-dir": "figures", "field": "DISPLACEMENT",
   "association": "POINTS", "view": "xy", "range": [0, 100], "edges": true,
   "width": 1600, "height": 1200}
CLI options override config values; --no-edges overrides "edges": true.
Relative paths are resolved from the current working directory, as on the CLI.
--vtkfile accepts one or more paths or glob patterns (*, ?, [abc], **).
Quote CLI patterns to expand them in the script. JSON "vtkfile" accepts a
string or a nonempty list of strings. CLI selection replaces JSON selection.
Patterns must match files; directories and unsupported file types are errors.
Matches are sorted per pattern; repeated files are processed only once.

Camera coordinates can be supplied with --camera-position X Y Z and
--camera-focal-point X Y Z, or JSON arrays "camera-position" and
"camera-focal-point". Omit either key (or use null) for automatic adjustment.
By default the camera fits each mesh using --view. With only a focal point,
the fitted camera is translated to retain its direction and distance.
With only a position, the focal point remains at the fitted mesh center.
Explicit coordinates override --view's viewing direction; --view still sets
the preferred up direction. Parallel projection and automatic image scale
are retained.
--camera-view-up AXIS (JSON: "camera-view-up": "z") overrides the preferred
up direction with x, y, z, -x, -y or -z. Omit it or use JSON null to retain
--view's default. Use --camera-view-up=-z for a negative axis on the CLI.
The selected axis is projected onto the image plane; an axis parallel to
the final viewing direction is invalid.
--camera-roll DEGREES (JSON: "camera-roll": 30) rotates the camera up vector
around the position-to-focal-point axis using the right-hand rule, after
automatic positioning, explicit coordinates and camera-view-up are applied.
Default: 0.
Position, focal point and image scale are unchanged.

Images default to <input-parent>/images/<input-stem>.png; existing images are
overwritten. Without --field, geometry is shown in a solid color.
With --output-dir, all images go to that directory. Different inputs that
would produce the same output path are rejected before rendering.
Vectors are colored by magnitude. Color limits are fitted per file unless
--range MIN MAX is supplied, which is recommended for comparing time steps.
In JSON, omit "range" or set it to null to fit each file's data range;
set "range": [MIN, MAX] to use fixed color limits.
--colormap NAME selects a ParaView color preset, e.g. "Cool to Warm" or
"Viridis" (availability depends on the ParaView version). JSON equivalent:
"colormap": "Viridis". Omit it or use null to use Turbo.
Explicit --colormap requires --field. Without --field, solid-color geometry
is retained. Presets are applied before automatic or fixed range scaling.

--representation surface|points|gauss selects surfaces, mesh nodes or stored
quadrature points (default: surface). --point-size PIXELS sets point size
(default: 5). --edges applies only to surface mode. Point coloring requires
--association POINTS. JSON keys: "representation", "point-size".
Gauss mode requires a cell offset array with a VTK quadrature scheme dictionary;
it never guesses an integration rule or substitutes cell centers. Use .vtu
to preserve this metadata. The offset array is selected automatically if unique;
otherwise specify --quadrature-offset NAME (JSON: "quadrature-offset").
Gauss colors use stored quadrature field data mapped to output POINTS, not
cell values or automatically interpolated nodal values. Missing data is an error.
Deformation is applied to the mesh before generating quadrature coordinates.

Use --deform to show deformed geometry: x_display = x + deformation_scale * u.
The displacement must be a three-component POINTS array, selected using
--deformation-field (default: DISPLACEMENT). --deformation-scale defaults to 1.
JSON equivalents: "deform": true, "deformation-field": "DISPLACEMENT",
"deformation-scale": 10. --no-deform overrides "deform": true.
Coloring (--field/--association) remains independent of deformation, and
the automatic camera fits the deformed geometry. Deformation is off by default.

On a headless machine, use a ParaView build with EGL/OSMesa support, or run
under xvfb-run if the installed build requires an X display.
"""

import argparse
import glob
import json
import math
from pathlib import Path
import sys


def config_arguments(path, parser):
    try:
        with path.open(encoding="utf-8") as stream:
            config = json.load(stream)
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error("Cannot read JSON config {}: {}".format(path, exc))
    if not isinstance(config, dict):
        parser.error("JSON config must be an object")
    types = {
        "vtkfile": (str, list), "output-dir": str, "field": str,
        "association": str, "view": str, "width": int, "height": int,
        "range": list, "edges": bool,
        "colormap": str,
        "representation": str, "point-size": (int, float), "quadrature-offset": str,
        "camera-position": list, "camera-focal-point": list,
        "camera-roll": (int, float),
        "camera-view-up": str,
        "deform": bool, "deformation-field": str, "deformation-scale": (int, float),
    }
    arguments = []
    for key, value in config.items():
        if key not in types:
            parser.error("Unknown JSON config key: {}".format(key))
        if key in ("range", "camera-position", "camera-focal-point",
                   "camera-view-up", "colormap", "quadrature-offset") and value is None:
            continue
        expected = types[key]
        allowed = expected if isinstance(expected, tuple) else (expected,)
        if type(value) not in allowed:
            parser.error("JSON config {!r} must be {}".format(
                key, " or ".join(t.__name__ for t in allowed)))
        if key == "vtkfile":
            paths = [value] if isinstance(value, str) else value
            if not paths or any(not isinstance(p, str) or not p.strip() for p in paths):
                parser.error("JSON config 'vtkfile' must contain nonempty path strings")
            arguments.append("--vtkfile")
            arguments.extend(paths)
        elif key in ("edges", "deform"):
            arguments.append("--" + key if value else "--no-" + key)
        elif types[key] is list:
            size = 2 if key == "range" else 3
            if len(value) != size or any(type(v) not in (int, float) for v in value):
                parser.error("JSON config {!r} must be an array of {} numbers".format(
                    key, size))
            arguments.append("--" + key)
            arguments.extend(str(v) for v in value)
        else:
            arguments.append("--{}={}".format(key, value))
    return arguments


def parse_arguments(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument("--config", type=Path)
    config_args, _ = config_parser.parse_known_args(argv)
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[config_parser],
    )
    parser.add_argument("--vtkfile", required=True, nargs="+", metavar="PATH",
                        help="One or more .vtk/.vtu paths or glob patterns")
    parser.add_argument("--output-dir", type=Path, help="Default: <input-parent>/images")
    parser.add_argument("--field", help="Scalar/vector array name, e.g. S1 or DISPLACEMENT")
    parser.add_argument("--colormap", metavar="NAME",
                        help="ParaView color preset name (default: Turbo)")
    parser.add_argument("--association", choices=("POINTS", "CELLS"), default="POINTS")
    parser.add_argument("--representation", choices=("surface", "points", "gauss"),
                        default="surface", help="Geometry display mode (default: surface)")
    parser.add_argument("--point-size", type=float, default=5.0, metavar="PIXELS",
                        help="Point size in pixels (default: 5)")
    parser.add_argument("--quadrature-offset", metavar="NAME",
                        help="Cell offset array carrying a stored quadrature dictionary")
    parser.add_argument("--deform", action="store_true", help="Show deformed geometry")
    parser.add_argument("--no-deform", dest="deform", action="store_false",
                        help="Show undeformed geometry, overriding the JSON config")
    parser.add_argument("--deformation-field", default="DISPLACEMENT",
                        help="Three-component POINTS displacement array (default: DISPLACEMENT)")
    parser.add_argument("--deformation-scale", type=float, default=1.0,
                        help="Displacement multiplier (default: 1)")
    parser.add_argument("--view", choices=("iso", "xy", "xz", "yz"), default="iso")
    parser.add_argument("--camera-position", nargs=3, type=float, metavar=("X", "Y", "Z"),
                        help="Camera position in world coordinates; default: automatic")
    parser.add_argument("--camera-focal-point", nargs=3, type=float,
                        metavar=("X", "Y", "Z"),
                        help="Camera focal point in world coordinates; default: mesh center")
    parser.add_argument("--camera-roll", type=float, default=0.0, metavar="DEGREES",
                        help="Rotation about the viewing axis in degrees (default: 0)")
    parser.add_argument("--camera-view-up", choices=("x", "y", "z", "-x", "-y", "-z"),
                        help="World axis pointing up before camera-roll; default: from --view")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=1200)
    parser.add_argument("--range", dest="color_range", nargs=2, type=float,
                        metavar=("MIN", "MAX"),
                        help="Fixed color limits for all images; default: fit each file")
    parser.add_argument("--edges", dest="edges", action="store_true", help="Show mesh edges")
    parser.add_argument("--no-edges", dest="edges", action="store_false",
                        help="Hide mesh edges, overriding the JSON config")
    parser.set_defaults(edges=False, deform=False)
    defaults = config_arguments(config_args.config, parser) if config_args.config else []
    args = parser.parse_args(defaults + argv)
    if args.colormap is not None:
        if not args.colormap.strip():
            parser.error("--colormap must not be empty")
        if not args.field:
            parser.error("--colormap requires --field")
    args.colormap = args.colormap or "Turbo"
    if not math.isfinite(args.point_size) or args.point_size <= 0:
        parser.error("--point-size must be finite and positive")
    if args.representation != "surface" and args.field and args.association != "POINTS":
        parser.error("Point and Gauss coloring require --association POINTS")
    if args.quadrature_offset is not None:
        if not args.quadrature_offset.strip():
            parser.error("--quadrature-offset must not be empty")
        if args.representation != "gauss":
            parser.error("--quadrature-offset requires --representation gauss")
    if any(not path.strip() for path in args.vtkfile):
        parser.error("--vtkfile requires nonempty paths")
    if args.width <= 0 or args.height <= 0:
        parser.error("--width and --height must be positive")
    if not math.isfinite(args.deformation_scale):
        parser.error("--deformation-scale must be finite")
    if not math.isfinite(args.camera_roll):
        parser.error("--camera-roll must be finite")
    if not args.deformation_field.strip():
        parser.error("--deformation-field must not be empty")
    for name in ("camera_position", "camera_focal_point"):
        coordinates = getattr(args, name)
        if coordinates is not None and not all(math.isfinite(v) for v in coordinates):
            parser.error("--{} requires finite coordinates".format(name.replace("_", "-")))
    if (args.camera_position is not None
            and args.camera_position == args.camera_focal_point):
        parser.error("Camera position and focal point must be different")
    if args.color_range is not None:
        low, high = args.color_range
        if not all(math.isfinite(v) for v in (low, high)) or low >= high:
            parser.error("--range requires finite MIN < MAX")
        if not args.field:
            parser.error("--range requires --field")
    return args


def get_vtk_files(patterns, output_dir=None):
    files = []
    seen = set()
    outputs = {}
    for pattern in patterns:
        literal = Path(pattern)
        matches = [literal] if literal.is_file() else [
            Path(path) for path in sorted(glob.glob(pattern, recursive=True))]
        if not matches:
            raise ValueError("No VTK files matched: {}".format(pattern))
        for path in matches:
            if not path.is_file() or path.suffix.lower() not in (".vtk", ".vtu"):
                raise ValueError("Expected a .vtk or .vtu file: {}".format(path))
            resolved = path.resolve()
            if resolved in seen:
                continue
            destination = ((output_dir if output_dir is not None else path.parent / "images")
                           / (path.stem + ".png")).resolve()
            if destination in outputs:
                raise ValueError("VTK files would produce duplicate PNG {}: {} and {}".format(
                    destination, outputs[destination], path))
            seen.add(resolved)
            outputs[destination] = path
            files.append(path)
    if not files:
        raise ValueError("No .vtk files selected")
    return files


def configure_camera(parav, view, args):
    directions = {
        "iso": ([1, 1, 1], [0, 0, 1]),
        "xy": ([0, 0, 1], [0, 1, 0]),
        "xz": ([0, -1, 0], [0, 0, 1]),
        "yz": ([1, 0, 0], [0, 0, 1]),
    }
    position, up = directions[args.view]
    view.CameraFocalPoint = [0, 0, 0]
    view.CameraPosition = position
    view.CameraViewUp = up
    view.CameraParallelProjection = 1
    parav.ResetCamera(view)
    if args.camera_focal_point is not None:
        if args.camera_position is None:
            view.CameraPosition = [
                p + target - original for p, target, original in zip(
                    view.CameraPosition, args.camera_focal_point, view.CameraFocalPoint)
            ]
        view.CameraFocalPoint = args.camera_focal_point
    if args.camera_position is not None:
        view.CameraPosition = args.camera_position
    direction = [f - p for f, p in zip(view.CameraFocalPoint, view.CameraPosition)]
    length = math.hypot(math.hypot(direction[0], direction[1]), direction[2])
    if length == 0 or not math.isfinite(length):
        raise ValueError("Camera position and focal point must define a finite nonzero direction")
    direction = [v / length for v in direction]
    if args.camera_view_up is not None:
        axes = {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}
        axis = args.camera_view_up
        sign = -1 if axis.startswith("-") else 1
        up = [sign * v for v in axes[axis.lstrip("-")]]
        if abs(sum(d * u for d, u in zip(direction, up))) >= 1 - 1e-12:
            raise ValueError("--camera-view-up must not be parallel to the viewing direction")
        view.CameraViewUp = up
    elif abs(sum(d * u for d, u in zip(direction, up))) > 0.999:
        view.CameraViewUp = min(
            ([1, 0, 0], [0, 1, 0], [0, 0, 1]),
            key=lambda axis: abs(sum(d * u for d, u in zip(direction, axis))),
        )
    if args.camera_roll % 360 != 0:
        angle = math.radians(args.camera_roll % 360)
        cosine, sine = math.cos(angle), math.sin(angle)
        up = list(view.CameraViewUp)
        dot = sum(d * u for d, u in zip(direction, up))
        cross = [
            direction[1] * up[2] - direction[2] * up[1],
            direction[2] * up[0] - direction[0] * up[2],
            direction[0] * up[1] - direction[1] * up[0],
        ]
        # Rodrigues' formula rotates up without moving either end of the viewing axis.
        view.CameraViewUp = [
            u * cosine + c * sine + d * dot * (1 - cosine)
            for u, c, d in zip(up, cross, direction)
        ]


def render_file(parav, vtk_file, output_file, args):
    parav._DisableFirstRenderCameraReset()
    if vtk_file.suffix.lower() == ".vtu":
        reader = parav.XMLUnstructuredGridReader(FileName=[str(vtk_file.resolve())])
    else:
        reader = parav.LegacyVTKReader(FileNames=[str(vtk_file.resolve())])
    view = None
    warped = None
    quadrature = None
    try:
        reader.UpdatePipeline()
        if reader.GetDataInformation().GetNumberOfPoints() == 0:
            raise ValueError("No points were read from {}".format(vtk_file))
        source = reader
        if args.deform:
            if args.deformation_field not in reader.PointData.keys():
                raise ValueError(
                    "{}: displacement field {!r} not found in POINTS; available: {}".format(
                        vtk_file, args.deformation_field, ", ".join(reader.PointData.keys()))
                )
            if reader.PointData[args.deformation_field].GetNumberOfComponents() != 3:
                raise ValueError("{}: displacement field {!r} must have 3 components".format(
                    vtk_file, args.deformation_field))
            warped = parav.WarpByVector(Input=reader)
            warped.Vectors = ["POINTS", args.deformation_field]
            warped.ScaleFactor = args.deformation_scale
            warped.UpdatePipeline()
            source = warped

        if args.representation == "gauss":
            quadrature = parav.QuadraturePointsGenerator(Input=source)
            schemes = list(quadrature.QuadratureSchemeDefinition.Available)
            if not schemes:
                raise ValueError(
                    "{}: no stored quadrature scheme dictionary/offset array; "
                    "true Gauss points cannot be generated from cell types alone".format(vtk_file))
            offset = args.quadrature_offset
            if offset is None:
                if len(schemes) != 1:
                    raise ValueError("Multiple quadrature schemes; specify --quadrature-offset: "
                                     + ", ".join(schemes))
                offset = schemes[0]
            if offset not in schemes:
                raise ValueError("Quadrature offset {!r} unavailable; available: {}".format(
                    offset, ", ".join(schemes)))
            quadrature.QuadratureSchemeDefinition = ["CELLS", offset]
            quadrature.UpdatePipeline()
            if quadrature.GetDataInformation().GetNumberOfPoints() == 0:
                raise ValueError("{}: no Gauss points were generated".format(vtk_file))
            source = quadrature

        if args.field:
            arrays = source.PointData if args.association == "POINTS" else source.CellData
            if args.field not in arrays.keys():
                raise ValueError(
                    "{}: field {!r} not found in {} for {}; available: {}".format(
                        vtk_file, args.field, args.association,
                        args.representation, ", ".join(arrays.keys())
                    )
                )

        view = parav.CreateView("RenderView")
        view.ViewSize = [args.width, args.height]
        view.UseColorPaletteForBackground = 0
        view.Background = [1.0, 1.0, 1.0]
        view.OrientationAxesVisibility = 1
        display = parav.Show(source, view)
        if args.representation == "surface":
            display.Representation = "Surface With Edges" if args.edges else "Surface"
        else:
            display.Representation = "Points"
            display.PointSize = args.point_size
        if args.field:
            parav.ColorBy(display, (args.association, args.field))
            lookup = parav.GetColorTransferFunction(args.field)
            if args.colormap is not None and not lookup.ApplyPreset(args.colormap, True):
                raise ValueError("Unknown or unavailable ParaView colormap: {!r}".format(
                    args.colormap))
            lookup.VectorMode = "Magnitude"
            lookup.AutomaticRescaleRangeMode = "Never"
            if args.color_range is None:
                display.RescaleTransferFunctionToDataRange(False, True)
            else:
                lookup.RescaleTransferFunction(*args.color_range)
            display.SetScalarBarVisibility(view, True)
            scalar_bar = parav.GetScalarBar(lookup, view)
            scalar_bar.TitleColor = [0.0, 0.0, 0.0]
            scalar_bar.LabelColor = [0.0, 0.0, 0.0]
        else:
            parav.ColorBy(display, None)
            display.DiffuseColor = [0.7, 0.75, 0.85]

        configure_camera(parav, view, args)
        parav.Render(view)
        parav.SaveScreenshot(str(output_file), view,
                             ImageResolution=[args.width, args.height])
        if not output_file.is_file() or output_file.stat().st_size == 0:
            raise RuntimeError("ParaView did not save an image: {}".format(output_file))
    finally:
        if view is not None:
            parav.Delete(view)
        if quadrature is not None:
            parav.Delete(quadrature)
        if warped is not None:
            parav.Delete(warped)
        parav.Delete(reader)


def main(argv=None):
    args = parse_arguments(argv)
    files = get_vtk_files(args.vtkfile, args.output_dir)
    try:
        import paraview.simple as parav
    except ImportError as exc:
        raise RuntimeError(
            "ParaView Python modules are unavailable. Run this script with pvpython."
        ) from exc
    for vtk_file in files:
        output_dir = args.output_dir or vtk_file.parent / "images"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / (vtk_file.stem + ".png")
        render_file(parav, vtk_file, output_file, args)
        print("Saved: {}".format(output_file), flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        sys.exit(1)
