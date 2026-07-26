from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

class APIException(Exception):
    """
    Custom base exception for all domain-specific API errors.
    Standardizes error codes and status mappings.
    """
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message

def register_exception_handlers(app: FastAPI) -> None:
    """
    Registers global exception hooks on the FastAPI app.
    Translates all validation, HTTP, and internal failures to the standard JSON format.
    """
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message
                }
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # Translate generic HTTP exceptions
        code = "HTTP_ERROR"
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            code = "UNAUTHORIZED"
        elif exc.status_code == status.HTTP_403_FORBIDDEN:
            code = "FORBIDDEN"
        elif exc.status_code == status.HTTP_404_NOT_FOUND:
            code = "NOT_FOUND"
        elif exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            code = "RATE_LIMIT_EXCEEDED"

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": code,
                    "message": exc.detail
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Format structured validation errors
        errors = exc.errors()
        messages = []
        for err in errors:
            loc = " -> ".join([str(x) for x in err["loc"][1:]]) if len(err["loc"]) > 1 else str(err["loc"][0])
            messages.append(f"[{loc}]: {err['msg']}")

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_FAILED",
                    "message": "; ".join(messages)
                }
            }
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        # Prevent leaking raw python exceptions in production environments
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please try again later."
                }
            }
        )
