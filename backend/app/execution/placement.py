"""Chooses where to (re)launch by reusing the chunk 4 optimizer on the REMAINING work."""
from __future__ import annotations

from dataclasses import replace

from ..scheduler.candidates import eligible_instances
from ..scheduler.catalog import CATALOG
from ..scheduler.estimator import run_carbon_kg
from ..scheduler.forecast import BaselineForecaster
from ..scheduler.market import load_market
from ..scheduler.models import SchedulerError, WorkloadSpec
from ..scheduler.optimizer import optimize
from .config import RESTART_OVERHEAD_H
from .datatypes import Placement


class OptimizerPlacements:
    """Returns placements in the order to try them: best, alternatives, then a last-resort on-demand."""

    def __init__(self, session):
        self.session = session

    def __call__(self, run, remaining_h: float, purchase_pref: str, now) -> list[Placement]:
        market = load_market(self.session, now)
        if purchase_pref == "On-demand":
            market = replace(market, spot={})           # no Spot data means on-demand pricing is used
        spec = WorkloadSpec(run.workload_name, remaining_h + RESTART_OVERHEAD_H, run.deadline, run.mode,
                            run.min_vcpu, run.min_memory_gb, run.min_gpus, run.allowed_regions, run.checkpointing)
        out: list[Placement] = []
        try:
            r = optimize(spec, market, now)
            for c in [r.best, *r.alternatives]:
                out.append(Placement(c.region, c.instance, c.purchase,
                                     c.cost / spec.duration_h, c.carbon_kg / spec.duration_h))
        except SchedulerError:
            pass                                        # fall through to the last resort
        last = self._last_resort(run, spec, market, now)
        if last and last not in out:
            out.append(last)
        return out

    @staticmethod
    def _last_resort(run, spec, market, now):
        names = {i.name for i in eligible_instances(spec, CATALOG)}
        opts = [(q.price, r, i) for (r, i), q in market.on_demand.items()
                if i in names and (not run.allowed_regions or r in run.allowed_regions)]
        if not opts:
            return None
        price, region, inst = min(opts)
        kg = 0.0
        if region in market.carbon:
            kg = run_carbon_kg(BaselineForecaster(market), region, CATALOG[inst], now, 1.0) or 0.0
        return Placement(region, inst, "On-demand", price, kg)
