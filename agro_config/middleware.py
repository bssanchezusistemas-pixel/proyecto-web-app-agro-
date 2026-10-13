"""
Middleware CORS ligero integrado para permitir peticiones desde el frontend en React (Vite / Vercel)
incluso en entornos donde django-cors-headers no esté instalado.
"""

from django.http import HttpRequest, HttpResponse


class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.method == "OPTIONS":
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        origin = request.headers.get("Origin") or "*"
        response["Access-Control-Allow-Origin"] = origin
        response["Access-Control-Allow-Credentials"] = "true"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = (
            "Accept, Authorization, Content-Type, X-CSRFToken, X-Requested-With"
        )
        return response
