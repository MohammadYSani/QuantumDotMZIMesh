from pathlib import Path

from cantilever_mzi_mesh.mesh4x4 import mesh4x4
from cantilever_mzi_mesh.params import U2Params
from cantilever_mzi_mesh.u2_block import u2_block



def main() -> None:
    params = U2Params(
        cmod_width=350,
        cmod_overhang=120,
        cmod_NL=13,
        cross_section="xs_620",
        push_pull=True,
        low_loss=True,
    )

    c = mesh4x4(params=params)

    out = Path("gds/cantilever_4x4_mzi_mesh.gds")
    out.parent.mkdir(exist_ok=True)

    c.write_gds(out)
    c.show()

    block = u2_block()


    for p in block.ports:
        print(p)

    print(f"Saved {out}")


if __name__ == "__main__":
    main()