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

"""School email integration tool for Cordos Elementary School communications."""

import datetime
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-2052da07f961"


def fetch_cordos_elementary_emails(filter_query: str = "Cordos Elementary") -> str:
    """Fetches and digests recent school emails specifically from Cordos Elementary School.

    Args:
        filter_query: Search or filter term for school emails (default: 'Cordos Elementary').

    Returns:
        A structured summary of recent Cordos Elementary School emails including sender, subject, date, and key takeaways.
    """
    # Demo email feed simulating parent inbox integration for Cordos Elementary School
    emails = [
        {
            "id": "eml_101",
            "sender": "Principal Vance <principal@cordoselementary.edu>",
            "subject": "Cordos Elementary Weekly Digest - Back to School Night & Drop-off Safety",
            "date": "2026-08-13",
            "school": "Cordos Elementary School",
            "category": "Announcement",
            "summary": "Back to School Night is scheduled for next Tuesday at 6:30 PM in the Cordos Auditorium. Carpool drop-off lane hours are strictly 7:45 AM - 8:15 AM.",
            "action_items": ["Attend Back to School Night", "Review new carpool map"],
        },
        {
            "id": "eml_102",
            "sender": "Mrs. Davis (3rd Grade Teacher) <davis.c@cordoselementary.edu>",
            "subject": "3rd Grade Weekly Homework & Science Fair Kickoff - Leo's Class",
            "date": "2026-08-13",
            "school": "Cordos Elementary School",
            "category": "Classwork & Homework",
            "summary": "Math Worksheet Page 42 due Friday. Science fair proposal forms distributed today—please sign and return by Monday. 20 mins daily reading required.",
            "action_items": ["Complete Math Page 42", "Sign Science Fair proposal form"],
        },
        {
            "id": "eml_103",
            "sender": "Nurse Brenda <nurse@cordoselementary.edu>",
            "subject": "IMPORTANT: Cordos Elementary Health & Immunization Form Reminder",
            "date": "2026-08-12",
            "school": "Cordos Elementary School",
            "category": "Health & Medical",
            "summary": "Updated annual health check forms and EpiPen/allergy action plans must be submitted to the nurse office by September 1.",
            "action_items": ["Submit updated health forms", "Check allergy medication expiration date"],
        },
    ]

    matching_emails = [
        e for e in emails if filter_query.lower() in e["school"].lower() or filter_query.lower() in e["subject"].lower() or filter_query.lower() in e["summary"].lower()
    ]

    if not matching_emails:
        matching_emails = emails

    output = [f"📧 Cordos Elementary School Email Digest ({len(matching_emails)} messages found):"]
    for email in matching_emails:
        output.append(
            f"\n• Subject: {email['subject']}\n"
            f"  From: {email['sender']} | Date: {email['date']}\n"
            f"  Summary: {email['summary']}\n"
            f"  Action Items: {', '.join(email['action_items'])}"
        )

    # Automatically persist to Firestore school_announcements collection
    try:
        db = firestore.Client(project=PROJECT_ID)
        for email in matching_emails:
            doc_id = f"cordos_{email['id']}"
            db.collection("school_announcements").document(doc_id).set(
                {
                    "source": "Cordos Elementary Email",
                    "title": email["subject"],
                    "content": email["summary"],
                    "priority": "urgent" if email["category"] == "Health & Medical" else "normal",
                    "date": email["date"],
                    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                },
                merge=True,
            )
    except Exception:
        pass

    return "\n".join(output)
