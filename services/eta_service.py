"""
ETA Service — Predicts ambulance estimated arrival time using Haversine distance.
"""
import math
from utils.logger import app_logger

AVERAGE_SPEED_KMH = 40.0   # city ambulance average
ROAD_FACTOR       = 1.35   # straight-line → road distance multiplier
DISPATCH_BUFFER   = 3.0    # minutes for driver prep + dispatch lag

def _haversine_km(lat1, lon1, lat2, lon2):
    """Returns straight-line distance in kilometres between two GPS coordinates."""
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(d_lon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


class ETAService:
    def compute(self, driver_lat, driver_lon, target_lat, target_lon,
                historical_avg_mins=None):
        """
        Returns predicted ETA in minutes.

        Parameters
        ----------
        driver_lat / driver_lon  : current ambulance GPS position
        target_lat / target_lon  : emergency scene GPS position
        historical_avg_mins      : optional historical average (minutes) for
                                   this driver — used as a correction factor
        """
        try:
            if None in (driver_lat, driver_lon, target_lat, target_lon):
                return None

            distance_km   = _haversine_km(driver_lat, driver_lon,
                                           target_lat, target_lon)
            road_distance = distance_km * ROAD_FACTOR
            travel_mins   = (road_distance / AVERAGE_SPEED_KMH) * 60

            # Blend with historical if available
            if historical_avg_mins and historical_avg_mins > 0:
                travel_mins = (travel_mins * 0.7) + (historical_avg_mins * 0.3)

            eta = round(travel_mins + DISPATCH_BUFFER, 1)
            app_logger.info(f"ETA computed: {eta} min  "
                            f"(dist={distance_km:.2f} km, road={road_distance:.2f} km)")
            return eta
        except Exception as e:
            app_logger.error(f"ETAService error: {e}")
            return None


eta_service = ETAService()
