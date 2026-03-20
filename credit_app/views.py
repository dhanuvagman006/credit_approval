import math
from datetime import date

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Customer, Loan
from .serializers import (
    RegisterRequestSerializer,
    CheckEligibilityRequestSerializer,
    CreateLoanRequestSerializer,
    ViewLoanResponseSerializer,
    ViewLoansItemSerializer,
)
from .services import (
    calculate_credit_score,
    get_loan_approval,
    calculate_monthly_installment,
)


class RegisterView(APIView):
    """POST /register - Register a new customer."""

    def post(self, request):
        serializer = RegisterRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # approved_limit = 36 * monthly_salary, rounded to nearest lakh (100,000)
        raw_limit = 36 * data['monthly_income']
        approved_limit = round(raw_limit / 100000) * 100000

        customer = Customer.objects.create(
            first_name=data['first_name'],
            last_name=data['last_name'],
            age=data['age'],
            phone_number=data['phone_number'],
            monthly_salary=data['monthly_income'],
            approved_limit=approved_limit,
            current_debt=0.0,
        )

        return Response({
            'customer_id': customer.customer_id,
            'name': f"{customer.first_name} {customer.last_name}",
            'age': customer.age,
            'monthly_income': customer.monthly_salary,
            'approved_limit': customer.approved_limit,
            'phone_number': customer.phone_number,
        }, status=status.HTTP_201_CREATED)


class CheckEligibilityView(APIView):
    """POST /check-eligibility - Check loan eligibility."""

    def post(self, request):
        serializer = CheckEligibilityRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        try:
            customer = Customer.objects.get(customer_id=data['customer_id'])
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)

        credit_score = calculate_credit_score(customer)

        active_loans = [l for l in customer.loans.all() if l.is_active]
        current_emis = sum(l.monthly_repayment for l in active_loans)

        new_emi = calculate_monthly_installment(
            data['loan_amount'], data['interest_rate'], data['tenure']
        )
        total_emis = current_emis + new_emi

        approved, corrected_rate, message = get_loan_approval(
            credit_score, data['interest_rate'], total_emis, customer.monthly_salary
        )

        final_emi = calculate_monthly_installment(
            data['loan_amount'], corrected_rate, data['tenure']
        )

        return Response({
            'customer_id': customer.customer_id,
            'approval': approved,
            'interest_rate': data['interest_rate'],
            'corrected_interest_rate': corrected_rate,
            'tenure': data['tenure'],
            'monthly_installment': final_emi,
        }, status=status.HTTP_200_OK)


class CreateLoanView(APIView):
    """POST /create-loan - Create a new loan."""

    def post(self, request):
        serializer = CreateLoanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        try:
            customer = Customer.objects.get(customer_id=data['customer_id'])
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)

        credit_score = calculate_credit_score(customer)

        active_loans = [l for l in customer.loans.all() if l.is_active]
        current_emis = sum(l.monthly_repayment for l in active_loans)

        new_emi = calculate_monthly_installment(
            data['loan_amount'], data['interest_rate'], data['tenure']
        )
        total_emis = current_emis + new_emi

        approved, corrected_rate, message = get_loan_approval(
            credit_score, data['interest_rate'], total_emis, customer.monthly_salary
        )

        if not approved:
            return Response({
                'loan_id': None,
                'customer_id': customer.customer_id,
                'loan_approved': False,
                'message': message,
                'monthly_installment': 0.0,
            }, status=status.HTTP_200_OK)

        final_emi = calculate_monthly_installment(
            data['loan_amount'], corrected_rate, data['tenure']
        )

        start_date = date.today()
        end_month = start_date.month + data['tenure']
        end_year = start_date.year + (end_month - 1) // 12
        end_month = ((end_month - 1) % 12) + 1
        try:
            end_date = start_date.replace(year=end_year, month=end_month)
        except ValueError:
            import calendar
            last_day = calendar.monthrange(end_year, end_month)[1]
            end_date = start_date.replace(year=end_year, month=end_month, day=last_day)

        loan = Loan.objects.create(
            customer=customer,
            loan_amount=data['loan_amount'],
            tenure=data['tenure'],
            interest_rate=corrected_rate,
            monthly_repayment=final_emi,
            emis_paid_on_time=0,
            start_date=start_date,
            end_date=end_date,
        )

        return Response({
            'loan_id': loan.loan_id,
            'customer_id': customer.customer_id,
            'loan_approved': True,
            'message': message,
            'monthly_installment': final_emi,
        }, status=status.HTTP_201_CREATED)


class ViewLoanView(APIView):
    """GET /view-loan/<loan_id> - View loan + customer details."""

    def get(self, request, loan_id):
        try:
            loan = Loan.objects.select_related('customer').get(loan_id=loan_id)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found.'}, status=status.HTTP_404_NOT_FOUND)

        customer = loan.customer
        return Response({
            'loan_id': loan.loan_id,
            'customer': {
                'id': customer.customer_id,
                'first_name': customer.first_name,
                'last_name': customer.last_name,
                'phone_number': customer.phone_number,
                'age': customer.age,
            },
            'loan_amount': loan.loan_amount,
            'interest_rate': loan.interest_rate,
            'monthly_installment': loan.monthly_repayment,
            'tenure': loan.tenure,
        }, status=status.HTTP_200_OK)


class ViewLoansView(APIView):
    """GET /view-loans/<customer_id> - View all current loans for a customer."""

    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)

        active_loans = [loans for loans in customer.loans.all() if loans.is_active]

        result = []
        for loan in active_loans:
            result.append({
                'loan_id': loan.loan_id,
                'loan_amount': loan.loan_amount,
                'interest_rate': loan.interest_rate,
                'monthly_installment': loan.monthly_repayment,
                'repayments_left': loan.repayments_left,
            })

        return Response(result, status=status.HTTP_200_OK)
