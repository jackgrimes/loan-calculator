# loan-calculator
Fo calculating balance of loans, taking into account borrowing, repayments, and interest rate changes
## Getting started 
1. Create conda environment from the environment.yml: From the project directory, execute: `conda env create -f environment.yml`
2. Set up the pre-commit:
    1. cd to project directory
    2. `pre-commit install --hook-type pre-commit`
3. Set `configs.py` as desired
    1. It must contain:
       1. `data_path` - path to folder
       2. `loan` - folder within data_path, for data for a particular loan
       3. `payments_divided_equally_over_tax_year_list` - list of booleans, assumptions to use in calculations
       4. `paydays_if_allocating_pay_evenly_over_tax_year` - list of integers, days of month to calculate payment as being made if pay is distributed evenly across the tax year (can include the string `last` for the last day of each month)
4. Add data with right format
4. Run `main.py`!
