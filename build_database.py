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
                if "\ufeffProvince/State" in row:
                    province_or_state = row["\ufeffProvince/State"]
                else:
                    province_or_state = row["Province/State"]
                yield {
                    "day": day,
                    "country_or_region": row["Country/Region"],
                    "province_or_state": province_or_state,
                    "confirmed": int(row["Confirmed"] or 0),
                    "deaths": int(row["Deaths"] or 0),
                    "recovered": int(row["Recovered"] or 0),
                    "last_update": row["Last Update"],
                }


if __name__ == "__main__":
    db = sqlite_utils.Database(base_path / "covid.db")
    # Drop table if it exists
    table = db["daily_reports"]
    if table.exists():
        table.drop()
    table.insert_all(load_daily_reports())
