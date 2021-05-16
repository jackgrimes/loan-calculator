import os

import pandas as pd

from configs import data_path
from utils import (
    calculate_balances_and_interest_added,
    get_and_prep_data,
)


def loan_calculator_runner():
    events, interest_rates, reported_interest_added = get_and_prep_data()

    # Try all the combinations of assumptions:
    # 1. getting paid on first day of the month, pay over the tax year being averaged
    # 2. evenly distributed over the months of the tax year

    # todo: payment on last day of month

    list_of_dfs = []

    for payments_divided_equally_over_tax_year in [False, True]:
        for assume_payment_made_day_of_month in [1, 20]:
            assumptions_string = (
                ""
                + payments_divided_equally_over_tax_year
                * "_payments_divided_equally_over_tax_year"
                + "_assume_pay_"
                + str(assume_payment_made_day_of_month)
            )
            list_of_dfs.append(
                calculate_balances_and_interest_added(
                    events,
                    interest_rates,
                    payments_divided_equally_over_tax_year,
                    assume_payment_made_day_of_month,
                    assumptions_string,
                )
            )

    all_calculations = pd.concat(list_of_dfs, axis=1)

    # todo: add in reported interest added and balances

    all_calculations.to_csv(
        os.path.join(data_path, "calculated_balances_under_various_assumptions.csv",),
        encoding="utf-8-sig",
        index=False,
    )


if __name__ == "__main__":
    loan_calculator_runner()
