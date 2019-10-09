# coding=utf-8
from scout_apm.compat import urlencode

# Originally derived from:
# 1. Rails:
#   https://github.com/rails/rails/blob/0196551e6039ca864d1eee1e01819fcae12c1dc9/railties/lib/rails/generators/rails/app/templates/config/initializers/filter_parameter_logging.rb.tt
# 2. Sentry server side scrubbing:
#   https://docs.sentry.io/data-management/sensitive-data/#server-side-scrubbing
FILTER_PARAMETERS = frozenset(
    [
        "access",
        "access_token",
        "api_key",
        "apikey",
        "auth",
        "auth_token",
        "card[number]",
        "certificate",
        "credentials",
        "crypt",
        "key",
        "mysql_pwd",
        "otp",
        "passwd",
        "password",
        "private",
        "protected",
        "salt",
        "secret",
        "ssn",
        "stripetoken",
        "token",
    ]
)


def create_filtered_path(path, query_params):
    filtered_params = sorted(
        (
            (k, "[FILTERED]" if k.lower() in FILTER_PARAMETERS else v)
            for k, v in query_params
        )
    )
    if not filtered_params:
        return path
    return path + "?" + urlencode(filtered_params)
