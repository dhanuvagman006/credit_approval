from datetime import date
from credit_app.models import Customer, Loan


def calculate_credit_score(customer: Customer) -> int:
    """
    Calculate credit score (0-100) based on historical loan data.

    Components:
      1. Past loans paid on time (ratio)
      2. Number of loans taken in past
      3. Loan activity in current year
      4. Loan approved volume vs approved limit
      5. If current debt > approved limit → score = 0
    """
    loans = customer.loans.all()

    active_loans = [l for l in loans if l.is_active]
    current_debt = sum(l.loan_amount for l in active_loans)
    if current_debt > customer.approved_limit:
        return 0

    if not loans.exists():
        return 50  

    total_loans = loans.count()
    total_emis = sum(l.tenure for l in loans if l.tenure)
    emis_paid_on_time = sum(l.emis_paid_on_time for l in loans)

    on_time_ratio = emis_paid_on_time / total_emis if total_emis > 0 else 0
    score_on_time = on_time_ratio * 35

    loan_count_score = max(0, 20 - (total_loans * 2))

    current_year = date.today().year
    current_year_loans = [l for l in loans if l.start_date and l.start_date.year == current_year]
    activity_score = max(0, 20 - (len(current_year_loans) * 4))

    total_loan_volume = sum(l.loan_amount for l in loans)
    if customer.approved_limit > 0:
        volume_ratio = total_loan_volume / customer.approved_limit
        if volume_ratio <= 1.0:
            volume_score = 25 * (1 - abs(volume_ratio - 0.5))
        else:
            volume_score = max(0, 25 - (volume_ratio - 1) * 25)
    else:
        volume_score = 0

    total_score = score_on_time + loan_count_score + activity_score + volume_score
    return min(100, max(0, round(total_score)))


def get_loan_approval(credit_score: int, interest_rate: float, monthly_emis: float, monthly_salary: float):
    """
    Determine loan approval status and corrected interest rate.

    Returns: (approved: bool, corrected_rate: float, message: str)
    """
    if monthly_salary > 0 and monthly_emis > 0.5 * monthly_salary:
        return False, interest_rate, "Total EMIs exceed 50% of monthly salary."

    if credit_score > 50:
        return True, interest_rate, "Loan approved."

    elif 30 < credit_score <= 50:
        if interest_rate > 12:
            return True, interest_rate, "Loan approved."
        else:
            corrected = 12.0
            return True, corrected, "Interest rate corrected to minimum 12% for your credit score."

    elif 10 < credit_score <= 30:
        if interest_rate > 16:
            return True, interest_rate, "Loan approved."
        else:
            corrected = 16.0
            return True, corrected, "Interest rate corrected to minimum 16% for your credit score."

    else: 
        return False, interest_rate, "Credit score too low to approve any loan."


def calculate_monthly_installment(loan_amount: float, annual_interest_rate: float, tenure_months: int) -> float:
    """
    Calculate EMI using compound interest (standard EMI formula).

    EMI = P * r * (1+r)^n / ((1+r)^n - 1)
    where r = monthly interest rate, n = tenure in months
    """
    if tenure_months <= 0:
        return 0.0

    monthly_rate = annual_interest_rate / (12 * 100)

    if monthly_rate == 0:
        return round(loan_amount / tenure_months, 2)

    emi = loan_amount * monthly_rate * ((1 + monthly_rate) ** tenure_months) / \
          (((1 + monthly_rate) ** tenure_months) - 1)
    return round(emi, 2)
