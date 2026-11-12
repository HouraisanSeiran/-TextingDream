# -*- coding: utf-8 -*-
"""Run configuration. Integers only, so a seed and a map identity fix the result."""
from dataclasses import asdict, dataclass

from .errors import CivSimError


def _int(name, value, lo, hi):
    if type(value) is not int:
        raise CivSimError("%s 必须是整数" % name)
    if value < lo or value > hi:
        raise CivSimError("%s 必须在 %d…%d 之间（得到 %d）" % (name, lo, hi, value))
    return value


@dataclass(frozen=True)
class CivSimConfig:
    """Deterministic controls for one civilisation run.

    ``seed`` is the civilisation seed. It is independent of the terrain
    ``world_seed``. The map identity is not stored here; the runner pins it
    beside this config in the run manifest.
    """

    seed: int
    start_year: int = 0
    end_year: int = 120
    max_polities: int = 8
    block_cells: int = 16
    min_land_cells: int = 4
    river_radius_m: int = 8000
    coast_scale_m: int = 20_000
    river_weight: int = 3
    coast_weight: int = 2
    slope_weight: int = 4
    highland_weight: int = 350
    climate_weight: int = 1
    distance_weight: int = 80
    base_expand_cost: int = 900
    expand_budget: int = 1600
    found_period: int = 12
    max_founds_per_year: int = 1
    found_jitter: int = 400
    min_capital_hops: int = 3
    war_per_mille: int = 180
    peace_per_mille: int = 220
    conquer_per_mille: int = 420
    max_war_years: int = 15
    max_new_wars_per_year: int = 2
    max_annals: int = 20_000
    # Society layer (dynasty / people / faith)
    society: bool = True
    reign_years: int = 18
    succession_per_mille: int = 80
    usurp_per_mille: int = 120
    appoint_per_mille: int = 40
    convert_per_mille: int = 25

    def __post_init__(self):
        _int("seed", self.seed, -2**63, 2**63 - 1)
        _int("start_year", self.start_year, 0, 1_000_000)
        _int("end_year", self.end_year, 0, 1_000_000)
        if self.end_year < self.start_year:
            raise CivSimError("结束年不能早于起始年")
        if self.end_year - self.start_year > 2000:
            raise CivSimError("起止年跨度不能超过 2000 年")
        _int("max_polities", self.max_polities, 1, 64)
        _int("block_cells", self.block_cells, 1, 256)
        _int("min_land_cells", self.min_land_cells, 1, 1_000_000)
        _int("river_radius_m", self.river_radius_m, 0, 1_000_000)
        _int("coast_scale_m", self.coast_scale_m, 1, 10_000_000)
        for name in (
            "river_weight", "coast_weight", "slope_weight", "highland_weight",
            "climate_weight", "distance_weight", "base_expand_cost", "expand_budget",
        ):
            _int(name, getattr(self, name), -1_000_000_000, 1_000_000_000)
        _int("found_period", self.found_period, 1, 10_000)
        _int("max_founds_per_year", self.max_founds_per_year, 1, 64)
        _int("found_jitter", self.found_jitter, 0, 1_000_000_000)
        _int("min_capital_hops", self.min_capital_hops, 1, 10_000)
        for name in ("war_per_mille", "peace_per_mille", "conquer_per_mille"):
            _int(name, getattr(self, name), 0, 1000)
        _int("max_war_years", self.max_war_years, 1, 10_000)
        _int("max_new_wars_per_year", self.max_new_wars_per_year, 0, 64)
        _int("max_annals", self.max_annals, 1, 200_000)
        if type(self.society) is not bool:
            raise CivSimError("society 必须是布尔值")
        _int("reign_years", self.reign_years, 1, 200)
        for name in ("succession_per_mille", "usurp_per_mille",
                     "appoint_per_mille", "convert_per_mille"):
            _int(name, getattr(self, name), 0, 1000)

    def to_dict(self):
        return asdict(self)
