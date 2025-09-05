from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from .utils import ensure_alias_for_client
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.core.management import call_command
from io import StringIO
from django.db import connections
import logging
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
import os


logger = logging.getLogger(__name__)
@method_decorator(csrf_exempt, name='dispatch')
class RegisterDBAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        client_id = (request.data or {}).get("client_id")
        client_username = (request.data or {}).get("client_username")

        if not client_id and not client_username:
            return Response({"detail": "Provide client_id or client_username."}, status=400)

        try:
            alias = ensure_alias_for_client(
                client_id=int(client_id) if str(client_id).isdigit() else None,
                client_username=client_username if not client_id else None,
            )

            if settings.DEBUG or str(os.getenv("ASSET_AUTO_MIGRATE", "0")) == "1":
                out = StringIO()
                call_command(
                    "migrate",
                    "communicationapp",
                    database=alias,
                    interactive=False,
                    verbosity=1,
                    stdout=out,
                )
                logger.info("Migrated app 'communicationapp' on %s\n%s", alias, out.getvalue())

            try:
                connections[alias].close()
            except Exception:
                pass

            return Response({"detail": "Alias ready", "alias": alias}, status=201)

        except Exception as e:
            logger.exception("RegisterDBByClient failed")
            return Response({"detail": str(e)}, status=400)
#COMMUNICATIONAPP/VIEWS.PY