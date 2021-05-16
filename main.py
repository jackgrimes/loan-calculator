import os

import pandas as pd

from configs import (
    data_path,
    loan,
    payments_divided_equally_over_tax_year_list,
    paydays_if_allocating_pay_evenly_over_tax_year,
)
from utils import (
    calculate_balances_and_interest_added,
    get_and_prep_data,
    clean_up_overall_df,
    compare_with_reported_interest,
    compare_with_reported_balances,
    convert_floats_to_2_dps,
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

    compare_with_reported_interest(all_calculations)

    compare_with_reported_balances(all_calculations)

    all_calculations = convert_floats_to_2_dps(all_calculations)

    all_calculations.to_csv(
        os.path.join(
            data_path,
            loan,
            "outputs",
            "calculated_balances_under_various_assumptions.csv",
        ),
        encoding="utf-8-sig",
        index=False,
    )


if __name__ == "__main__":
    loan_calculator_runner()
