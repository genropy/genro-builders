# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""WeatherDashboard - BuilderManager with resolver-backed data.

Demonstrates how the data store can contain BagResolver nodes.
When build() resolves ^pointers, the resolvers fire automatically
and fetch fresh data from external APIs.

Each build() produces an HTML page with live weather data for
multiple cities and recent earthquake activity. Data is always
current — resolvers re-fetch on every build (respecting cache_time).

Requires:
    pip install genro-builders genro-bag httpx

Usage:
    python -m genro_builders.contrib.html.examples.weather_dashboard

    # Or from Python:
    from genro_builders.contrib.html.examples.weather_dashboard import WeatherDashboard

    dashboard = WeatherDashboard()
    print(dashboard.page.render())
"""

from __future__ import annotations

from pathlib import Path

from genro_bag import Bag
from genro_bag.resolvers.contrib import EarthquakeResolver, OpenMeteoResolver

from genro_builders.contrib.html import HtmlBuilder
from genro_builders.manager import BuilderManager

CITIES = [
    ("Rome", "IT"),
    ("Milan", "IT"),
    ("London", "GB"),
    ("Berlin", "DE"),
    ("Paris", "FR"),
]


class WeatherDashboard(BuilderManager):
    """HTML dashboard showing live weather and earthquake data.

    The data store contains:
    - One OpenMeteoResolver per city (weather data)
    - One EarthquakeResolver (USGS recent earthquakes feed)

    When build() resolves ^pointers, each resolver fetches
    fresh data from the respective API.

    Example:
        dashboard = WeatherDashboard()
        print(dashboard.page.render())
    """

    def __init__(self):
        self.page = self.set_builder("page", HtmlBuilder)
        self.run()

    def store(self, data):
        """Set up resolvers in the data store."""
        for city, country in CITIES:
            key = city.lower()
            data.set_item(
                key, None,
                resolver=OpenMeteoResolver(city=city, country_code=country),
            )
        data.set_item("quakes", None, resolver=EarthquakeResolver())

    def main(self, source):
        """Build the HTML page with ^pointers to resolver data."""
        body = source.body()
        body.h1("Live Dashboard")

        # Weather section
        body.h2("Weather")
        self._weather_table(body)

        # Earthquake section
        body.h2("Recent Earthquakes (last hour)")
        body.p("^quakes.title")
        self._earthquake_table(body)

    def _weather_table(self, parent):
        """Build the weather table from ^pointer data."""
        table = parent.table()
        header = table.tr()
        header.th("City")
        header.th("Weather")
        header.th("Temp")
        header.th("Wind")
        header.th("Humidity")

        for city, _country in CITIES:
            key = city.lower()
            tr = table.tr()
            tr.td(city)
            tr.td(f"^{key}.weather")
            tr.td(f"^{key}.temperature_2m")
            tr.td(f"^{key}.wind_speed_10m")
            tr.td(f"^{key}.relative_humidity_2m")

    def _earthquake_table(self, parent):
        """Build the earthquake table from resolved feed data."""
        feed = self.reactive_store.get_item("quakes")
        if not feed or not isinstance(feed, Bag):
            parent.p("No earthquake data available")
            return

        features = feed.get_item("features")
        if not features or not isinstance(features, Bag):
            parent.p("No earthquakes in the last hour")
            return

        table = parent.table()
        header = table.tr()
        header.th("Location")
        header.th("Magnitude")

        for node in features:
            tr = table.tr()
            tr.td(str(node.attr.get("place", "Unknown")))
            tr.td(str(node.attr.get("mag", "?")))


def demo():
    """Run the dashboard and print HTML output."""
    print("Fetching weather and earthquake data...")
    dashboard = WeatherDashboard()
    html = dashboard.page.render()
    print(html)
    print()

    output_path = Path(__file__).parent.parent.parent.parent.parent / "temp" / "weather_dashboard.html"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(html)
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    demo()
