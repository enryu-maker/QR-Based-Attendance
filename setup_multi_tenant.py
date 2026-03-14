import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qr_attendance_system.settings")
django.setup()

from django.contrib.auth.models import User
from core.models import Company, Employee, OfficeLocation, Holiday

def setup():
    # 1. Create Superuser
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("Superuser 'admin' created.")

    # 2. Create Company Admin User
    if not User.objects.filter(username='demo_admin').exists():
        user = User.objects.create_user('demo_admin', 'demo@attendflow.io', 'demo123')
        print("Company admin 'demo_admin' created.")
    else:
        user = User.objects.get(username='demo_admin')

    # 3. Create Company
    company, created = Company.objects.get_or_create(
        name="AttendOS Demo Corp",
        admin_user=user
    )
    if created:
        print(f"Company '{company.name}' created.")

    # 4. Create Office Location
    OfficeLocation.objects.get_or_create(
        company=company,
        name="Tech Park Office",
        latitude=28.5355,
        longitude=77.3910,
        max_distance_meters=200
    )

    # 5. Create Sample Employee
    Employee.objects.get_or_create(
        company=company,
        employee_id="EMP001",
        first_name="John",
        last_name="Doe",
        email="john@attendflow.io",
        monthly_salary=45000
    )

    print("Setup complete!")

if __name__ == "__main__":
    setup()
