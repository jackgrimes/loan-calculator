import os

import pandas as pd

from configs import (
    data_path,
    loan,
    payments_divided_equally_over_tax_year_list,
    paydays_if_allocating_pay_evenly_over_tax_year,
    comparing_interests,
    comparing_balances,
)
from utils import (
    calculate_balances_and_interest_added,
    get_and_prep_data,
    clean_up_overall_df,
    compare_with_reported_interest,
    compare_with_reported_balances,
    convert_floats_to_2_dps,
    output_all_calculations,
)
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%d-%b-%y %H:%M:%S"
)


def loan_calculator_runner():
    events, interest_rates, reported_interest_added = get_and_prep_data()

    # Try all the combinations of assumptions:
    # 1. getting paid on first day of the month, pay over the tax year being averaged
    # 2. evenly distributed over the months of the tax year

    list_of_dfs = []

    for (
        payments_divided_equally_over_tax_year
    ) in payments_divided_equally_over_tax_year_list:
        if payments_divided_equally_over_tax_year:
            for (
                assume_payment_made_day_of_month
            ) in paydays_if_allocating_pay_evenly_over_tax_year:
                list_of_dfs.append(
                    calculate_balances_and_interest_added(
                        events,
                        interest_rates,
                        payments_divided_equally_over_tax_year,
                        assume_payment_made_day_of_month,
                    )
                )
        else:
            list_of_dfs.append(
                calculate_balances_and_interest_added(
                    events,
                    interest_rates,
                    payments_divided_equally_over_tax_year,
                    assume_payment_made_day_of_month=None,
                )
            )

    all_calculations = pd.concat(list_of_dfs, axis=1)

    all_calculations = clean_up_overall_df(all_calculations)

    if comparing_interests:
        compare_with_reported_interest(all_calculations)

    if comparing_balances:
        compare_with_reported_balances(all_calculations)

    output_all_calculations(all_calculations)


if __name__ == "__main__":
    loan_calculator_runner()
