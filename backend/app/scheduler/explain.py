from __future__ import annotations

from .config import DEFAULT_REGION


def fmt_t(d) -> str:
    return d.strftime("%a %d %b %H:%M UTC")


def explain(spec, best, alts, all_cands, on_demand_cost, run_now_carbon) -> list[str]:
    out = []
    # cost
    if best.purchase == "On-demand":
        out.append(f"Estimated cost is ${best.cost:.2f} on an on-demand instance.")
    else:
        pct = round(100 * (1 - best.cost / on_demand_cost)) if on_demand_cost else 0
        out.append(f"Estimated cost is ${best.cost:.2f}, {pct}% below the on-demand price of ${on_demand_cost:.2f} in {best.region}."
                   if pct > 0 else f"Estimated cost is ${best.cost:.2f}.")
    # carbon
    pct = round(100 * (1 - best.carbon_kg / run_now_carbon)) if run_now_carbon else 0
    out.append(f"Estimated emissions are {best.carbon_kg:.1f} kg CO2, {pct}% below running now in {DEFAULT_REGION} ({run_now_carbon:.1f} kg)."
               if pct > 0 else f"Estimated emissions are {best.carbon_kg:.1f} kg CO2.")
    # region comparison
    pool = [best] + list(alts)
    if len(pool) > 1:
        cheapest = min(pool, key=lambda c: c.cost)
        cleanest = min(pool, key=lambda c: c.carbon_kg)
        n = len(pool)
        if cleanest is best and spec.mode != "Cost":
            out.append(f"{best.region} has the lowest estimated emissions of the {n} regions that can run your job.")
        if cheapest is best and spec.mode != "Carbon":
            out.append(f"{best.region} has the lowest estimated cost of the {n} regions that can run your job.")
        if cheapest is not best:
            out.append(f"{cheapest.region} would cost ${best.cost - cheapest.cost:.2f} less but emit {cheapest.carbon_kg - best.carbon_kg:.1f} kg more CO2.")
        if cleanest is not best and cleanest is not cheapest:
            out.append(f"{cleanest.region} would emit {best.carbon_kg - cleanest.carbon_kg:.1f} kg less but cost ${cleanest.cost - best.cost:.2f} more.")
    # timing
    same = [c for c in all_cands if (c.region, c.instance, c.purchase) == (best.region, best.instance, best.purchase)]
    earliest = min(same, key=lambda c: c.start)
    if best.start > earliest.start:
        saved_cost, saved_carbon = earliest.cost - best.cost, earliest.carbon_kg - best.carbon_kg
        parts = []
        if saved_cost > 0.005:
            parts.append(f"${saved_cost:.2f}")
        if saved_carbon > 0.05:
            parts.append(f"{saved_carbon:.1f} kg CO2")
        if parts:
            out.append(f"Starting at {fmt_t(best.start)} instead of now saves about {' and '.join(parts)}, based on typical hourly patterns.")
    # deadline and risk
    slack = (spec.deadline - best.finish).total_seconds() / 3600
    out.append(f"It is expected to finish {fmt_t(best.finish)}, {slack:.1f} hours before your deadline.")
    if best.purchase == "On-demand":
        out.append("On-demand instances are not interrupted.")
    elif spec.checkpointing:
        out.append(f"Interruption risk is {best.risk_label.lower()}. If the job is interrupted, it resumes from its last checkpoint.")
    else:
        out.append(f"Interruption risk is {best.risk_label.lower()} and this job cannot checkpoint, so an interruption means restarting it.")
    return out
