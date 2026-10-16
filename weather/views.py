from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import get_weather_for_query


class WeatherForecastView(APIView):
    """
    Real forecast via Open-Meteo (national met models).
    Query: ?location=Greater%20Noida  OR  ?lat=28.47&lon=77.50
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        location = request.query_params.get('location')
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')

        try:
            lat_f = float(lat) if lat not in (None, '') else None
            lon_f = float(lon) if lon not in (None, '') else None
        except ValueError:
            return Response({'error': 'Invalid lat/lon'}, status=status.HTTP_400_BAD_REQUEST)

        if lat_f is None and lon_f is None and not (location and str(location).strip()):
            return Response(
                {'error': 'Provide location or lat & lon'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            weather = get_weather_for_query(location=location, lat=lat_f, lon=lon_f)
        except LookupError:
            return Response({'error': 'Could not find that location'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            print(f'Weather fetch failed: {exc}')
            return Response(
                {'error': 'Weather service temporarily unavailable'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({'weather': weather})
