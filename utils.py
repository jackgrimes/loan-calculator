import calendar
import datetime
import logging
import os

import pandas as pd

from configs import data_path, loan

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%d-%b-%y %H:%M:%S"
)


def get_days(year):
    DATE_END = datetime.date(year, 12, 31)
    DATE_START = datetime.date(year - 1, 12, 31)
    return (DATE_END - DATE_START).days


def get_and_prep_data():
    # Read in and clean up data
    logging.info("Reading data")
    events = pd.read_csv(
        os.path.join(data_path, loan, "inputs", "loan_events.csv"),
        dayfirst=True,
        parse_dates=True,
        index_col=["date"],
    )

    interest_rates = pd.read_csv(
        os.path.join(data_path, loan, "inputs", "interest_rates.csv"),
        dayfirst=True,
        parse_dates=True,
        index_col=["date"],
    )

    reported_interest_added = pd.read_csv(
        os.path.join(data_path, loan, "inputs", "reported_interest_added.csv"),
        dayfirst=True,
        parse_dates=True,
        index_col=["date"],
    )

    return events, interest_rates, reported_interest_added


def months_per_tax_year(y):
    df = pd.DataFrame()
    year_months = [f"{y}-{x}" for x in range(4, 13)]
    year_months.extend([f"{y + 1}-{x}" for x in range(1, 4)])
    df["year_month"] = pd.Series(year_months)
    df["tax_year"] = y
    return df


def convert_floats_to_2_dps(df):
    for col in df.columns:
        if df.dtypes[col] == float:
            df[col] = df[col].apply(lambda x: round(x, ndigits=2))
    return df


def calculate_balances_and_interest_added(
    events,
    interest_rates,
    payments_divided_equally_over_tax_year,
    assume_payment_made_day_of_month,
):
    assumptions_string = (
        ""
        + (
            payments_divided_equally_over_tax_year
            * "_payments_divided_equally_over_tax_year"
        )
        + ("_assume_pay_" + str(assume_payment_made_day_of_month))
    )

    logging.info(f"Doing {assumptions_string}")

    if payments_divided_equally_over_tax_year:

        events["financial_year"] = events.index.map(
            lambda x: x.year if (x.month > 4 and x.day > 5) else x.year - 1
        )

        pre_2019 = events[events.financial_year < 2019]
        post_2019 = events[events.financial_year >= 2019]

        pre_2019_neg = pre_2019[pre_2019["balance_change"] < 0]
        pre_2019_pos = pre_2019[pre_2019["balance_change"] > 0]

        average_monthly_repayment = (
            pre_2019_neg.groupby(["financial_year"]).sum()["balance_change"] / 12
        )

        repayments_averaged_over_tax_year = pd.DataFrame()
        for y in average_monthly_repayment.index:
            df = months_per_tax_year(y)
            df["balance_change"] = average_monthly_repayment[y]
            repayments_averaged_over_tax_year = repayments_averaged_over_tax_year.append(
                df
            )

        repayments_averaged_over_tax_year.set_index(["tax_year"], inplace=True)

        if assume_payment_made_day_of_month == "last":
            days = repayments_averaged_over_tax_year["year_month"].apply(
                lambda x: calendar.monthrange(
                    int(x.split("-")[0]), int(x.split("-")[1])
                )[1]
            )
            repayments_averaged_over_tax_year["date"] = pd.to_datetime(
                repayments_averaged_over_tax_year["year_month"] + "-" + days.astype(str)
            )
            repayments_averaged_over_tax_year = repayments_averaged_over_tax_year.set_index(
                ["date"]
            )
        else:
            repayments_averaged_over_tax_year["date"] = pd.to_datetime(
                repayments_averaged_over_tax_year["year_month"]
                + "-"
                + str(assume_payment_made_day_of_month),
                format="%Y-%m-%d",
            )
            repayments_averaged_over_tax_year = repayments_averaged_over_tax_year.set_index(
                ["date"]
            )

        events = repayments_averaged_over_tax_year.append([pre_2019_pos, post_2019])
        events.sort_index(inplace=True)

    earliest_date = min(min(events.index), min(interest_rates.index))
    latest_date = max(max(events.index), max(interest_rates.index))

    daily = pd.date_range(earliest_date, latest_date, freq="D")

    df_daily = events.reindex(daily)
    interest_rates = interest_rates.reindex(daily)

    df_daily["balance_change"] = df_daily["balance_change"].fillna(0)
    df_daily["rate"] = interest_rates["rate"].fillna(method="ffill")

    all_rows = pd.DataFrame()

    yesterday_balance = 0

    for row in df_daily.itertuples():
        daily_interest_rate = (1 + (row.rate) / 100) ** (
            1 / get_days(row.Index.year)
        ) - 1

        interest_added_today = yesterday_balance * daily_interest_rate

        balance = yesterday_balance + row.balance_change + interest_added_today

        this_row = pd.DataFrame(
            {
                "date": [row.Index],
                "payments": row.balance_change,
                "annual_interest_rate": row.rate,
                "calculated_daily_interest"
                + assumptions_string: [interest_added_today],
                "calculated_balance" + assumptions_string: [balance],
            }
        )
        all_rows = pd.concat([all_rows, this_row])

        yesterday_balance = balance

    all_rows.columns = [col + assumptions_string for col in all_rows.columns]
    return all_rows


