import scout_apm.api
from scout_apm.core.tracked_request import TrackedRequest


def test_rename_transaction():
    tr = TrackedRequest.instance()
    assert('transaction_name' not in tr.tags)
    scout_apm.api.rename_transaction('Unit Test')
    assert(tr.tags['transaction.name'] == 'Unit Test')



