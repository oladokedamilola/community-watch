# reports/management/commands/geocode_reports.py
from django.core.management.base import BaseCommand
from reports.geocoding_utils import batch_geocode_existing_reports


class Command(BaseCommand):
    help = 'Geocode existing reports that lack coordinates'

    def handle(self, *args, **options):
        self.stdout.write('Starting geocoding for existing reports...')
        
        updated = batch_geocode_existing_reports()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully geocoded {updated} reports'))