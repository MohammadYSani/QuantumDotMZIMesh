import gdsfactory as gf

from qm_pic_tech import get_qm_pic_pdk
from qm_pic_tech.qm_pic_components.qm_pic_doubleCMZI import qm_pic_doubleCMZI

try:
    from .params import U2Params
except ImportError:
    from params import U2Params


@gf.cell
def u2_block(params: U2Params = U2Params()) -> gf.Component:
    pdk = get_qm_pic_pdk()
    pdk.activate()

    return qm_pic_doubleCMZI(
        Rbend90=params.Rbend90,
        cmod_width=params.cmod_width,
        cmod_overhang=params.cmod_overhang,
        cmod_NL=params.cmod_NL,
        push_pull=params.push_pull,
        low_loss=params.low_loss,
        routing_direction=params.routing_direction,
        cross_section=params.cross_section,
    )
