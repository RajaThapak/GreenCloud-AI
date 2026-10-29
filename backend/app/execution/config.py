"""Recovery settings. ASSUMPTION marks a modelling choice to justify in your report."""
MAX_SPOT_RETRIES = 2        # Spot relaunches allowed after interruptions, then switch to on-demand
MAX_ATTEMPTS = 4            # total launches per run before giving up
MAX_LAUNCH_FAILURES = 6     # consecutive monitor ticks with no capacity anywhere before failing
RESTART_OVERHEAD_H = 0.1    # ASSUMPTION: boot + image pull + checkpoint load per relaunch (6 minutes)
HEARTBEAT_TIMEOUT_MIN = 10  # a running instance silent this long is treated as lost
REAPER_GRACE_MIN = 5        # never reap an instance younger than this (its DB row may not exist yet)
