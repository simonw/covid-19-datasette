import json
from pathlib import Path
import sqlite_utils
from sqlite_utils.db import DescIndex
import csv

base_path = (Path(__file__) / "..").resolve()
jhu_csse_base = base_path / "COVID-19"
nytimes_base = base_path / "covid-19-data"
latimes_base = base_path / "california-coronavirus-data"
economist_base = base_path / "covid-19-excess-deaths-tracker"

EXTRA_CSVS = [
    # file_path, table_name
    (nytimes_base / "us-counties.csv", "ny_times_us_counties"),
    (nytimes_base / "us-states.csv", "ny_times_us_states"),
]


def load_daily_reports():
    daily_reports = list(
        (jhu_csse_base / "csse_covid_19_data" / "csse_covid_19_daily_reports").glob(
            "*.csv"
        )
    )
    for filepath in daily_reports:
        mm, dd, yyyy = filepath.stem.split("-")
        day = f"{yyyy}-{mm}-{dd}"
        with filepath.open() as fp:
            for row in csv.DictReader(fp):
                # Weirdly, this column is sometimes \ufeffProvince/State
                province_or_state = (
                    row.get("\ufeffProvince/State")
                    or row.get("Province/State")
                    or row.get("Province_State")
                    or None
                )
                country_or_region = row.get("Country_Region") or row.get(
                    "Country/Region"
                )
                yield {
                    "day": day,
                    "country_or_region": country_or_region.strip()
                    if country_or_region
                    else None,
                    "province_or_state": province_or_state.strip()
                    if province_or_state
                    else None,
                    "admin2": row.get("Admin2") or None,
                    "fips": row.get("FIPS", "").strip() or None,
                    "confirmed": int(float(row["Confirmed"] or 0)),
                    "deaths": int(float(row["Deaths"] or 0)),
                    "recovered": int(float(row["Recovered"] or 0)),
                    "active": int(row["Active"]) if row.get("Active") else None,
                    "latitude": row.get("Latitude") or row.get("Lat") or None,
                    "longitude": row.get("Longitude") or row.get("Long_") or None,
                    "last_update": row.get("Last Update")
                    or row.get("Last_Update")
                    or None,
                    "combined_key": row.get("Combined_Key") or None,
                }


def add_missing_latitude_longitude(db):
    # Some rows are missing a latitude/longitude, try to backfill those
    with db.conn:
        for row in db.conn.execute(
            """
            select
                country_or_region, province_or_state,
                max(latitude), max(longitude)
            from
                johns_hopkins_csse_daily_reports
            where
                latitude is not null
            group by
                country_or_region, province_or_state
        """
        ).fetchall():
            country_or_region, province_or_state, latitude, longitude = row
            db.conn.execute(
                """
                update johns_hopkins_csse_daily_reports
                set latitude = ?, longitude = ?
                where country_or_region = ?
                and province_or_state = ?
                and latitude is null
            """,
                [latitude, longitude, country_or_region, province_or_state],
            )


def load_csv(filepath):
    with filepath.open() as fp:
        for row in csv.DictReader(fp):
            for key in row:
                if row[key].isdigit():
                    # Convert integers
                    row[key] = int(row[key])
                else:
                    try:
                        float(row[key])
                    except ValueError:
                        pass
                    else:
                        # Convert floats
                        row[key] = float(row[key])
            yield row


def load_csv_with_cadence(filepath):
    for row in load_csv(filepath):
        cadence = None
        if "week" in row:
            cadence = "weekly"
        elif "month" in row:
            cadence = "monthly"
        if cadence is not None:
            row["cadence"] = cadence
        yield row


def load_economist_data(db, economist_base):
    # economist_excess_deaths table
    excess_table = db["economist_excess_deaths"]
    if excess_table.exists():
        excess_table.drop()
    for filepath in (economist_base / "output-data" / "excess-deaths").glob("*.csv"):
        excess_table.insert_all(load_csv_with_cadence(filepath), alter=True)
    # economist_historical_deaths table
    historical_table = db["economist_historical_deaths"]
    if historical_table.exists():
        historical_table.drop()
    for filepath in (economist_base / "output-data" / "historical-deaths").glob(
        "*.csv"
    ):
        historical_table.insert_all(load_csv_with_cadence(filepath), alter=True)
    historical_table.create_index(["country"], if_not_exists=True)
    historical_table.create_index(["cadence"], if_not_exists=True)
    historical_table.create_index(["end_date"], if_not_exists=True)


if __name__ == "__main__":
    db = sqlite_utils.Database(base_path / "covid.db")

    # Load John Hopkins CSSE daily reports
    table = db["johns_hopkins_csse_daily_reports"]
    if table.exists():
        table.drop()
    table.insert_all(load_daily_reports())
    table.create_index(["day"], if_not_exists=True)
    table.create_index(["province_or_state"], if_not_exists=True)
    table.create_index(["country_or_region"], if_not_exists=True)
    table.create_index(["combined_key"], if_not_exists=True)
    add_missing_latitude_longitude(db)

    # Add a view with the old name
    if "daily_reports" in db.table_names():
        db["daily_reports"].drop()

    if "daily_reports" not in db.view_names():
        db.create_view(
            "daily_reports", "select * from johns_hopkins_csse_daily_reports"
        )

    csvs_to_load = EXTRA_CSVS[:]
    # Add LA Times CSVs, but only if they are in metadata.json
    in_metadata = set(
        json.load(open("metadata.json"))["databases"]["covid"]["tables"].keys()
    )
    for path in latimes_base.glob("*.csv"):
        table_name = path.stem.replace("-", "_")
        if not table_name.startswith("latimes_"):
            table_name = "la_times_{}".format(table_name)
        if table_name in in_metadata:
            csvs_to_load.append((path, table_name))

    # Now do the NYTimes and LA times data
    for csv_path, table_name in csvs_to_load:
        table = db[table_name]
        if table.exists():
            table.drop()
        table.insert_all(load_csv(csv_path))

    db["ny_times_us_counties"].create_index(["state"])
    db["ny_times_us_counties"].create_index(["county"])
    db["ny_times_us_counties"].create_index(["fips"])
    db["ny_times_us_counties"].create_index([DescIndex("date")])

    # And the US census data
    if "us_census_state_populations_2019" not in db.table_names():
        db["us_census_state_populations_2019"].insert_all(
            load_csv(base_path / "us_census_state_populations_2019.csv")
        )
    if "us_census_county_populations_2019" not in db.table_names():
        db["us_census_county_populations_2019"].insert_all(
            load_csv(base_path / "us_census_county_populations_2019.csv"), pk="fips"
        )

    # The Economist
    load_economist_data(db, economist_base)

    # More views
    db.create_view("latest_ny_times_counties_with_populations", """
    select
      ny_times_us_counties.date,
      ny_times_us_counties.county,
      ny_times_us_counties.state,
      ny_times_us_counties.fips,
      ny_times_us_counties.cases,
      ny_times_us_counties.deaths,
      us_census_county_populations_2019.population,
      1000000 * ny_times_us_counties.deaths / us_census_county_populations_2019.population as deaths_per_million,
      1000000 * ny_times_us_counties.cases / us_census_county_populations_2019.population as cases_per_million
    from
      ny_times_us_counties
      join us_census_county_populations_2019 on ny_times_us_counties.fips = us_census_county_populations_2019.fips
    where
      "date" = (
        select
          max(date)
        from
          ny_times_us_counties
      )
    order by
      deaths_per_million desc
    """, replace=True)
