import gdsfactory as gf

from .params import U2Params
from .u2_block import u2_block

from qm_pic_tech.qm_pic_components.qm_pic_metal_pad import qm_pic_metal_pad

LEFT_GROUP = ["U23_a", "U01_a", "U12_a"]

LEFT_SIGNALS = [
    ("U23_a", "es1"),
    ("U23_a", "es2"),
    ("U12_a", "es1"),
    ("U12_a", "es2"),
]

LEFT_GROUNDS = [
    ("U23_a", "eg1"), ("U23_a", "eg2"), ("U23_a", "eg3"),
    ("U01_a", "eg1"), ("U01_a", "eg2"), ("U01_a", "eg3"),
    ("U12_a", "eg1"), ("U12_a", "eg2"), ("U12_a", "eg3"),
]

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
            layer=(201, 0),
        )

    # --- optical port labels ---
    for name, ref in refs.items():
        for p in ref.ports:
#            if p.port_type == "optical":
                c.add_label(
                    f"{name}:{p.name}",
                    position=p.center,
                    layer=(200, 0),
                )

    
        # --- routing ---
    def route_pairs(c, refs, pairs, cross_section, radius=30):
        for src_block, src_port, dst_block, dst_port in pairs:
            gf.routing.route_single(
                component=c,
                port1=refs[src_block].ports[src_port],
                port2=refs[dst_block].ports[dst_port],
                cross_section=cross_section,
                radius=radius,
            )

    def place_device_pads(c, refs, pad, device_name, pad_y, dx=140, gnd_extra_y=180, x0_override=None):
        x0 = refs[device_name].center[0] if x0_override is None else x0_override

        pads = {}

        positions = {
            f"{device_name}_es1": (x0 - dx, pad_y),
            f"{device_name}_es2": (x0 + dx, pad_y),
            f"GND_{device_name}": (x0, pad_y + gnd_extra_y),
        }

        for pad_name, pos in positions.items():
            r = c << pad
            r.move(pos)
            pads[pad_name] = r
            c.add_label(pad_name, position=r.center, layer=(201, 0))

        return pads
    
    route_pairs(
        c,
        refs,
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
    # Left-group electrical pads
    # -------------------------------------------------
    pad = qm_pic_metal_pad(
        width=100,
        height=100,
        orientation=270,
    )

    pad_y = c.bbox().top + 250

    left_pad_refs = {}

    x_dev1 = refs["U23_a"].center[0]
    x_dev3 = refs["U12_a"].center[0]
    x_dev2 = 0.5 * (x_dev1 + x_dev3)

    left_pad_refs.update(place_device_pads(c, refs, pad, "U23_a", pad_y, dx=140))
    left_pad_refs.update(place_device_pads(c, refs, pad, "U01_a", pad_y, dx=140, x0_override=x_dev2))
    left_pad_refs.update(place_device_pads(c, refs, pad, "U12_a", pad_y, dx=140))

    # Shared U01_a routing controls
    u01_turn_x = left_pad_refs["GND_U01_a"].center[0]
    u01_turn_y = pad_y - 600

    # -------------------------------------------------
    # Custom U12_a ground routing around signal pads
    # -------------------------------------------------
    gnd_ref = left_pad_refs["GND_U12_a"]

    p_eg1 = refs["U12_a"].ports["eg1"]
    p_eg2 = refs["U12_a"].ports["eg2"]
    p_eg3 = refs["U12_a"].ports["eg3"]
    p_gnd = gnd_ref.ports["e1"]

    gnd_lane_y = pad_y + 100
    left_escape_x = p_gnd.center[0] - 250
    right_escape_x = p_gnd.center[0] + 250

    gf.routing.route_single(
        component=c,
        port1=p_eg2,
        port2=p_gnd,
        cross_section="xs_M1_strip",
        radius=10,
        waypoints=[
            (p_eg2.center[0], gnd_lane_y - 50),
            (u01_turn_x, gnd_lane_y - 50),
            (u01_turn_x, p_gnd.center[1] - 80),
            (p_gnd.center[0], p_gnd.center[1] - 80),
        ],
    )

    gf.routing.route_single(
        component=c,
        port1=p_eg1,
        port2=p_gnd,
        cross_section="xs_M1_strip",
        radius=10,
        # left ground
        waypoints=[
            (p_eg1.center[0], gnd_lane_y - 100),
            (u01_turn_x, gnd_lane_y - 100),
            (left_escape_x, gnd_lane_y - 100),
            (left_escape_x, p_gnd.center[1] - 80),
            (p_gnd.center[0], p_gnd.center[1] - 80),
        ],
    )

    gf.routing.route_single(
        component=c,
        port1=p_eg3,
        port2=p_gnd,
        cross_section="xs_M1_strip",
        radius=10,
        # right ground
        waypoints=[
            (p_eg3.center[0], gnd_lane_y - 150),
            (u01_turn_x, gnd_lane_y - 150),
            (right_escape_x, gnd_lane_y - 150),
            (right_escape_x, p_gnd.center[1] - 80),
            (p_gnd.center[0], p_gnd.center[1] - 80),
        ],
    )

    # -------------------------------------------------
    # Custom U23_a ground routing around signal pads
    # -------------------------------------------------
    gnd_ref = left_pad_refs["GND_U23_a"]

    p_eg1 = refs["U23_a"].ports["eg1"]
    p_eg2 = refs["U23_a"].ports["eg2"]
    p_eg3 = refs["U23_a"].ports["eg3"]
    p_gnd = gnd_ref.ports["e1"]

    gnd_lane_y = pad_y + 150
    left_escape_x = p_gnd.center[0] - 250
    right_escape_x = p_gnd.center[0] + 250

    gf.routing.route_single(
        component=c,
        port1=p_eg2,
        port2=p_gnd,
        cross_section="xs_M1_strip",
        radius=10,
        waypoints=[
            (p_eg2.center[0], gnd_lane_y),
            (p_gnd.center[0], gnd_lane_y),
        ],
    )

    gf.routing.route_single(
        component=c,
        port1=p_eg1,
        port2=p_gnd,
        cross_section="xs_M1_strip",
        radius=10,
        waypoints=[
            (p_eg1.center[0], gnd_lane_y - 250),
            (left_escape_x, gnd_lane_y - 250),
            (left_escape_x, gnd_lane_y),
            (p_gnd.center[0], gnd_lane_y),
        ],
    )

    gf.routing.route_single(
        component=c,
        port1=p_eg3,
        port2=p_gnd,
        cross_section="xs_M1_strip",
        radius=10,
        waypoints=[
            (p_eg3.center[0], gnd_lane_y - 250),
            (right_escape_x, gnd_lane_y - 250),
            (right_escape_x, gnd_lane_y),
            (p_gnd.center[0], gnd_lane_y),
        ],
    )

    # -------------------------------------------------
    # Custom U01_a signal routing to middle pad cluster
    # -------------------------------------------------

    for i, port_name in enumerate(["es1", "es2"]):
        p1 = refs["U01_a"].ports[port_name]
        p2 = left_pad_refs[f"U01_a_{port_name}"].ports["e1"]

        lane_y = u01_turn_y - i * 25

        gf.routing.route_single(
            component=c,
            port1=p1,
            port2=p2,
            cross_section="xs_M1_strip",
            radius=10,
            waypoints=[
                (p1.center[0], lane_y),
                (u01_turn_x, lane_y),
                (u01_turn_x, p2.center[1] - 60),
                (p2.center[0], p2.center[1] - 60),
            ],
        )
    # -------------------------------------------------
    # Custom U01_a ground routing to middle GND pad
    # -------------------------------------------------
    gnd_ref = left_pad_refs["GND_U01_a"]

    p_eg1 = refs["U01_a"].ports["eg1"]
    p_eg2 = refs["U01_a"].ports["eg2"]
    p_eg3 = refs["U01_a"].ports["eg3"]
    p_gnd = gnd_ref.ports["e1"]

    # shared controls for U01_a GND bundle
    u01_turn_x = left_pad_refs["GND_U01_a"].center[0]
    gnd_lane_y = u01_turn_y

    left_escape_x = p_gnd.center[0] - 250
    right_escape_x = p_gnd.center[0] + 250

    # center ground
    gf.routing.route_single(
        component=c,
        port1=p_eg2,
        port2=p_gnd,
        cross_section="xs_M1_strip",
        radius=10,
        waypoints=[
            (p_eg2.center[0], gnd_lane_y),
            (p_gnd.center[0], gnd_lane_y),
        ]
    )

    # left ground
    gf.routing.route_single(
        component=c,
        port1=p_eg1,
        port2=p_gnd,
        cross_section="xs_M1_strip",
        radius=10,
        waypoints=[
            (p_eg1.center[0], gnd_lane_y - 250),
            (left_escape_x, gnd_lane_y - 250),
            (left_escape_x, gnd_lane_y),
            (p_gnd.center[0], gnd_lane_y),
        ]
    )

    # right ground
    gf.routing.route_single(
        component=c,
        port1=p_eg3,
        port2=p_gnd,
        cross_section="xs_M1_strip",
        radius=10,
        waypoints=[
            (p_eg3.center[0], gnd_lane_y - 250),
            (right_escape_x, gnd_lane_y - 250),
            (right_escape_x, gnd_lane_y),
            (p_gnd.center[0], gnd_lane_y),
        ]
    )

    return c