from pathlib import Path

import gdsfactory as gf

from .params import U2Params
from .u2_block import u2_block

from qm_pic_tech.qm_pic_components.qm_pic_metal_pad import qm_pic_metal_pad


LABEL_LAYER = (201, 0)
PORT_LABEL_LAYER = (200, 0)
METAL_CROSS_SECTION = "xs_M1_strip"
PAD_SIZE = 100
GND_PAD_HEIGHT = 280
GND_PAD_TOP_OFFSET = 180


@gf.cell
def mesh4x4(
    params: U2Params = U2Params(),
    pitch_x: float = 1120,
    pitch_y: float = 200,
) -> gf.Component:
    c = gf.Component("cantilever_4x4_mzi_mesh")

    block = u2_block(params=params)

    # Clements-like 4-mode mesh:
    # column 0: (0,1), (2,3)
    # column 1: (1,2)
    # column 2: (0,1), (2,3)
    # column 3: (1,2)
    placements = [
        (0, 0.5, "U01_a"),
        (0, 2.5, "U23_a"),
        (1, 1.5, "U12_a"),
        (2, 0.5, "U01_b"),
        (2, 2.5, "U23_b"),
        (3, 1.5, "U12_b"),
    ]

    refs = {}

    for col, mode_mid, name in placements:
        r = c << block
        r.move((col * pitch_x, mode_mid * pitch_y))

        refs[name] = r

        c.add_label(
            name,
            position=(col * pitch_x, mode_mid * pitch_y),
            layer=LABEL_LAYER,
        )

    # --- optical port labels ---
    for name, ref in refs.items():
        for p in ref.ports:
            c.add_label(
                f"{name}:{p.name}",
                position=p.center,
                layer=PORT_LABEL_LAYER,
            )

    # --- routing ---
    def route_pairs(pairs, cross_section, radius=30):
        for src_block, src_port, dst_block, dst_port in pairs:
            gf.routing.route_single(
                component=c,
                port1=refs[src_block].ports[src_port],
                port2=refs[dst_block].ports[dst_port],
                cross_section=cross_section,
                radius=radius,
            )

    def place_device_pads(device_name, pad_y, dx=140, x0_override=None):
        x0 = refs[device_name].center[0] if x0_override is None else x0_override
        pad_height = pad.bbox().height()
        gnd_pad_height = gnd_pad.bbox().height()
        gnd_top_y = pad_y + GND_PAD_TOP_OFFSET + 0.5 * pad_height
        gnd_y = gnd_top_y - 0.5 * gnd_pad_height

        pads = {}

        positions = {
            f"{device_name}_es1": (pad, (x0 - dx, pad_y)),
            f"{device_name}_es2": (pad, (x0 + dx, pad_y)),
            f"GND_{device_name}": (gnd_pad, (x0, gnd_y)),
        }

        for pad_name, (pad_component, pos) in positions.items():
            r = c << pad_component
            r.move(pos)
            pads[pad_name] = r
            c.add_label(pad_name, position=r.center, layer=LABEL_LAYER)

        return pads

    route_pairs(
        pairs=[
            ("U23_a", "o4", "U12_a", "o2"),
            ("U01_a", "o4", "U01_b", "o1"),
            ("U12_b", "o1", "U01_b", "o3"),
            ("U23_b", "o2", "U23_a", "o3"),
            ("U01_a", "o3", "U12_a", "o1"),
            ("U01_b", "o2", "U12_a", "o4"),
            ("U23_b", "o1", "U12_a", "o3"),
            ("U23_b", "o4", "U12_b", "o2"),
        ],
        cross_section=params.cross_section,
        radius=30,
    )

    # -------------------------------------------------
    # Electrical pads
    # -------------------------------------------------
    pad = qm_pic_metal_pad(
        width=PAD_SIZE,
        height=PAD_SIZE,
        orientation=270,
    )
    gnd_pad = qm_pic_metal_pad(
        width=PAD_SIZE,
        height=GND_PAD_HEIGHT,
        orientation=270,
    )

    pad_y = c.bbox().top + 250

    pad_refs = {}

    def place_u2_group_pads(upper_device, center_device, lower_device):
        x_upper = refs[upper_device].center[0]
        x_lower = refs[lower_device].center[0]
        x_center = 0.5 * (x_upper + x_lower)

        pad_refs.update(place_device_pads(upper_device, pad_y, dx=140))
        pad_refs.update(
            place_device_pads(
                center_device,
                pad_y,
                dx=140,
                x0_override=x_center,
            )
        )
        pad_refs.update(place_device_pads(lower_device, pad_y, dx=140))

    place_u2_group_pads("U23_a", "U01_a", "U12_a")
    place_u2_group_pads("U23_b", "U01_b", "U12_b")

    def route_signal_bundle(device_name):
        split_y = pad_y - 125

        for port_name in ["es1", "es2"]:
            p1 = refs[device_name].ports[port_name]
            p2 = pad_refs[f"{device_name}_{port_name}"].ports["e1"]

            gf.routing.route_single(
                component=c,
                port1=p1,
                port2=p2,
                cross_section=METAL_CROSS_SECTION,
                radius=10,
                waypoints=[
                    (p1.center[0], split_y),
                    (p2.center[0], split_y),
                ],
            )

    def ground_pad_ports(device_name):
        gnd_ref = pad_refs[f"GND_{device_name}"]
        p_gnd_bottom = gnd_ref.ports["e1"]
        pad_side_y = gnd_ref.center[1]
        pad_half_width = 50.5

        p_gnd_left = gf.Port(
            name=f"{device_name}_gnd_left",
            center=(gnd_ref.center[0] - pad_half_width, pad_side_y),
            width=p_gnd_bottom.width,
            orientation=180,
            layer=p_gnd_bottom.layer,
            port_type="electrical",
        )
        p_gnd_right = gf.Port(
            name=f"{device_name}_gnd_right",
            center=(gnd_ref.center[0] + pad_half_width, pad_side_y),
            width=p_gnd_bottom.width,
            orientation=0,
            layer=p_gnd_bottom.layer,
            port_type="electrical",
        )
        return p_gnd_bottom, p_gnd_left, p_gnd_right, pad_side_y

    def route_ground_bundle(device_name):
        p_gnd_bottom, p_gnd_left, p_gnd_right, pad_side_y = ground_pad_ports(
            device_name
        )

        gf.routing.route_single(
            component=c,
            port1=refs[device_name].ports["eg2"],
            port2=p_gnd_bottom,
            cross_section=METAL_CROSS_SECTION,
            radius=10,
        )

        escape_y = pad_y - 210
        left_outer_x = pad_refs[f"{device_name}_es1"].center[0] - 120
        right_outer_x = pad_refs[f"{device_name}_es2"].center[0] + 120

        gf.routing.route_single(
            component=c,
            port1=refs[device_name].ports["eg1"],
            port2=p_gnd_left,
            cross_section=METAL_CROSS_SECTION,
            radius=10,
            waypoints=[
                (refs[device_name].ports["eg1"].center[0], escape_y),
                (left_outer_x, escape_y),
                (left_outer_x, pad_side_y),
            ],
        )

        gf.routing.route_single(
            component=c,
            port1=refs[device_name].ports["eg3"],
            port2=p_gnd_right,
            cross_section=METAL_CROSS_SECTION,
            radius=10,
            waypoints=[
                (refs[device_name].ports["eg3"].center[0], escape_y),
                (right_outer_x, escape_y),
                (right_outer_x, pad_side_y),
            ],
        )

    def route_u01_bundle(device_name):
        gnd_ref = pad_refs[f"GND_{device_name}"]
        p_gnd_bottom, p_gnd_left, p_gnd_right, pad_side_y = ground_pad_ports(
            device_name
        )
        bundle_x = gnd_ref.center[0]
        bundle_y = refs[device_name].ports["eg2"].center[1] + 175
        split_y = pad_y - 125
        escape_y = pad_y - 210
        bundle_radius = 5
        lane_offsets = {
            "eg1": 32,
            "es1": 16,
            "eg2": 0,
            "es2": -16,
            "eg3": -32,
        }
        turn_offsets = {
            "eg1": -64,
            "es1": -32,
            "eg2": 0,
            "es2": 32,
            "eg3": 64,
        }

        for port_name in ["es1", "es2"]:
            p1 = refs[device_name].ports[port_name]
            p2 = pad_refs[f"{device_name}_{port_name}"].ports["e1"]
            lane_y = bundle_y + lane_offsets[port_name]
            turn_x = bundle_x + turn_offsets[port_name]

            gf.routing.route_single(
                component=c,
                port1=p1,
                port2=p2,
                cross_section=METAL_CROSS_SECTION,
                radius=bundle_radius,
                waypoints=[
                    (p1.center[0], lane_y),
                    (turn_x, lane_y),
                    (turn_x, split_y),
                    (p2.center[0], split_y),
                ],
            )

        p1 = refs[device_name].ports["eg2"]
        gf.routing.route_single(
            component=c,
            port1=p1,
            port2=p_gnd_bottom,
            cross_section=METAL_CROSS_SECTION,
            radius=bundle_radius,
            waypoints=[
                (p1.center[0], bundle_y),
                (bundle_x + turn_offsets["eg2"], bundle_y),
            ],
        )

        left_outer_x = pad_refs[f"{device_name}_es1"].center[0] - 120
        right_outer_x = pad_refs[f"{device_name}_es2"].center[0] + 120

        p1 = refs[device_name].ports["eg1"]
        gf.routing.route_single(
            component=c,
            port1=p1,
            port2=p_gnd_left,
            cross_section=METAL_CROSS_SECTION,
            radius=bundle_radius,
            waypoints=[
                (p1.center[0], bundle_y + lane_offsets["eg1"]),
                (bundle_x + turn_offsets["eg1"], bundle_y + lane_offsets["eg1"]),
                (bundle_x + turn_offsets["eg1"], escape_y),
                (left_outer_x, escape_y),
                (left_outer_x, pad_side_y),
            ],
        )

        p1 = refs[device_name].ports["eg3"]
        gf.routing.route_single(
            component=c,
            port1=p1,
            port2=p_gnd_right,
            cross_section=METAL_CROSS_SECTION,
            radius=bundle_radius,
            waypoints=[
                (p1.center[0], bundle_y + lane_offsets["eg3"]),
                (bundle_x + turn_offsets["eg3"], bundle_y + lane_offsets["eg3"]),
                (bundle_x + turn_offsets["eg3"], escape_y),
                (right_outer_x, escape_y),
                (right_outer_x, pad_side_y),
            ],
        )

    routing_steps = [
        (route_signal_bundle, "U23_a"),
        (route_ground_bundle, "U23_a"),
        (route_u01_bundle, "U01_a"),
        (route_signal_bundle, "U12_a"),
        (route_ground_bundle, "U12_a"),
        (route_signal_bundle, "U23_b"),
        (route_ground_bundle, "U23_b"),
        (route_u01_bundle, "U01_b"),
        (route_signal_bundle, "U12_b"),
        (route_ground_bundle, "U12_b"),
    ]
    for route, device_name in routing_steps:
        route(device_name)

    return c


def main() -> None:
    component = mesh4x4()
    out = Path("gds/cantilever_4x4_mzi_mesh.gds")
    out.parent.mkdir(exist_ok=True)
    component.write_gds(out)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
