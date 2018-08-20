from scout_apm.core.remote_ip import RemoteIp

def test_no_forwarded_for():
    ip = RemoteIp.lookup_from_headers({'REMOTE_ADDR': '1.1.1.1'})
    assert(ip == '1.1.1.1')


def test_forwarded_for():
    ip = RemoteIp.lookup_from_headers({
        'REMOTE_ADDR': '1.1.1.1',
        'HTTP_X_FORWARDED_FOR': '2.2.2.2,3.3.3.3',
        })
    assert(ip == '2.2.2.2')


def test_client_ip():
    ip = RemoteIp.lookup_from_headers({
        'REMOTE_ADDR': '1.1.1.1',
        'HTTP_CLIENT_IP': '2.2.2.2',
        })
    assert(ip == '2.2.2.2')


def test_forwarded_over_client_ip():
    ip = RemoteIp.lookup_from_headers({
        'REMOTE_ADDR': '1.1.1.1',
        'HTTP_X_FORWARDED_FOR': '2.2.2.2,3.3.3.3',
        'HTTP_CLIENT_IP': '4.4.4.4',
        })
    assert(ip == '2.2.2.2')
