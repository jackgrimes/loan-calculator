import os
from calendar import monthrange
from datetime import date

import pandas as pd

from configs import data_path, months_dict


def get_days(year):
    DATE_END = date(year, 12, 31)
    DATE_START = date(year - 1, 12, 31)
    return (DATE_END - DATE_START).days


def get_and_prep_data():
    # Read in and clean up data

    events = pd.read_csv(
        os.path.join(data_path, "loan_events.csv"), parse_dates=["date"]
    )
    events.set_index("date", inplace=True)

    interest_rates = pd.read_csv(
        os.path.join(data_path, "interest_rates.csv"), parse_dates=["date"]
    )
    interest_rates.set_index("date", inplace=True)

    reported_interest_added = pd.read_csv(
        os.path.join(data_path, "reported_interest_added.csv"), parse_dates=["date"]
    )
    reported_interest_added.set_index("date", inplace=True)

    return events, interest_rates, reported_interest_added


def compare_my_interest_estimates_with_reported(
    all_results, all_rows, assumptions_string
):

    # Compare calculated values with interest amounts from statements

    my_estimate_columns = [
        col
        for col in all_rows.columns
        for y in ["calculated_interest", "calculated_balance_end_of_month"]
        if col.startswith(y)
    ]

    my_estimate_of_interest_string = [
        col for col in my_estimate_columns if ("calculated_interest" in col)
    ][0]

    all_rows["interest_exactly_matched" + assumptions_string] = all_rows[
        my_estimate_of_interest_string
    ] == all_results["interest_applied_from_statement"].str.replace(
        "£", ""
    ).str.replace(
        ",", ""
    ).astype(
        float
    )
    all_rows["interest_estimate_within_1_percent" + assumptions_string] = (
        (
            all_rows[my_estimate_of_interest_string]
            .str.replace("£", "")
            .str.replace(",", "")
            .astype(float)
            - all_results["calculated_balance_end_of_month"]
            .str.replace("£", "")
            .str.replace(",", "")
            .astype(float)
        )
        / all_results["calculated_balance_end_of_month"]
        .str.replace("£", "")
        .str.replace(",", "")
        .astype(float)
    ).abs().fillna(0) < 0.01
    all_rows["interest_estimate_within_5_percent" + assumptions_string] = (
        (
            all_rows[my_estimate_of_interest_string]
            .str.replace("£", "")
            .str.replace(",", "")
            .astype(float)
            - all_results["interest_applied_from_statement"]
            .str.replace("£", "")
            .str.replace(",", "")
            .astype(float)
        )
        / all_results["interest_applied_from_statement"]
        .str.replace("£", "")
        .str.replace(",", "")
        .astype(float)
    ).abs().fillna(0) < 0.05
    return all_rows


def calculate_balances_and_interest_added(
    events,
    interest_rates,
    payments_divided_equally_over_tax_year,
    assume_payment_made_day_of_month,
    assumptions_string,
):

    start_balance = 0
    all_rows = pd.DataFrame()
    for row in df.itertuples():
        daily_interest = (1 + row.interest) ** (1 / get_days(row.Year))
        days_this_month = monthrange(row.Year, months_dict[row.monthname])[1]
        if pd.isnull(start_balance):
            start_balance = 0
        if not pd.isnull(row.BorrowDate):
            borrow_day = row.BorrowDate.day
            interest1 = start_balance * (daily_interest ** (borrow_day)) - start_balance
            interest2 = (
                (start_balance + interest1 + row.BorrowAmount)
                * (daily_interest ** (days_this_month - borrow_day))
                - row.BorrowAmount
                - start_balance
                - interest1
            )
            # total_interest = np.floor((interest1 + interest2)*100)/100
            total_interest = interest1 + interest2
            total_interest_rounded = round(total_interest, 2)
            start_balance = start_balance + total_interest + row.BorrowAmount
        elif (not pd.isnull(row.PayDate)) or (
            not pd.isnull(row.AverageMonthlyRepaymentOverTaxYear)
        ):
            pay_day = row.PayDate.day
            # If no payday (for example because pay is being divided over the rest of the tax year),
            # assume payday is 20th
            # Otherwise make assumptions about which pay day they were using when distributing payments
            # evenly over the tax year up until tax year 2019-2020
            if pd.isnull(pay_day):
                pay_day = 20
            if (assume_pay == "first") and (row.TaxYear < 2019):
                pay_day = 1
            if (assume_pay == "last") and (row.TaxYear < 2019):
                pay_day = monthrange(row.Year, row.monthnum)[1]
            interest1 = start_balance * (daily_interest ** (pay_day)) - start_balance
            if (not applying_logic_from_letter) or (row.TaxYear > 2018):
                interest2 = (
                    (start_balance + interest1 + row.RepaidAmount)
                    * (daily_interest ** (days_this_month - pay_day))
                    - row.RepaidAmount
                    - start_balance
                    - interest1
                )
            else:
                interest2 = (
                    (start_balance + interest1 + row.AverageMonthlyRepaymentOverTaxYear)
                    * (daily_interest ** (days_this_month - pay_day))
                    - row.AverageMonthlyRepaymentOverTaxYear
                    - start_balance
                    - interest1
                )

            total_interest = interest1 + interest2
            total_interest_rounded = round(total_interest, 2)
            if (not applying_logic_from_letter) or (row.TaxYear > 2018):
                start_balance = start_balance + total_interest + row.RepaidAmount
            else:
                start_balance = (
                    start_balance
                    + total_interest
                    + row.AverageMonthlyRepaymentOverTaxYear
                )
        else:
            total_interest = (
                start_balance * (daily_interest ** (days_this_month)) - start_balance
            )
            total_interest_rounded = round(total_interest, 2)
            start_balance = start_balance + total_interest

        this_row = pd.DataFrame(
            {
                "Year": [row.Year],
                "Month": [row.Month],
                "calculated_interest" + assumptions_string: [total_interest_rounded],
                "calculated_balance_end_of_month" + assumptions_string: [start_balance],
            }
        )
        all_rows = pd.concat([all_rows, this_row])

    all_rows.reset_index(drop=True, inplace=True)

    my_estimate_columns = [
        col
        for col in all_rows.columns
        for y in ["calculated_interest", "calculated_balance_end_of_month"]
        if col.startswith(y)
    ]

    for col in my_estimate_columns:
        all_rows[col].values[0] = 0
        all_rows[col] = all_rows[col].map("£{:,.2f}".format)

    return all_rows
