from django.db import models


class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age = models.IntegerField(null=True, blank=True)
    phone_number = models.BigIntegerField()
    monthly_salary = models.IntegerField()
    approved_limit = models.IntegerField()
    current_debt = models.FloatField(default=0.0)

    class Meta:
        db_table = 'customers'

    def __str__(self):
        return f"{self.first_name} {self.last_name} (ID: {self.customer_id})"


class Loan(models.Model):
    loan_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    loan_amount = models.FloatField()
    tenure = models.IntegerField(help_text="Tenure in months")
    interest_rate = models.FloatField()
    monthly_repayment = models.FloatField()
    emis_paid_on_time = models.IntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'loans'

    def __str__(self):
        return f"Loan {self.loan_id} for Customer {self.customer_id}"

    @property
    def repayments_left(self):
        from datetime import date
        if self.end_date and self.end_date > date.today():
            today = date.today()
            months_remaining = (self.end_date.year - today.year) * 12 + (self.end_date.month - today.month)
            return max(0, months_remaining)
        return 0

    @property
    def is_active(self):
        from datetime import date
        if self.end_date:
            return self.end_date >= date.today()
        return True
