import os

from configs import data_path
from utils import (
    calculate_balances_and_interest_added,
    compare_my_interest_estimates_with_reported,
    get_and_prep_data,
)


def loan_calculator_runner():
    events, interest, reported_interest_added = get_and_prep_data()

    # Try all the combinations of assumptions:
    # 1. getting paid on first day of the month, pay over the tax year being averaged
    # 2. evenly distributed over the months of the tax year

    for payments_divided_equally_over_tax_year in [False, True]:
        for assume_payment_made_day_of_month in [None, "first", "last"]:
            assumptions_string = (
                ""
                + payments_divided_equally_over_tax_year
                * "_payments_divided_equally_over_tax_year"
                + "_assume_pay_"
                + str(assume_payment_made_day_of_month)
            )
            _ = calculate_balances_and_interest_added(
                # df,
                payments_divided_equally_over_tax_year,
                assume_payment_made_day_of_month,
                assumptions_string,
            )

            res = compare_my_interest_estimates_with_reported(
                # all_results, this_assumption_set_results, assumptions_string
            )

            # all_results = pd.merge(all_results, all_rows, on=["Year", "Month"])

    res.to_csv(
        os.path.join(data_path, "calculated_balances_under_various_assumptions.csv",),
        encoding="utf-8-sig",
        index=False,
    )


if __name__ == "__main__":
    loan_calculator_runner()
