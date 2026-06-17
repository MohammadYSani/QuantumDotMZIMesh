import gdsfactory as gf

from .params import U2Params
from .u2_block import u2_block


@gf.cell
def mesh4x4(
    params: U2Params = U2Params(),
    pitch_x: float = 1150,
    pitch_y: float = 300,
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
            if p.port_type == "optical":
                c.add_label(
                    f"{name}:{p.name}",
                    position=p.center,
                    layer=(200, 0),
                )

    # --- routing ---
    gf.routing.route_single(
        component=c,
        port1=refs["U01_a"].ports["o3"],
        port2=refs["U12_a"].ports["o1"],
        cross_section=params.cross_section,
        radius=30,
    )
    return c