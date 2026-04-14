import logging

import grpc
from auth.jwt import InvalidTokenError, JWTValidator
from grpc import aio

logger = logging.getLogger("api-lab.grpc.auth")

_USER_CONTEXT_KEY = "authenticated_user"


def get_user_from_context(context):
    for key, value in context.invocation_metadata():
        if key == _USER_CONTEXT_KEY:
            return value
    return None


class _AbortHandler(grpc.GenericRpcHandler):
    def __init__(self, code, details):
        self._code = code
        self._details = details

    def service(self, _handler_call_details):
        return grpc.unary_unary_rpc_method_handler(self._abort)

    async def _abort(self, _request, context):
        await context.abort(self._code, self._details)


class AuthInterceptor(aio.ServerInterceptor):
    def __init__(self, jwt_validator: JWTValidator):
        self._validator = jwt_validator
        self._abort_handler = _AbortHandler(
            grpc.StatusCode.UNAUTHENTICATED,
            "Invalid or missing authentication token",
        )

    async def intercept_service(self, continuation, handler_call_details):
        metadata = dict(handler_call_details.invocation_metadata)
        method = handler_call_details.method

        if method and method.endswith("/Check"):
            return await continuation(handler_call_details)
        if method and method.endswith("/Watch"):
            return await continuation(handler_call_details)
        if method and "grpc.reflection" in method:
            return await continuation(handler_call_details)

        auth_value = metadata.get("authorization", "")

        if not auth_value.lower().startswith("bearer "):
            return self._abort_handler.service(handler_call_details)

        token = auth_value[7:]
        try:
            _user = await self._validator.validate(token)
        except InvalidTokenError:
            return self._abort_handler.service(handler_call_details)

        return await continuation(handler_call_details)
