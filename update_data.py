import json
import urllib.request
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo


PACIFIC = ZoneInfo("America/Los_Angeles")

# Approximate Morro Bay location used for the NWS hourly forecast.
MORRO_LAT = 35.3658
MORRO_LON = -120.8499


# ---------------------------------------------------------
# BASIC INTERNET DOWNLOAD FUNCTIONS
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# NDBC BUOY DATA
# ---------------------------------------------------------

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
# DIABLO CANYON BUOY
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

    wind_speed_ms = number(
        row.get("WSPD")
    )

    wind_gust_ms = number(
        row.get("GST")
    )

    wind_direction = number(
        row.get("WDIR")
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
            ),

        "wind_mph":
            round(
                wind_speed_ms * 2.23694,
                1
            )
            if wind_speed_ms is not None
            else None,

        "wind_gust_mph":
            round(
                wind_gust_ms * 2.23694,
                1
            )
            if wind_gust_ms is not None
            else None,

        "wind_direction_deg":
            wind_direction

    }


# ---------------------------------------------------------
# CAPE SAN MARTIN OFFSHORE BUOY
# NDBC 46028
# ---------------------------------------------------------

def offshore_data():

    row = parse_ndbc("46028")

    wave_m = number(
        row.get("WVHT")
    )

    period = number(
        row.get("DPD")
    )

    direction = number(
        row.get("MWD")
    )

    return {

        "station": "46028",

        "name":
            "Cape San Martin",

        "wave_height_ft":
            meters_to_feet(
                wave_m
            ),

        "period_sec":
            period,

        "direction_deg":
            direction

    }


# ---------------------------------------------------------
# NOAA TIDE API
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


# ---------------------------------------------------------
# TIDE CURVE
#
# NOAA returns many points throughout the day.
# These points will be used to draw the graph.
# ---------------------------------------------------------

def tide_curve(today):

    date_string = (
        today.strftime("%Y%m%d")
    )

    result = tide_request(
        date_string,
        "6"
    )

    predictions = (
        result.get(
            "predictions",
            []
        )
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


# ---------------------------------------------------------
# HIGH / LOW TIDE TABLE
# ---------------------------------------------------------

def tide_highs_lows(today):

    date_string = (
        today.strftime("%Y%m%d")
    )

    result = tide_request(
        date_string,
        "hilo"
    )

    predictions = (
        result.get(
            "predictions",
            []
        )
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
# NATIONAL WEATHER SERVICE
# MORRO BAY HOURLY FORECAST
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


        # Only keep roughly the next 30 hours.
        difference = (
            local_start - now
        ).total_seconds() / 3600


        if difference < -1:
            continue


        if difference > 30:
            break


        wind_speed_text = (
            period.get(
                "windSpeed",
                ""
            )
        )


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
                wind_speed_text,

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
# MAIN PROGRAM
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


    # DIABLO CANYON

    try:

        data["diablo"] = (
            diablo_data()
        )

    except Exception as error:

        print(
            "Diablo Canyon error:",
            error
        )


    # CAPE SAN MARTIN

    try:

        data["offshore"] = (
            offshore_data()
        )

    except Exception as error:

        print(
            "Cape San Martin error:",
            error
        )


    # TIDE GRAPH

    try:

        data["tide_curve"] = (
            tide_curve(now)
        )

    except Exception as error:

        print(
            "Tide curve error:",
            error
        )


    # HIGH / LOW TIDES

    try:

        data["tides"] = (
            tide_highs_lows(now)
        )

    except Exception as error:

        print(
            "High/low tide error:",
            error
        )


    # MORRO BAY WIND FORECAST

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


    # SAVE EVERYTHING TO data.json

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
