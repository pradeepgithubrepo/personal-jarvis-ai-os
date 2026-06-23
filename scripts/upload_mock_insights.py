# scripts/upload_mock_insights.py

import os
import sys
import json
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from consumer.supabase_client import SupabaseClient
from configs.settings import settings

MOCK_DATA = {
    "daily_brief.json": {
        "greeting": "Good Morning Pradeep",
        "priorities": [
            "Finalize school admission documents for child",
            "Pay outstanding HDFC credit card bill",
            "Prepare travel packing list for next week's Mumbai trip"
        ],
        "financial_alerts": [
            "Credit card bill of 12,450 INR is due in 3 days.",
            "Salary credit expected from Client A on June 30."
        ],
        "family_updates": [
            "Ravi has football practice today at 5:00 PM.",
            "Dinner reservations confirmed for Saturday at 7:30 PM."
        ],
        "school_circulars": [
            "Grade 5: Science project instructions uploaded.",
            "Fee payment reminder for Term 2."
        ],
        "important_reminders": [
            "Annual health checkup appointment tomorrow at 10:00 AM.",
            "Car service due by end of this week."
        ],
        "last_updated": "2026-06-22T04:00:00Z"
    },
    "todos.json": {
        "todos": [
            {
                "id": "todo-1",
                "title": "Review school circular on Term 2 exams",
                "status": "pending",
                "due_date": "2026-06-22",
                "priority": "high",
                "category": "School"
            },
            {
                "id": "todo-2",
                "title": "Pay broadband internet bill",
                "status": "pending",
                "due_date": "2026-06-22",
                "priority": "high",
                "category": "Financial"
            },
            {
                "id": "todo-3",
                "title": "Renew car insurance policy",
                "status": "pending",
                "due_date": "2026-06-23",
                "priority": "medium",
                "category": "Financial"
            },
            {
                "id": "todo-4",
                "title": "Pack bags for business trip to Mumbai",
                "status": "pending",
                "due_date": "2026-06-23",
                "priority": "medium",
                "category": "Travel"
            },
            {
                "id": "todo-5",
                "title": "Schedule dentist appointment",
                "status": "pending",
                "due_date": "2026-06-25",
                "priority": "low",
                "category": "Health"
            },
            {
                "id": "todo-6",
                "title": "Submit project proposal to client",
                "status": "completed",
                "due_date": "2026-06-21",
                "priority": "high",
                "category": "Work"
            }
        ],
        "last_updated": "2026-06-22T04:00:00Z"
    },
    "financial.json": {
        "upcoming_bills": [
            {
                "title": "Broadband Internet",
                "amount": 1200,
                "due_date": "2026-06-22",
                "status": "pending"
            },
            {
                "title": "HDFC Credit Card",
                "amount": 12450,
                "due_date": "2026-06-25",
                "status": "pending"
            },
            {
                "title": "Electricity Bill",
                "amount": 3400,
                "due_date": "2026-06-28",
                "status": "pending"
            }
        ],
        "salary_credits": [
            {
                "title": "Monthly Consulting Fee",
                "amount": 150000,
                "date": "2026-06-01"
            },
            {
                "title": "AdSense Revenue",
                "amount": 8500,
                "date": "2026-06-15"
            }
        ],
        "spend_categories": {
            "Groceries & Food": 18500,
            "Utilities & Bills": 8200,
            "Fuel & Transport": 6000,
            "Dining & Entertainment": 9500,
            "Healthcare": 3000
        },
        "monthly_summary": {
            "income": 158500,
            "expenses": 45200,
            "savings": 113300
        },
        "alerts": [
            "High dining spend detected this week (+15% vs last week).",
            "Utility bills are 5% lower than the previous month."
        ],
        "last_updated": "2026-06-22T04:00:00Z"
    },
    "fyi.json": {
        "updates": [
            {
                "title": "Amazon package delivered",
                "category": "delivery",
                "timestamp": "2026-06-22T10:30:00Z",
                "content": "Your package with the wireless mouse has been left at the reception."
            },
            {
                "title": "Annual school fee circular published",
                "category": "school",
                "timestamp": "2026-06-21T15:00:00Z",
                "content": "Term 2 fee structure is available. Payment deadline is July 10."
            },
            {
                "title": "Weekend family lunch plan changed",
                "category": "family",
                "timestamp": "2026-06-21T09:00:00Z",
                "content": "Lunch at grandparents' house moved from Sunday to Saturday at 1:00 PM."
            },
            {
                "title": "Local power outage announcement",
                "category": "general",
                "timestamp": "2026-06-20T17:30:00Z",
                "content": "Maintenance scheduled for Thursday between 9:00 AM and 11:00 AM."
            }
        ],
        "last_updated": "2026-06-22T04:00:00Z"
    },
    "family.json": {
        "messages": [
            {
                "sender": "Shobana",
                "content": "Don't forget to pick up the vegetables on your way back.",
                "date": "2026-06-22"
            },
            {
                "sender": "Mom",
                "content": "Are we coming over this Saturday?",
                "date": "2026-06-21"
            }
        ],
        "events": [
            {
                "title": "Family Lunch",
                "date": "2026-06-27",
                "description": "Lunch at grandparents' place"
            },
            {
                "title": "Ravi's Football Match",
                "date": "2026-06-28",
                "description": "Inter-school finals at 9:00 AM"
            }
        ],
        "reminders": [
            {
                "title": "Water the balcony plants",
                "date": "2026-06-22"
            },
            {
                "title": "Buy gift for Neha's birthday party",
                "date": "2026-06-25"
            }
        ],
        "last_updated": "2026-06-22T04:00:00Z"
    },
    "school.json": {
        "circulars": [
            {
                "title": "Grade 5 Term 2 Syllabus Out",
                "child": "Ravi",
                "date": "2026-06-22",
                "description": "The detailed syllabus for Term 2 examinations has been posted."
            },
            {
                "title": "School Picnic Announcement",
                "child": "Ravi",
                "date": "2026-06-20",
                "description": "Annual picnic scheduled for July 5th. Sign permission slips."
            }
        ],
        "activities": [
            {
                "title": "Football Team Practice",
                "child": "Ravi",
                "date": "2026-06-22"
            },
            {
                "title": "Science Lab Session",
                "child": "Ravi",
                "date": "2026-06-24"
            }
        ],
        "homework": [
            {
                "title": "Maths Exercises 4 & 5",
                "child": "Ravi",
                "due_date": "2026-06-23",
                "subject": "Mathematics"
            },
            {
                "title": "Draw solar system diagram",
                "child": "Ravi",
                "due_date": "2026-06-24",
                "subject": "Science"
            }
        ],
        "events": [
            {
                "title": "Parent Teacher Association Meeting",
                "child": "Ravi",
                "date": "2026-06-29"
            }
        ],
        "last_updated": "2026-06-22T04:00:00Z"
    },
    "travel.json": {
        "tickets": [
            {
                "from": "Bangalore (BLR)",
                "to": "Mumbai (BOM)",
                "date": "2026-06-29",
                "booking_ref": "6E-2401",
                "departure_time": "08:15 AM",
                "passenger": "Pradeep"
            }
        ],
        "bookings": [
            {
                "name": "Taj Lands End, Mumbai",
                "type": "Hotel",
                "check_in": "2026-06-29",
                "check_out": "2026-07-02",
                "status": "confirmed"
            }
        ],
        "alerts": [
            "Web check-in opens on June 28 at 08:15 AM.",
            "Mumbai weather forecast: Heavy rain expected next week."
        ],
        "last_updated": "2026-06-22T04:00:00Z"
    },
    "health.json": {
        "medical_reminders": [
            {
                "medicine_name": "Multivitamin",
                "dosage": "1 tablet",
                "time": "After breakfast"
            },
            {
                "medicine_name": "Omega-3",
                "dosage": "1 capsule",
                "time": "With dinner"
            }
        ],
        "health_alerts": [
            "Annual dental cleanup is due this month.",
            "Drinking water intake is below target today."
        ],
        "appointments": [
            {
                "doctor": "Dr. Ramesh (Dentist)",
                "time": "2026-06-25T11:00:00Z",
                "clinic": "Smile Dental Care"
            }
        ],
        "last_updated": "2026-06-22T04:00:00Z"
    }
}

def seed():
    bucket_name = getattr(settings, "supabase_insights_bucket", "jarvis-insights")
    client = SupabaseClient(bucket=bucket_name)
    
    logger.info(f"Seeding mock insight JSON payloads to Supabase bucket '{bucket_name}'...")
    
    for filename, content in MOCK_DATA.items():
        serialized = json.dumps(content, indent=2)
        success = client.upload_file(filename, serialized)
        if success:
            logger.success(f"Uploaded {filename} successfully.")
        else:
            logger.error(f"Failed to upload {filename}!")

if __name__ == "__main__":
    seed()
