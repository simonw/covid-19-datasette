# covid-19-datasette

Deploys a Datasette instance with data from https://github.com/CSSEGISandData/COVID-19

The Datasette instance lives at https://covid-19.datasettes.com/ and is updated hourly.

Please **do not** use this tool to share information about COVID-19 without making absolutely sure you understand how the data is structured and sourced.

The database is built from the daily report CSV files in the Johns Hopkins CSSE `csse_covid_19_data` folder - be sure to consult [their README](https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data) for documentation of the fields.

The [build script for the database](https://github.com/simonw/covid-19-datasette/blob/master/build_database.py) makes one alteration to the data: it attempts to fill any missing  `latitude` and `longitude` columns with values from similar rows.

If you are going to make use of those columns, make sure you understand how that backfill mechanism works in case it affects your calculations in some way.
