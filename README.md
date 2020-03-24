# covid-19-datasette

Deploys a Datasette instance with data from https://github.com/CSSEGISandData/COVID-19

The Datasette instance lives at https://covid-19.datasettes.com/ and is updated hourly.

Please **do not** use this tool to share information about COVID-19 without making absolutely sure you understand how the data is structured and sourced.

The database is built from the daily report CSV files in the Johns Hopkins CSSE `csse_covid_19_data` folder - be sure to consult [their README](https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data) for documentation of the fields.

They are actively making changes to how they report data. You should [follow their issues](https://github.com/CSSEGISandData/COVID-19/issues) closely for updates - for example [this issue](https://github.com/CSSEGISandData/COVID-19/issues/382) about switching from reporting USA data at the county to the state level.

The [build script for the database](https://github.com/simonw/covid-19-datasette/blob/master/build_database.py) makes one alteration to the data: it attempts to fill any missing  `latitude` and `longitude` columns with values from similar rows.

If you are going to make use of those columns, make sure you understand how that backfill mechanism works in case it affects your calculations in some way.

More about this project: [COVID-19 numbers in Datasette](https://simonwillison.net/2020/Mar/11/covid-19/).

This repository uses the deployment pattern described in [Deploying a data API using GitHub Actions and Cloud Run](https://simonwillison.net/2020/Jan/21/github-actions-cloud-run/).

## Example issues

* On the 23rd March 2020 Johns Hopkins [added four new columns](https://github.com/CSSEGISandData/COVID-19/commit/e748b6d8a55e4a88371af56b129ababe1712522d) to the daily CSV file: `admin2`, `fips`, `active` and `combined_key`. These are not present in older CSV files. [#4](https://github.com/simonw/covid-19-datasette/issues/4).
* Some countries (like Italy) are represented by [just the rows](https://covid-19.datasettes.com/covid/daily_reports?country_or_region=Italy&_sort_desc=confirmed#g.mark=bar&g.x_column=day&g.x_type=ordinal&g.y_column=confirmed&g.y_type=quantitative) with `country_or_region` set to `Italy` (and `province_or_state` set to `null`). Larger countries such as the United States have multiple rows for each day divided into separate `province_or_state` values - [example](https://covid-19.datasettes.com/covid/daily_reports?_size=1000&country_or_region__exact=US&_sort_desc=day#g.mark=bar&g.x_column=day&g.x_type=ordinal&g.y_column=confirmed&g.y_type=quantitative&g.color_column=province_or_state).
* Santa Clara County appears to be represented as `Santa Clara, CA` in some records and `Santa Clara County, CA` in others - [example](https://covid-19.datasettes.com/covid/daily_reports?province_or_state__contains=santa+clara&_sort_desc=day#g.mark=bar&g.x_column=day&g.x_type=ordinal&g.y_column=confirmed&g.y_type=quantitative).
* Passengers from the Diamond Princess cruise are represented by a number of different rows with "From Diamond Princess" in their `province_or_state` column - [example](https://covid-19.datasettes.com/covid/daily_reports?_facet=province_or_state&_facet=country_or_region&province_or_state__contains=from+diamond&_sort_desc=day).