def clean_up_overall_df(df):
    columns_only_needed_once = ["date", "annual_interest_rate"]
    for col in columns_only_needed_once:
        all_these_cols = [c for c in df.columns if col in c]
        all_these_cols_to_drop = all_these_cols[1:]
        df.drop(columns=all_these_cols_to_drop, inplace=True)
        df.rename(columns={all_these_cols[0]: col}, inplace=True)
    return df


def compare_with_reported_interest(df):
    df = df.set_index("date")
    df = df[
        [col for col in df.columns if (col.startswith("calculated_daily_interest"))]
    ]
    df = df.groupby(pd.Grouper(freq="M")).sum()
    years_and_months = list(zip(df.index.year, df.index.month))
    years_and_months = [str(x[0]) + "-" + str(x[1]).zfill(2) for x in years_and_months]
    df.index = pd.Index(years_and_months)
    for col in df.columns:
        if "calculated_daily_interest" in col:
            df.rename(
                columns={
                    col: col.replace(
                        "calculated_daily_interest", "calculated_monthly_interest"
                    )
                },
                inplace=True,
            )

    reported_interest_added = pd.read_csv(
        os.path.join(data_path, loan, "inputs", "reported_interest_added.csv"),
        parse_dates=True,
    )
    reported_interest_added.index = reported_interest_added["date"].apply(
        lambda x: x.split("/")[2] + "-" + x.split("/")[1]
    )

    df["reported_interest_added_this_month"] = reported_interest_added[
        "reported_interest_added_this_month"
    ]

    df = convert_floats_to_2_dps(df)

    df.to_csv(
        os.path.join(
            data_path,
            loan,
            "outputs",
            "comparison_calculated_reported_monthly_interest.csv",
        )
    )


def compare_with_reported_balances(df):
    df = df.set_index("date")
    df = df[[col for col in df.columns if (col.startswith("calculated_balance_"))]]
    reported_balances = pd.read_csv(
        os.path.join(data_path, loan, "inputs", "reported_balances.csv"),
        parse_dates=True,
    )

    reported_balances["date"] = pd.to_datetime(reported_balances["date"])
    reported_balances.set_index(["date"], drop=True, inplace=True)

    df["reported_balance"] = reported_balances["reported_balance"]

    df.dropna(subset=["reported_balance"], inplace=True)

    df = convert_floats_to_2_dps(df)

    df.to_csv(
        os.path.join(
            data_path, loan, "outputs", "comparison_calculated_reported_balances.csv"
        ),
    )
