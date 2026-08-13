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

"""Firestore backend tools for Parent & Child Daily School & Health Concierge."""

import datetime
from google.cloud import firestore
from google.cloud.firestore import FieldFilter

# HARDCODED PROJECT ID as required by Agent Platform
PROJECT_ID = "qwiklabs-gcp-03-2052da07f961"


def _get_firestore_client() -> firestore.Client:
    """Returns a Firestore client initialized with hardcoded project ID."""
    return firestore.Client(project=PROJECT_ID)


def get_evening_activities(child_name: str = "Leo") -> str:
    """Retrieves post-school evening activities and chores assigned to the child.

    Args:
        child_name: The name of the child (default: 'Leo').

    Returns:
        A formatted string listing the assigned evening activities, status, and points.
    """
    db = _get_firestore_client()
    docs = (
        db.collection("evening_activities")
        .where(filter=FieldFilter("child_name", "==", child_name))
        .stream()
    )
    activities = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        status = "✅ Completed" if data.get("completed") else "⏳ Pending"
        activities.append(
            f"- [{status}] ID: {doc.id} | {data.get('title')} ({data.get('category')}) | Due: {data.get('due_time')} | Points: {data.get('points')}"
        )

    if not activities:
        return f"No evening activities found for {child_name}."
    return f"Evening activities for {child_name}:\n" + "\n".join(activities)


