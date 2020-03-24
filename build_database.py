from pathlib import Path
import sqlite_utils
import csv

base_path = (Path(__file__) / "..").resolve()
covid_base = base_path / "COVID-19"


def load_daily_reports():
    daily_reports = list(
        (covid_base / "csse_covid_19_data" / "csse_covid_19_daily_reports").glob(
            "*.csv"
        )
    )
    for filepath in daily_reports:
        mm, dd, yyyy = filepath.stem.split("-")
        day = f"{yyyy}-{mm}-{dd}"
        with filepath.open() as fp:
            for row in csv.DictReader(fp):
                # Weirdly, this column is sometimes \ufeffProvince/State
                province_or_state = row.get("\ufeffProvince/State") or row.get("Province/State") or row.get("Province_State") or None
                country_or_region = row.get("Country_Region") or row.get("Country/Region")
                yield {
                    "day": day,
                    "country_or_region": country_or_region.strip() if country_or_region else None,
                    "province_or_state": province_or_state.strip() if province_or_state else None,
                    "admin2": province_or_state.strip() if province_or_state else None,
                    "fips": row.get("FIPS", "").strip() or None,
                    "confirmed": int(row["Confirmed"] or 0),
                    "deaths": int(row["Deaths"] or 0),
                    "recovered": int(row["Recovered"] or 0),
                    "active": int(row["Active"]) if row.get("Active") else None,
                    "latitude": row.get("Latitude") or row.get("Lat") or None,
                    "longitude": row.get("Longitude") or row.get("Long_") or None,
                    "last_update": row.get("Last Update") or row.get("Last_Update") or None,
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
                daily_reports
            where
                latitude is not null
            group by
                country_or_region, province_or_state
        """
        ).fetchall():
            country_or_region, province_or_state, latitude, longitude = row
            db.conn.execute(
                """
                update daily_reports
                set latitude = ?, longitude = ?
                where country_or_region = ?
                and province_or_state = ?
                and latitude is null
            """,
                [latitude, longitude, country_or_region, province_or_state],
            )


if __name__ == "__main__":
    db = sqlite_utils.Database(base_path / "covid.db")
    # Drop table if it exists
    table = db["daily_reports"]
    if table.exists():
        table.drop()
    table.insert_all(load_daily_reports())
    add_missing_latitude_longitude(db)
