from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta

from .models import Customer, Loan
from .services import calculate_credit_score, get_loan_approval, calculate_monthly_installment


class CalculateMontlyInstallmentTest(TestCase):
    def test_basic_emi(self):
        emi = calculate_monthly_installment(100000, 12, 12)
        self.assertAlmostEqual(emi, 8884.88, places=1)

    def test_zero_interest(self):
        emi = calculate_monthly_installment(12000, 0, 12)
        self.assertAlmostEqual(emi, 1000.0, places=2)

    def test_zero_tenure(self):
        emi = calculate_monthly_installment(100000, 12, 0)
        self.assertEqual(emi, 0.0)


class CreditScoreTest(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name='Test', last_name='User',
            phone_number=9999999999,
            monthly_salary=50000,
            approved_limit=1800000,
            current_debt=0,
        )

    def test_no_loans_returns_neutral_score(self):
        score = calculate_credit_score(self.customer)
        self.assertEqual(score, 50)

    def test_debt_exceeds_limit_returns_zero(self):
        self.customer.current_debt = 0
        # Create active loan exceeding approved limit
        Loan.objects.create(
            customer=self.customer,
            loan_amount=2000000,
            tenure=12,
            interest_rate=10,
            monthly_repayment=17584,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
        )
        score = calculate_credit_score(self.customer)
        self.assertEqual(score, 0)

    def test_score_with_good_history(self):
        # Past loan, fully paid on time
        Loan.objects.create(
            customer=self.customer,
            loan_amount=100000,
            tenure=12,
            interest_rate=10,
            monthly_repayment=8792,
            emis_paid_on_time=12,
            start_date=date(2022, 1, 1),
            end_date=date(2022, 12, 31),
        )
        score = calculate_credit_score(self.customer)
        self.assertGreater(score, 30)


class GetLoanApprovalTest(TestCase):
    def test_high_credit_score_approved(self):
        approved, rate, msg = get_loan_approval(60, 10, 5000, 50000)
        self.assertTrue(approved)
        self.assertEqual(rate, 10)

    def test_medium_score_corrects_rate(self):
        approved, rate, msg = get_loan_approval(40, 8, 5000, 50000)
        self.assertTrue(approved)
        self.assertEqual(rate, 12.0)

    def test_low_medium_score_corrects_rate(self):
        approved, rate, msg = get_loan_approval(20, 10, 5000, 50000)
        self.assertTrue(approved)
        self.assertEqual(rate, 16.0)

    def test_very_low_score_rejected(self):
        approved, rate, msg = get_loan_approval(5, 20, 5000, 50000)
        self.assertFalse(approved)

    def test_emi_exceeds_50_percent_rejected(self):
        # EMI = 26000, salary = 50000 → 52% > 50%
        approved, rate, msg = get_loan_approval(80, 10, 26000, 50000)
        self.assertFalse(approved)


class RegisterAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_customer(self):
        response = self.client.post('/register', {
            'first_name': 'John',
            'last_name': 'Doe',
            'age': 30,
            'monthly_income': 50000,
            'phone_number': 9876543210,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIn('customer_id', data)
        self.assertEqual(data['approved_limit'], 1800000)  # 36 * 50000 = 1800000

    def test_register_approved_limit_rounded_to_lakh(self):
        response = self.client.post('/register', {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'age': 25,
            'monthly_income': 47000,
            'phone_number': 9111111111,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        # 36 * 47000 = 1692000 → rounded to nearest lakh = 1700000
        self.assertEqual(data['approved_limit'], 1700000)

    def test_register_missing_fields(self):
        response = self.client.post('/register', {
            'first_name': 'John',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CheckEligibilityAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(
            first_name='Alice', last_name='Wonderland',
            phone_number=9000000001,
            monthly_salary=80000,
            approved_limit=2880000,
            current_debt=0,
        )

    def test_check_eligibility_customer_not_found(self):
        response = self.client.post('/check-eligibility', {
            'customer_id': 99999,
            'loan_amount': 100000,
            'interest_rate': 10,
            'tenure': 12,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_check_eligibility_valid(self):
        response = self.client.post('/check-eligibility', {
            'customer_id': self.customer.customer_id,
            'loan_amount': 100000,
            'interest_rate': 10,
            'tenure': 12,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('approval', data)
        self.assertIn('corrected_interest_rate', data)
        self.assertIn('monthly_installment', data)


class CreateLoanAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(
            first_name='Bob', last_name='Builder',
            phone_number=9000000002,
            monthly_salary=100000,
            approved_limit=3600000,
            current_debt=0,
        )
        # Create good loan history
        Loan.objects.create(
            customer=self.customer,
            loan_amount=200000,
            tenure=24,
            interest_rate=10,
            monthly_repayment=9227,
            emis_paid_on_time=24,
            start_date=date(2021, 1, 1),
            end_date=date(2022, 12, 31),
        )

    def test_create_loan_approved(self):
        response = self.client.post('/create-loan', {
            'customer_id': self.customer.customer_id,
            'loan_amount': 500000,
            'interest_rate': 14,
            'tenure': 24,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertTrue(data['loan_approved'])
        self.assertIsNotNone(data['loan_id'])

    def test_create_loan_customer_not_found(self):
        response = self.client.post('/create-loan', {
            'customer_id': 99999,
            'loan_amount': 100000,
            'interest_rate': 10,
            'tenure': 12,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ViewLoanAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(
            first_name='Charlie', last_name='Chaplin',
            phone_number=9000000003,
            monthly_salary=60000,
            approved_limit=2160000,
            current_debt=0,
        )
        self.loan = Loan.objects.create(
            customer=self.customer,
            loan_amount=300000,
            tenure=12,
            interest_rate=10,
            monthly_repayment=26376,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
        )

    def test_view_loan(self):
        response = self.client.get(f'/view-loan/{self.loan.loan_id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['loan_id'], self.loan.loan_id)
        self.assertIn('customer', data)
        self.assertEqual(data['customer']['first_name'], 'Charlie')

    def test_view_loan_not_found(self):
        response = self.client.get('/view-loan/99999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_view_loans_by_customer(self):
        response = self.client.get(f'/view-loans/{self.customer.customer_id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertIn('repayments_left', data[0])
