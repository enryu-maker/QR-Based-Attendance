import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qr_attendance_system.settings")
django.setup()

from core.models import Holiday, Company

def seed():
    holidays = [
        ("Republic Day", "2026-01-26"),
        ("Holi", "2026-03-04"),
        ("Id-ul-Fitr (Eid)", "2026-03-21"),
        ("Ram Navami", "2026-03-26"),
        ("Good Friday", "2026-04-03"),
        ("Buddha Purnima", "2026-05-01"),
        ("Id-ul-Zuha (Bakrid)", "2026-05-27"),
        ("Independence Day", "2026-08-15"),
        ("Janmashtami", "2026-09-04"),
        ("Mahatma Gandhi Jayanti", "2026-10-02"),
        ("Dussehra", "2026-10-20"),
        ("Diwali (Deepavali)", "2026-11-08"),
        ("Guru Nanak Jayanti", "2026-11-24"),
        ("Christmas Day", "2026-12-25"),
    ]

    # Seed for all companies currently in system
    companies = Company.objects.all()
    for company in companies:
        for name, date in holidays:
            Holiday.objects.update_or_create(
                company=company, 
                date=date, 
                defaults={"name": name}
            )
        print(f"Holidays seeded for {company.name}")

    # Also seed as global (company=None)
    for name, date in holidays:
        Holiday.objects.update_or_create(
            company=None, 
            date=date, 
            defaults={"name": name}
        )
    print("Global holidays seeded.")

if __name__ == "__main__":
    seed()
