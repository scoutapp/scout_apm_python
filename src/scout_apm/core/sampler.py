# coding=utf-8

import logging
import random
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class Sampler:
    """
    Handles sampling decision logic for Scout APM.

    This class encapsulates all sampling-related functionality including:
    - Loading and managing sampling configuration
    - Pattern matching for operations (endpoints and jobs)
    - Making sampling decisions based on operation type and patterns
    """

    # Constants for operation type detection
    CONTROLLER_PREFIX = "Controller/"
    JOB_PREFIX = "Job/"

    def __init__(self, config):
        """
        Initialize sampler with Scout configuration.

        Args:
            config: ScoutConfig instance containing sampling configuration
        """
        self.config = config
        self.sample_rate = config.value("sample_rate")
        self.sample_endpoints = config.value("sample_endpoints")
        self.sample_jobs = config.value("sample_jobs")
        self.ignore_endpoints = set(config.value("ignore_endpoints"))
        self.ignore_jobs = set(config.value("ignore_jobs"))
        self.endpoint_sample_rate = config.value("endpoint_sample_rate")
        self.job_sample_rate = config.value("job_sample_rate")

    def _any_sampling(self):
        """
        Check if any sampling is enabled.

        Returns:
            Boolean indicating if any sampling is enabled
        """
        return (
            self.sample_rate < 100
            or self.sample_endpoints
            or self.sample_jobs
            or self.ignore_endpoints
            or self.ignore_jobs
            or self.endpoint_sample_rate is not None
            or self.job_sample_rate is not None
        )

    def _find_matching_rate(
        self, name: str, patterns: Dict[str, float]
    ) -> Optional[str]:
        """
        Finds the matching sample rate for a given operation name.

        Args:
            name: The operation name to match
            patterns: Dictionary of pattern to sample rate mappings

        Returns:
            The sample rate for the matching pattern or None if no match found
        """

        for pattern, rate in patterns.items():
            if name.startswith(pattern):
                return rate
        return None

    def _get_operation_type_and_name(
        self, operation: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Determines if an operation is an endpoint or job and extracts its name.

        Args:
            operation: The full operation string (e.g. "Controller/users/show")

        Returns:
            Tuple of (type, name) where type is either 'endpoint' or 'job',
            and name is the operation name without the prefix
        """
        if operation.startswith(self.CONTROLLER_PREFIX):
            return "endpoint", operation[len(self.CONTROLLER_PREFIX) :]
        elif operation.startswith(self.JOB_PREFIX):
            return "job", operation[len(self.JOB_PREFIX) :]
        else:
            return None, None

    def get_effective_sample_rate(self, operation: str) -> int:
        """
        Determines the effective sample rate for a given operation.

        Priority order:
        1. Ignored operations (returns 0)
        2. Specific operation sample rate
        3. Global sample rate

        Args:
            operation: The operation string (e.g. "Controller/users/show")

        Returns:
            Integer between 0 and 100 representing sample rate
        """
        op_type, name = self._get_operation_type_and_name(operation)
        if not op_type or not name:
            return self.sample_rate  # Fall back to global rate for unknown operations

        if op_type == "endpoint":
            if name in self.ignore_endpoints:
                return 0

            matching_rate = self._find_matching_rate(name, self.sample_endpoints)
            if matching_rate is not None:
                return matching_rate
            if self.endpoint_sample_rate is not None:
                return self.endpoint_sample_rate

        else:  # op_type == 'job'
            if name in self.ignore_jobs:
                return 0

            matching_rate = self._find_matching_rate(name, self.sample_jobs)
            if matching_rate is not None:
                return matching_rate
            if self.job_sample_rate is not None:
                return self.job_sample_rate

        # Fall back to global sample rate
        return self.sample_rate

    def should_sample(self, operation: str) -> bool:
        """
        Determines if an operation should be sampled.
        If no sampling is enabled, always return True.

        Args:
            operation: The operation string (e.g. "Controller/users/show"
                   or "Job/mailer")

        Returns:
            Boolean indicating whether to sample this operation
        """
        if not self._any_sampling():
            return True
        return random.randint(1, 100) <= self.get_effective_sample_rate(operation)
