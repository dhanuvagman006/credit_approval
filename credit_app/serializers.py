from rest_framework import serializers
from .models import Customer, Loan


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['customer_id', 'first_name', 'last_name', 'age', 'phone_number',
                  'monthly_salary', 'approved_limit', 'current_debt']


class RegisterRequestSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    age = serializers.IntegerField(min_value=0)
    monthly_income = serializers.IntegerField(min_value=0)
    phone_number = serializers.IntegerField()


class RegisterResponseSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    name = serializers.CharField()
    age = serializers.IntegerField()
    monthly_income = serializers.IntegerField()
    approved_limit = serializers.IntegerField()
    phone_number = serializers.IntegerField()


class CheckEligibilityRequestSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.FloatField(min_value=0)
    interest_rate = serializers.FloatField(min_value=0)
    tenure = serializers.IntegerField(min_value=1)


class CheckEligibilityResponseSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    approval = serializers.BooleanField()
    interest_rate = serializers.FloatField()
    corrected_interest_rate = serializers.FloatField()
    tenure = serializers.IntegerField()
    monthly_installment = serializers.FloatField()


class CreateLoanRequestSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.FloatField(min_value=0)
    interest_rate = serializers.FloatField(min_value=0)
    tenure = serializers.IntegerField(min_value=1)


class CreateLoanResponseSerializer(serializers.Serializer):
    loan_id = serializers.IntegerField(allow_null=True)
    customer_id = serializers.IntegerField()
    loan_approved = serializers.BooleanField()
    message = serializers.CharField()
    monthly_installment = serializers.FloatField()


class CustomerInLoanSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='customer_id')

    class Meta:
        model = Customer
        fields = ['id', 'first_name', 'last_name', 'phone_number', 'age']


class ViewLoanResponseSerializer(serializers.ModelSerializer):
    loan_id = serializers.IntegerField()
    customer = CustomerInLoanSerializer()
    monthly_installment = serializers.FloatField(source='monthly_repayment')

    class Meta:
        model = Loan
        fields = ['loan_id', 'customer', 'loan_amount', 'interest_rate',
                  'monthly_installment', 'tenure']


class ViewLoansItemSerializer(serializers.ModelSerializer):
    loan_id = serializers.IntegerField()
    monthly_installment = serializers.FloatField(source='monthly_repayment')
    repayments_left = serializers.IntegerField()

    class Meta:
        model = Loan
        fields = ['loan_id', 'loan_amount', 'interest_rate',
                  'monthly_installment', 'repayments_left']
