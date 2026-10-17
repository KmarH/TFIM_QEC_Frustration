"""Plan / quote / run an H2 run group at the tier set in config.py (hardware.nexus_tier).

  .venv/bin/python -I scripts/run_h2_nexus.py --group bare-2x2-step1 --shots 1000     # DRY RUN
  .venv/bin/python -I scripts/run_h2_nexus.py --group G1 --tier sc                    # free quote
  .venv/bin/python -I scripts/run_h2_nexus.py --group G1 --approval "<token>"         # emulator tier,
                                                                                      # only if config says so

Dry run by default. The emulator (which spends HQC) is reachable only by editing config and passing
the per-run approval token; see docs/nexus_toggle.md and src/h2_driver.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.h2_driver import cli  # noqa: E402

if __name__ == "__main__":
    sys.exit(cli())
