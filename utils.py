import os
from datetime import date

import pandas as pd

from configs import data_path


def get_days(year):
    DATE_END = date(year, 12, 31)
    DATE_START = date(year - 1, 12, 31)
    return (DATE_END - DATE_START).days


def get_and_prep_data():
    # Read in and clean up data

    events = pd.read_csv(
        os.path.join(data_path, "loan_events.csv"),
        dayfirst=True,
        parse_dates=True,
        index_col=["date"],
    )

    interest_rates = pd.read_csv(
        os.path.join(data_path, "interest_rates.csv"),
        parse_dates=True,
        index_col=["date"],
    )

    reported_interest_added = pd.read_csv(
        os.path.join(data_path, "reported_interest_added.csv"),
        parse_dates=True,
        index_col=["date"],
        dayfirst=True,
    )

    return events, interest_rates, reported_interest_added


def months_per_tax_year(y):
    df = pd.DataFrame()
    year_months = [f"{y}-{x}" for x in range(4, 13)]
    year_months.extend([f"{y + 1}-{x}" for x in range(1, 4)])
    df["year_month"] = pd.Series(year_months)
    df["tax_year"] = y
    return df


def calculate_balances_and_interest_added(
    events,
    interest_rates,
    payments_divided_equally_over_tax_year,
    assume_payment_made_day_of_month,
    assumptions_string,
):

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