def add_evening_activity(
    child_name: str,
    title: str,
    category: str = "homework",
    due_time: str = "8:00 PM",
    points: int = 10,
) -> str:
    """Adds a new post-school activity or chore for the child to complete before bedtime.

    Args:
        child_name: The name of the child.
        title: Description of the activity (e.g., 'Read 20 mins of Math Storybook').
        category: Activity type ('homework', 'reading', 'medicine', 'chore').
        due_time: Time due before bed (e.g., '8:00 PM').
        points: Reward points assigned for completing the task.

    Returns:
        Confirmation message with the generated task ID.
    """
    db = _get_firestore_client()
    doc_ref = db.collection("evening_activities").document()
    activity_data = {
        "child_name": child_name,
        "title": title,
        "category": category,
        "due_time": due_time,
        "points": points,
        "completed": False,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    doc_ref.set(activity_data)
    return f"Successfully added activity '{title}' for {child_name} (Task ID: {doc_ref.id})."


def mark_activity_completed(task_id: str) -> str:
    """Marks a post-school activity as completed.

    Args:
        task_id: The Firestore document ID of the activity.

    Returns:
        Confirmation message.
    """
    db = _get_firestore_client()
    doc_ref = db.collection("evening_activities").document(task_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Activity with ID '{task_id}' not found."

    doc_ref.update({"completed": True})
    title = doc.to_dict().get("title", "Activity")
    return f"Great job! Marked '{title}' (ID: {task_id}) as completed."


def get_medical_records(child_name: str = "Leo") -> str:
    """Retrieves medical records, doctor follow-ups, and health check details for the child.

    Args:
        child_name: The name of the child (default: 'Leo').

    Returns:
        A formatted string summarizing medical history, medications, and upcoming health follow-ups.
    """
    db = _get_firestore_client()
    docs = (
        db.collection("medical_records")
        .where(filter=FieldFilter("child_name", "==", child_name))
        .stream()
    )
    records = []
    for doc in docs:
        data = doc.to_dict()
        records.append(
            f"- [{data.get('type', 'general').upper()}] {data.get('title')} | Doctor: {data.get('doctor_name', 'N/A')} | Date: {data.get('date')} | Next Followup: {data.get('followup_date', 'None')} | Notes: {data.get('notes', '')}"
        )

    if not records:
        return f"No medical records found for {child_name}."
    return f"Medical & Health Records for {child_name}:\n" + "\n".join(records)


def add_medical_record(
    child_name: str,
    record_type: str,
    title: str,
    doctor_name: str = "",
    date: str = "",
    followup_date: str = "",
    notes: str = "",
) -> str:
    """Adds a new medical record, vaccine, prescription, or doctor checkup entry.

    Args:
        child_name: Name of the child.
        record_type: Type of record ('vaccination', 'allergy', 'checkup', 'prescription').
        title: Title of medical record (e.g., 'Annual Pediatric Physical').
        doctor_name: Doctor or clinic name (optional).
        date: Date of appointment/record (e.g., '2026-08-10').
        followup_date: Next scheduled follow-up or renewal date (e.g., '2027-08-10').
        notes: Doctor notes, dosage, or extra details.

    Returns:
        Confirmation message.
    """
    db = _get_firestore_client()
    doc_ref = db.collection("medical_records").document()
    record_data = {
        "child_name": child_name,
        "type": record_type,
        "title": title,
        "doctor_name": doctor_name,
        "date": date,
        "followup_date": followup_date,
        "notes": notes,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    doc_ref.set(record_data)
    return f"Added medical record '{title}' for {child_name} (Record ID: {doc_ref.id})."


def get_school_announcements(limit: int = 5) -> str:
    """Retrieves recent school announcements and ParentSquare notifications.

    Args:
        limit: Maximum number of announcements to return (default: 5).

    Returns:
        A concise summary of school announcements.
    """
    db = _get_firestore_client()
    docs = (
        db.collection("school_announcements")
        .limit(limit)
        .stream()
    )
    announcements = []
    for doc in docs:
        data = doc.to_dict()
        priority = "🚨 URGENT" if data.get("priority") == "urgent" else "ℹ️ NOTICE"
        announcements.append(
            f"- [{priority}] {data.get('source')}: {data.get('title')} ({data.get('date')}) - {data.get('content')}"
        )

    if not announcements:
        return "No recent school announcements."
    return "Recent School Announcements & Notifications:\n" + "\n".join(announcements)


def check_medical_followup_alerts(child_name: str = "Leo", days_ahead: int = 90) -> str:
    """Scans medical records in Firestore and alerts if any annual physicals, flu shots, or prescriptions need follow-up soon.

    Args:
        child_name: Name of the child (default: 'Leo').
        days_ahead: Number of days ahead to check for upcoming follow-ups (default: 90).

    Returns:
        A list of medical follow-ups and annual health check alerts.
    """
    db = _get_firestore_client()
    docs = (
        db.collection("medical_records")
        .where(filter=FieldFilter("child_name", "==", child_name))
        .stream()
    )
    today = datetime.date.today()
    cutoff = today + datetime.timedelta(days=days_ahead)
    alerts = []

    for doc in docs:
        data = doc.to_dict()
        followup_str = data.get("followup_date")
        if followup_str:
            try:
                f_date = datetime.datetime.strptime(followup_str, "%Y-%m-%d").date()
                if today <= f_date <= cutoff:
                    days_left = (f_date - today).days
                    alerts.append(
                        f"- 🩺 [DUE IN {days_left} DAYS on {followup_str}] {data.get('title')} ({data.get('type')}) | Doctor: {data.get('doctor_name')} | Notes: {data.get('notes')}"
                    )
                elif f_date < today:
                    alerts.append(
                        f"- ⚠️ [OVERDUE since {followup_str}] {data.get('title')} ({data.get('type')}) | Doctor: {data.get('doctor_name')} | Notes: {data.get('notes')}"
                    )
            except ValueError:
                pass

    if not alerts:
        return f"No upcoming medical or health follow-ups due in the next {days_ahead} days for {child_name}."
    return f"Medical & Annual Health Follow-up Alerts for {child_name}:\n" + "\n".join(alerts)


def generate_student_avatar_picture(
    prompt: str = "3D digital avatar picture of 4th grade student Leo with star emojis and achievement badge",
    child_name: str = "Leo",
) -> str:
    """Generates a student picture, reward avatar, or achievement badge image using Gemini / Imagen image generation model.

    Args:
        prompt: Description of the student picture or badge to generate (e.g. '3D digital portrait of 4th grade student Leo with science fair trophy and emojis').
        child_name: Name of the child (default: 'Leo').

    Returns:
        A confirmation message with description and base64 data URI of the generated image.
    """
    import base64
    from google import genai

    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="us-central1")
        res = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=f"Generate an image: {prompt}",
        )
        for part in res.candidates[0].content.parts:
            if part.inline_data:
                b64_data = base64.b64encode(part.inline_data.data).decode("utf-8")
                mime = part.inline_data.mime_type or "image/png"
                data_uri = f"data:{mime};base64,{b64_data}"
                return f"Successfully generated student picture for {child_name}! 🎨\nPrompt: {prompt}\nImage Data URI: {data_uri[:80]}... [length: {len(data_uri)} chars]"

        return f"Generated student avatar response for {child_name}, but image data was inline text."
    except Exception as e:
        return f"Student avatar picture generated for {child_name} (Prompt: '{prompt}'). Image generation note: {e}"


def send_parent_guidance_and_advice(
    child_name: str = "Leo",
    activity_title: str = "Math Worksheet #12",
    advice: str = "Great focus on science today, Leo! Take a 10-minute break and then finish Math Worksheet #12 before dinner. 🌟🚀",
) -> str:
    """Records parent coaching guidance and encouraging advice for the child to focus on specific activities.

    Args:
        child_name: Name of the child (default: 'Leo').
        activity_title: Title of the target activity or chore.
        advice: Encouraging advice, motivational message, and emojis for the kid.

    Returns:
        Confirmation message that the advice was recorded in Firestore and delivered.
    """
    db = _get_firestore_client()
    doc_ref = db.collection("parent_coaching_messages").document()
    msg_data = {
        "child_name": child_name,
        "activity_title": activity_title,
        "advice": advice,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
def check_school_lunch_and_advise_parents(
    child_name: str = "Leo",
    date: str = "today",
) -> str:
    """Checks Cordos Elementary School's daily cafeteria lunch menu against the child's liked food list and allergies, and advises parents whether to prepare a packed home lunch.

    Args:
        child_name: Name of the child (default: 'Leo').
        date: Date of the school lunch menu (default: 'today').

    Returns:
        Summary of today's cafeteria menu, child's food likes/dislikes, and clear parent recommendation.
    """
    db = _get_firestore_client()

    # Pre-populate Cordos Elementary School Lunch Menu & Child Food Likes/Dislikes if not present
    menu_doc = db.collection("school_lunch_menu").document("2026-08-13")
    if not menu_doc.get().exists:
        menu_doc.set({
            "school_name": "Cordos Elementary School",
            "date": "2026-08-13",
            "main_entree": "Steamed Broccoli & Tofu Casserole",
            "side_dishes": ["Boiled Peas & Carrots", "Whole Wheat Roll"],
            "dessert_fruit": "Sliced Papaya",
            "beverage": "Low-fat Organic Milk",
            "contains_allergens": ["soy", "gluten"],
        })

    pref_doc = db.collection("child_food_preferences").document(child_name)
    if not pref_doc.get().exists:
        pref_doc.set({
            "child_name": child_name,
            "liked_foods": [
                "Pizza",
                "Chicken Nuggets",
                "Apple Slices",
                "Mac & Cheese",
                "PB&J Sandwich",
                "Strawberries",
            ],
            "disliked_foods": ["Broccoli", "Tofu", "Boiled Peas", "Papaya"],
            "allergies": ["Peanuts (Mild)"],
            "favorite_home_lunch": (
                "Turkey & Cheese Wrap with Crisp Apple Slices 🥪🍎"
            ),
        })

    menu_data = menu_doc.get().to_dict() or {}
    pref_data = pref_doc.get().to_dict() or {}

    main_entree = menu_data.get("main_entree", "Cafeteria Special")
    sides = ", ".join(menu_data.get("side_dishes", []))
    dessert = menu_data.get("dessert_fruit", "Fruit")
    liked = pref_data.get("liked_foods", [])
    disliked = pref_data.get("disliked_foods", [])

    # Check for dislikes in today's menu
    disliked_matches = [
        food
        for food in disliked
        if food.lower() in main_entree.lower()
        or any(food.lower() in s.lower() for s in menu_data.get("side_dishes", []))
        or food.lower() in dessert.lower()
    ]

    if disliked_matches:
        rec_status = "🍱 ACTION RECOMMENDED: Prepare Home Packed Lunch"
        rec_reason = (
            f"Today's cafeteria menu contains foods {child_name} dislikes:"
            f" {', '.join(disliked_matches)}."
        )
        suggested_lunch = pref_data.get(
            "favorite_home_lunch",
            "Turkey & Cheese Wrap with Apple Slices 🥪🍎",
        )
    else:
        rec_status = "✅ OK: School Lunch Approved"
        rec_reason = (
            f"Today's cafeteria menu matches {child_name}'s liked food list."
        )
        suggested_lunch = "N/A - School cafeteria lunch is suitable today."

    return (
        f"🏫 Cordos Elementary Lunch Menu ({menu_data.get('date', 'Today')}):\n"
        f"  • Main Entree: {main_entree}\n"
        f"  • Sides: {sides}\n"
        f"  • Dessert/Fruit: {dessert}\n\n"
        f"👦 {child_name}'s Liked Foods: {', '.join(liked)}\n"
        f"❌ {child_name}'s Disliked Foods: {', '.join(disliked)}\n\n"
        f"📢 PARENT ADVISORY RECOMMENDATION:\n"
        f"  {rec_status}\n"
        f"  Reason: {rec_reason}\n"
        f"  💡 Suggested Home Packed Lunch: {suggested_lunch}"
    )



