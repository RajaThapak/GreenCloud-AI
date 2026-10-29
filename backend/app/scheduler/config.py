"""Every tunable number for the scheduler lives here.
Values marked ASSUMPTION are modelling choices: justify each one in your report
and replace them with cited figures where you can."""

MODE_WEIGHTS = {"Cost": (1.0, 0.0), "Balanced": (0.5, 0.5), "Carbon": (0.0, 1.0)}  # (cost, carbon)

DEADLINE_BUFFER = 1.2        # job must fit in duration x 1.2, which leaves time for one retry
MAX_HORIZON_H = 72           # how far ahead a start time may be
START_STEP_H = 1             # spacing between candidate start times

LOST_WORK_CHECKPOINT = 0.10      # ASSUMPTION: share of work redone after an interruption (job checkpoints)
LOST_WORK_NO_CHECKPOINT = 0.50   # ASSUMPTION: same, for jobs that cannot checkpoint
DEFAULT_INTERRUPTION = 0.10      # ASSUMPTION: used when an instance family is not listed below

# ASSUMPTION: chance a Spot run is interrupted. Replace with Spot Instance Advisor bands,
# then with your own run logs once the platform has executed real jobs.
INTERRUPTION_BY_FAMILY = {"t3": 0.05, "m5": 0.07, "c5": 0.08, "r5": 0.07, "g5": 0.12}
LOW_RISK_MAX = 0.08          # chance <= this is labelled Low
MEDIUM_RISK_MAX = 0.15       # chance <= this is labelled Medium, above is High

PUE = 1.2                    # ASSUMPTION: data-centre overhead multiplier
WATTS_PER_VCPU = 2.0         # ASSUMPTION: replace with a cited source (e.g. Cloud Carbon Footprint method)
WATTS_PER_GPU = 150.0        # ASSUMPTION: same
DEFAULT_REGION = "us-east-1" # the "if you ran it now" baseline for carbon savings

LATEST_LOOKBACK_H = 24       # how far back to look for the latest price or carbon reading
PROFILE_DAYS = 7             # history used for the hour-of-day pattern

STALE_CARBON_H = 3
STALE_SPOT_H = 6
