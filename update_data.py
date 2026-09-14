import json
import urllib.request
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo


PACIFIC = ZoneInfo("America/Los_Angeles")

MORRO_LAT = 35.3658
MORRO_LON = -120.8499


def download_text(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Morro-Bay-Surf/1.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        return response.read().decode(
            "utf-8",
            errors="replace"
        )


def download_json(url):
    return json.loads(
        download_text(url)
    )


def parse_ndbc(station):

    url = (
        "https://www.ndbc.noaa.gov/"
        f"data/realtime2/{station}.txt"
    )

    text = download_text(url)

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if len(lines) < 3:
        raise RuntimeError(
            f"No observations for {station}"
        )

    headers = (
        lines[0]
        .lstrip("#")
        .split()
    )

    for line in lines[2:]:

        values = line.split()

        if len(values) < len(headers):
            continue

        return dict(
            zip(headers, values)
        )

    raise RuntimeError(
        f"No valid observation for {station}"
    )


def number(value):

    if value is None:
        return None

    if value in {
        "MM",
        "999",
        "999.0",
        "99.0",
        "9999"
    }:
        return None

    try:
        return float(value)

    except ValueError:
        return None


def meters_to_feet(value):

    if value is None:
        return None

    return round(
        value * 3.28084,
        1
    )


def celsius_to_fahrenheit(value):

    if value is None:
        return None

    return round(
        value * 9 / 5 + 32,
        1
    )


# ---------------------------------------------------------
# DIABLO CANYON
# NDBC 46215
# ---------------------------------------------------------

def diablo_data():

    row = parse_ndbc("46215")

    wave_m = number(
        row.get("WVHT")
    )

    period = number(
        row.get("DPD")
    )

    direction = number(
        row.get("MWD")
    )

    water_c = number(
        row.get("WTMP")
    )

    return {

        "station": "46215",

        "name": "Diablo Canyon",

        "wave_height_ft":
            meters_to_feet(
                wave_m
            ),

        "period_sec":
            period,

        "direction_deg":
            direction,

        "water_temp_f":
            celsius_to_fahrenheit(
                water_c
            )

    }


# ---------------------------------------------------------
# SANTA MARIA OFFSHORE BUOY
# NDBC 46011
# ---------------------------------------------------------

def offshore_data():

    row = parse_ndbc("46011")

    wave_m = number(
        row.get("WVHT")
    )

    period = number(
        row.get("DPD")
    )

    direction = number(
        row.get("MWD")
    )

    water_c = number(
        row.get("WTMP")
    )

    return {

        "station": "46011",

        "name": "Santa Maria Offshore",

        "wave_height_ft":
            meters_to_feet(
                wave_m
            ),

        "period_sec":
            period,

        "direction_deg":
            direction,

        "water_temp_f":
            celsius_to_fahrenheit(
                water_c
            )

    }


# ---------------------------------------------------------
# NOAA TIDES
# PORT SAN LUIS 9412110
# ---------------------------------------------------------

def tide_request(
    date_string,
    interval
):

    params = {

        "product":
            "predictions",

        "application":
            "Morro-Bay-Surf",

        "begin_date":
            date_string,

        "end_date":
            date_string,

        "datum":
            "MLLW",

        "station":
            "9412110",

        "time_zone":
            "lst_ldt",

        "units":
            "english",

        "format":
            "json",

        "interval":
            interval

    }

    url = (
        "https://api.tidesandcurrents.noaa.gov/"
        "api/prod/datagetter?"
        + urllib.parse.urlencode(
            params
        )
    )

    return download_json(url)


def tide_curve(today):

    date_string = (
        today.strftime("%Y%m%d")
    )

    result = tide_request(
        date_string,
        "6"
    )

    predictions = result.get(
        "predictions",
        []
    )

    curve = []

    for prediction in predictions:

        timestamp = datetime.strptime(
            prediction["t"],
            "%Y-%m-%d %H:%M"
        )

        curve.append({

            "time":
                timestamp.strftime(
                    "%-I:%M %p"
                ),

            "hour_decimal":
                round(
                    timestamp.hour
                    + timestamp.minute / 60,
                    2
                ),

            "height_ft":
                round(
                    float(
                        prediction["v"]
                    ),
                    2
                )

        })

    return curve


def tide_highs_lows(today):

    date_string = (
        today.strftime("%Y%m%d")
    )

    result = tide_request(
        date_string,
        "hilo"
    )

    predictions = result.get(
        "predictions",
        []
    )

    tides = []

    for prediction in predictions:

        timestamp = datetime.strptime(
            prediction["t"],
            "%Y-%m-%d %H:%M"
        )

        tides.append({

            "type":
                "HIGH"
                if prediction["type"] == "H"
                else "LOW",

            "time":
                timestamp.strftime(
                    "%-I:%M %p"
                ),

            "hour_decimal":
                round(
                    timestamp.hour
                    + timestamp.minute / 60,
                    2
                ),

            "height_ft":
                round(
                    float(
                        prediction["v"]
                    ),
                    1
                )

        })

    return tides


# ---------------------------------------------------------
# MORRO BAY WIND FORECAST
# NATIONAL WEATHER SERVICE
# ---------------------------------------------------------

def morro_wind_forecast(now):

    point_url = (
        "https://api.weather.gov/"
        f"points/{MORRO_LAT},{MORRO_LON}"
    )

    point_data = download_json(
        point_url
    )

    forecast_url = (
        point_data[
            "properties"
        ][
            "forecastHourly"
        ]
    )

    forecast_data = download_json(
        forecast_url
    )

    periods = (
        forecast_data
        .get(
            "properties",
            {}
        )
        .get(
            "periods",
            []
        )
    )

    forecast = []

    for period in periods:

        start = datetime.fromisoformat(
            period["startTime"]
        )

        local_start = (
            start.astimezone(
                PACIFIC
            )
        )

        difference = (
            local_start - now
        ).total_seconds() / 3600

        if difference < -1:
            continue

        if difference > 30:
            break

        forecast.append({

            "time":
                local_start.strftime(
                    "%-I %p"
                ),

            "date":
                local_start.strftime(
                    "%a"
                ),

            "hour":
                local_start.hour,

            "temperature_f":
                period.get(
                    "temperature"
                ),

            "wind_speed":
                period.get(
                    "windSpeed",
                    ""
                ),

            "wind_direction":
                period.get(
                    "windDirection"
                ),

            "short_forecast":
                period.get(
                    "shortForecast"
                )

        })

    return forecast


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    now = datetime.now(
        PACIFIC
    )

    data = {

        "location":
            "Morro Bay, California",

        "date_display":
            now.strftime(
                "%A, %B %-d, %Y"
            ),

        "updated_display":
            now.strftime(
                "%-I:%M %p %Z"
            ),

        "diablo":
            None,

        "offshore":
            None,

        "tide_curve":
            [],

        "tides":
            [],

        "wind_forecast":
            []

    }


    try:

        data["diablo"] = (
            diablo_data()
        )

    except Exception as error:

        print(
            "Diablo Canyon error:",
            error
        )


    try:

        data["offshore"] = (
            offshore_data()
        )

    except Exception as error:

        print(
            "Santa Maria offshore error:",
            error
        )


    try:

        data["tide_curve"] = (
            tide_curve(now)
        )

    except Exception as error:

        print(
            "Tide curve error:",
            error
        )


    try:

        data["tides"] = (
            tide_highs_lows(now)
        )

    except Exception as error:

        print(
            "High/low tide error:",
            error
        )


    try:

        data["wind_forecast"] = (
            morro_wind_forecast(
                now
            )
        )

    except Exception as error:

        print(
            "Wind forecast error:",
            error
        )


    with open(
        "data.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2
        )


    print(
        json.dumps(
            data,
            indent=2
        )
    )


if __name__ == "__main__":
    main()
