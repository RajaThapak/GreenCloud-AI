SCHEDULED, RUNNING, RECOVERING = "Scheduled", "Running", "Recovering"
COMPLETED, RECOVERED, FAILED, CANCELLED = "Completed", "Recovered", "Failed", "Cancelled"

ACTIVE = (RUNNING, RECOVERING)                       # the monitor looks at these
TERMINAL = (COMPLETED, RECOVERED, FAILED, CANCELLED)

# why an attempt ended
END_COMPLETED, END_INTERRUPTED, END_LOST = "completed", "interrupted", "lost"
END_FAILED, END_CANCELLED = "failed", "cancelled"
