import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qr_attendance_system.settings")
django.setup()

from django.contrib.auth.models import User
from core.models import OfficeLocation, Employee

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("Superuser created (admin/admin123)")

if not OfficeLocation.objects.exists():
    # Example coordinates for somewhere
    OfficeLocation.objects.create(name='Main HQ', latitude=37.7749, longitude=-122.4194, max_distance_meters=1000)
    print("Office location created")

if not Employee.objects.exists():
    Employee.objects.create(employee_id='EMP001', first_name='John', last_name='Doe', email='john@example.com')
    print("Employee EMP001 created")
