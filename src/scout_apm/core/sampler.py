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

    def _get_matching_pattern(
        self, name: str, patterns: Dict[str, float]
    ) -> Optional[str]:
        """
        Find the most specific matching pattern for an operation name.

        Args:
            name: The operation name to match
            patterns: Dictionary of pattern to sample rate mappings

        Returns:
            The matching pattern or None if no match found
        """
        logger.debug(f"Finding matching pattern for name: {name}")
        logger.debug(f"Patterns: {patterns}")

        # First check for exact match
        if name in patterns:
            logger.debug(f"Exact match found for name: {name}")
            return name

        # Then check for wildcard patterns, prioritizing longest match
        matching_pattern = None
        longest_match = 0

        wildcard_patterns = [p for p in patterns if "*" in p]
        for pattern in wildcard_patterns:
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if name.startswith(prefix) and len(prefix) > longest_match:
                    longest_match = len(prefix)
                    matching_pattern = pattern

        return matching_pattern

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
            logger.debug(f"Unknown operation type for: {operation}")
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

            matching_pattern = self._get_matching_pattern(name, self.sample_endpoints)
            if matching_pattern:
                return self.sample_endpoints[matching_pattern]

        else:  # op_type == 'job'
            if name in self.ignore_jobs:
                return 0

            matching_pattern = self._get_matching_pattern(name, self.sample_jobs)
            if matching_pattern:
                logger.debug(f"Matching job pattern: {matching_pattern}")
                return self.sample_jobs[matching_pattern]

        # Fall back to global sample rate
        logger.debug(f"Using global sample rate: {self.sample_rate}")
        return self.sample_rate

    def should_sample(self, operation: str) -> bool:
        """
        Determines if an operation should be sampled.

        Args:
            operation: The operation string (e.g. "Controller/users/show"
                   or "Job/mailer")

        Returns:
            Boolean indicating whether to sample this operation
        """
        return random.randint(1, 100) <= self.get_effective_sample_rate(operation)
