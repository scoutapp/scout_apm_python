from __future__ import absolute_import, division, print_function, unicode_literals


class RemoteIp(object):
    """
    A helper class to lookup what IP the request is associated with for adding
    Context to a request

    This is not suitable to use in any security sensitive position. This is
    spoofable by the requester.

    Some of this algorithm is borrowed for Ruby on Rails' RemoteIp middleware
    """

    @classmethod
    def lookup_from_headers(cls, headers):
        """
        Given a dictionary of headers (WSGI request.META for instance), look up
        the most likely user's IP
        """

        # A single address, set by this server, returned as an Array
        remote_addr = cls.ips_from(headers.get("REMOTE_ADDR"))

        # Could be a CSV list and/or repeated headers that were concatenated.
        forwarded_ips = cls.ips_from(headers.get("HTTP_X_FORWARDED_FOR"))
        client_ips = cls.ips_from(headers.get("HTTP_CLIENT_IP"))

        # We assume these things about the IP headers:
        #
        #   - X-Forwarded-For will be a list of IPs, one per proxy, or blank.
        #       in order: `client,proxy1,proxy2`
        #   - Client-Ip is propagated from the outermost proxy, or is blank
        #   - REMOTE_ADDR will be the IP that made the request to this server
        #
        # X-Forwarded-For and Client-Ip shouldn't be set at the same time, but
        # if they are, use the one in Forwarded
        ips = forwarded_ips + client_ips + remote_addr

        try:
            return ips[0]
        except IndexError:
            return None

    @classmethod
    def ips_from(cls, header):
        """Splits the header into a list"""

        if header is None:
            return []

        return header.split(",")
