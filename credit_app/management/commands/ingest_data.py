from django.core.management.base import BaseCommand
from credit_app.tasks import ingest_customer_data, ingest_loan_data


class Command(BaseCommand):
    help = 'Ingest customer and loan data from Excel files using background tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Run ingestion synchronously (without Celery)',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting data ingestion...')

        if options['sync']:
            # Run synchronously (useful when Celery is not available)
            self.stdout.write('Running customer ingestion synchronously...')
            result1 = ingest_customer_data()
            self.stdout.write(self.style.SUCCESS(f'Customer ingestion: {result1}'))

            self.stdout.write('Running loan ingestion synchronously...')
            result2 = ingest_loan_data()
            self.stdout.write(self.style.SUCCESS(f'Loan ingestion: {result2}'))
        else:
            # Dispatch to Celery workers
            task1 = ingest_customer_data.delay()
            self.stdout.write(f'Customer ingestion task dispatched: {task1.id}')

            task2 = ingest_loan_data.delay()
            self.stdout.write(f'Loan ingestion task dispatched: {task2.id}')

        self.stdout.write(self.style.SUCCESS('Data ingestion initiated.'))
