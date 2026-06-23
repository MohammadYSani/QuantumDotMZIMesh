from dataclasses import dataclass


@dataclass(frozen=True)
class U2Params:
    cmod_width: float = 350
    cmod_overhang: float = 120
    cmod_NL: int = 13
    Rbend90: float = 20
    push_pull: bool = True
    low_loss: bool = True
    routing_direction: str = "up"
    cross_section: str = "xs_620"  # singleCMZI currently supports xs_620/xs_737
