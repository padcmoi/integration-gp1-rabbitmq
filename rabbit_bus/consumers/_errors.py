"""Bus errors that carry the HTTP status of the answer.

Raising one of these from a consumer sets the statusCode of the reply; a bare
ValueError answers 400, NotImplementedError 501, anything else 500. There is
deliberately no 401: the mailbox is the authorization, a caller that cannot
publish to the queue cannot reach the bus at all.
"""


class BusError(Exception):
    status = 500


class BadRequest(BusError):
    status = 400


class Forbidden(BusError):
    status = 403


class NotFound(BusError):
    status = 404


class Conflict(BusError):
    status = 409
