# coding=utf-8

import logging
import random
from typing import Dict, Optional, Tuple

from scout_apm.core.tracked_request import TrackedRequest

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
        self.legacy_ignore = config.value("ignore")

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

    def _find_exact_match(
        self, name: str, patterns: Dict[str, float]
    ) -> Optional[float]:
        """
        Finds the exact sample rate for a given operation name.

        Args:
            name: The operation name to match
            patterns: Dictionary of pattern to sample rate mappings

        Returns:
            The sample rate for the matching pattern or None if no match found
        """
        return patterns.get(name)

    def _find_prefix_match(
        self, name: str, patterns: Dict[str, float]
    ) -> Optional[float]:
        """Find the longest matching prefix in sample configurations."""
        matching_prefixes = [
            (prefix, rate)
            for prefix, rate in patterns.items()
            if name.startswith(prefix)
        ]
        if not matching_prefixes:
            return None
        # Return rate for longest matching prefix
        return max(matching_prefixes, key=lambda x: len(x[0]))[1]

    def _is_legacy_ignored(self, name: str) -> bool:
        """Check if path matches any legacy ignore patterns."""
        return any(name.startswith(ignored) for ignored in self.legacy_ignore)

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

    def get_effective_sample_rate(self, request: TrackedRequest) -> int:
        """
        Determines the effective sample rate for a given operation.

        Priority order (highest to lowest):
        1. Exact matches in sample_endpoints/sample_jobs
        2. Exact matches in ignore lists (returns 0)
        3. Prefix matches in sample_endpoints/sample_jobs
        4. Legacy ignore patterns (returns 0)
        5. Request-level ignore (returns 0)
        6. Operation-specific default rate
        7. Global sample rate
        """
        operation = request.operation
        op_type, name = self._get_operation_type_and_name(operation)

        if not op_type or not name:
            return self.sample_rate

        patterns = self.sample_endpoints if op_type == "endpoint" else self.sample_jobs
        ignored_set = (
            self.ignore_endpoints if op_type == "endpoint" else self.ignore_jobs
        )
        default_rate = (
            self.endpoint_sample_rate if op_type == "endpoint" else self.job_sample_rate
        )

        # Check for exact match in sampling patterns
        exact_rate = self._find_exact_match(name, patterns)
        if exact_rate is not None:
            return exact_rate

        # Check for exact endpoint/job ignores
        if name in ignored_set:
            return 0

        # Check for prefix match in sampling patterns
        prefix_rate = self._find_prefix_match(name, patterns)
        if prefix_rate is not None:
            return prefix_rate

        # Check legacy ignore patterns
        if self._is_legacy_ignored(name):
            return 0

        # Check if request is explicitly ignored via tag
        if request.is_ignored():
            return 0

        # Use operation-specific default rate if available
        if default_rate is not None:
            return default_rate

        # Fall back to global sample rate
        return self.sample_rate

    def should_sample(self, request: TrackedRequest) -> bool:
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
        return random.randint(1, 100) <= self.get_effective_sample_rate(request)
