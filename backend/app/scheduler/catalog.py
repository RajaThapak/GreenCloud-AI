"""Instance sizes (published AWS specs). Add a type here AND to INSTANCE_TYPES in collectors/config.py."""
from .models import InstanceSpec

CATALOG = {
    s.name: s
    for s in [
        InstanceSpec("t3.large", 2, 8),
        InstanceSpec("m5.xlarge", 4, 16),
        InstanceSpec("c5.2xlarge", 8, 16),
        InstanceSpec("r5.xlarge", 4, 32),
        InstanceSpec("g5.xlarge", 4, 16, gpus=1),
        InstanceSpec("g5.2xlarge", 8, 32, gpus=1),
    ]
}
