import os

# Env variables have precedence over Python configs in ScoutConfig.
# Unset all Scout env variables to prevent interference with tests.

for key in os.environ.keys():
    if key.startswith("SCOUT_"):
        del os.environ[key]
