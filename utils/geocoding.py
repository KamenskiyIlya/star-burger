import requests
from geopy.distance import distance as geopy_distance

from geocacheapp.models import GeoPoint


def get_cached_coordinates_bulk(addresses):
    cached_geopoints = GeoPoint.objects.filter(address__in=addresses)
    points_coords = {
        point.address: (point.lon, point.lat) for point in cached_geopoints
    }
    return points_coords


def save_coordinates_bulk(coordinates: dict):
    geopoints_to_create = []
    for address, (lon, lat) in coordinates.items():
        geopoints_to_create.append(GeoPoint(address=address, lon=lon, lat=lat))

    GeoPoint.objects.bulk_create(geopoints_to_create)


def get_coordinates(apikey, address):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(
        base_url,
        params={
            "geocode": address,
            "apikey": apikey,
            "format": "json",
        },
    )
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection'][
        'featureMember'
    ]

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lon, lat


def calculate_distance(coords_1, coords_2):
    distance = round(
        geopy_distance(
            (coords_1[1], coords_1[0]), (coords_2[1], coords_2[0])
        ).km,
        2,
    )
    return distance
