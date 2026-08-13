# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Seed script to populate Firestore collections with sample data."""

import datetime
from google.cloud import firestore

# HARDCODED PROJECT ID as required by Agent Platform
PROJECT_ID = "qwiklabs-gcp-03-2052da07f961"


def seed_database():
    """Populates Firestore collections with initial seed data."""
    print(f"Connecting to Firestore for project '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)

    # 1. Evening Activities Collection
    evening_activities = [
        {
            "child_name": "Leo",
            "title": "Complete Math Worksheet (Page 42)",
            "category": "homework",
            "due_time": "7:30 PM",
            "points": 15,
            "completed": False,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "child_name": "Leo",
            "title": "Read 20 minutes of 'The Magic Treehouse'",
            "category": "reading",
            "due_time": "8:00 PM",
            "points": 10,
            "completed": False,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "child_name": "Leo",
            "title": "Take Evening Allergy Medicine (5ml Claritin)",
            "category": "medicine",
            "due_time": "8:15 PM",
            "points": 10,
            "completed": False,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    ]

    print("Seeding 'evening_activities' collection...")
    for item in evening_activities:
        db.collection("evening_activities").add(item)

    # 2. Medical Records Collection
    medical_records = [
        {
            "child_name": "Leo",
            "type": "checkup",
            "title": "Annual 8-Year Pediatric Physical Checkup",
            "doctor_name": "Dr. Sarah Jenkins (Valley Pediatrics)",
            "date": "2026-06-15",
            "followup_date": "2027-06-15",
            "notes": "Growth percentile: 75th. All vital signs normal. Vision 20/20.",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "child_name": "Leo",
            "type": "allergy",
            "title": "Mild Seasonal Allergy & Peanut Sensitivity",
            "doctor_name": "Dr. Mark Rivera (Allergy Specialist)",
            "date": "2026-03-10",
            "followup_date": "2027-03-10",
            "notes": "EpiPen prescribed for school nurse file. Refill due annually in March.",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "child_name": "Leo",
            "type": "vaccination",
            "title": "Annual Flu Vaccine & MMR Booster",
            "doctor_name": "Valley Pediatrics Clinic",
            "date": "2025-10-05",
            "followup_date": "2026-10-05",
            "notes": "Annual flu shot due October 2026.",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    ]

    print("Seeding 'medical_records' collection...")
    for item in medical_records:
        db.collection("medical_records").add(item)

    # 3. School Announcements Collection
    school_announcements = [
        {
            "source": "ParentSquare",
            "title": "Back to School Night & Science Fair Registration",
            "content": "Parent-teacher orientation next Tuesday at 6:30 PM. Register science fair projects by Friday.",
            "priority": "normal",
            "date": "2026-08-12",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "source": "School Nurse",
            "title": "Annual Health Forms & Immunization Record Due",
            "content": "Please submit updated annual health and emergency contact forms via ParentSquare before Sept 1.",
            "priority": "urgent",
            "date": "2026-08-11",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    ]

    print("Seeding 'school_announcements' collection...")
    for item in school_announcements:
        db.collection("school_announcements").add(item)

    print("✅ Firestore database seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
