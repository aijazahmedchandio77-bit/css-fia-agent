"""
A rotating pool of CSS syllabus subjects/topics for Task 5 (study-card
images). Deterministically picked by date + time-slot so it cycles through
different topics across days without needing any persistent storage.
"""

TOPICS = [
    ("Pakistan Affairs", "Ideology of Pakistan"),
    ("Pakistan Affairs", "Allama Iqbal's Political Philosophy"),
    ("Pakistan Affairs", "Quaid-i-Azam's Constitutional Struggle"),
    ("Pakistan Affairs", "1973 Constitution: Salient Features"),
    ("Pakistan Affairs", "18th Amendment"),
    ("Pakistan Affairs", "Land and People of Pakistan"),
    ("Current Affairs", "Pakistan-Afghanistan Relations"),
    ("Current Affairs", "Pakistan-India Relations & Kashmir"),
    ("Current Affairs", "CPEC: Progress and Challenges"),
    ("Current Affairs", "Pakistan's Economic Challenges"),
    ("Current Affairs", "Climate Change and Pakistan"),
    ("Current Affairs", "Pakistan's Foreign Policy Priorities"),
    ("International Relations", "United Nations: Structure and Role"),
    ("International Relations", "Israel-Palestine Conflict"),
    ("International Relations", "Nuclear Non-Proliferation Regime"),
    ("International Relations", "Global Trade Organizations (WTO, IMF, World Bank)"),
    ("Islamic Studies", "Sources of Islamic Law"),
    ("Islamic Studies", "Seerat-un-Nabi: Makkan Period"),
    ("Islamic Studies", "Khulafa-e-Rashideen: Key Achievements"),
    ("English Grammar", "Parts of Speech Overview"),
    ("English Grammar", "Precis Writing Technique"),
    ("General Science", "Basics of Climate Science"),
    ("General Science", "Artificial Intelligence: Key Concepts"),
    ("Governance", "Federalism in Pakistan"),
    ("Governance", "Local Government System"),
]


def pick_topic(day_index: int, slot_index: int):
    """Deterministic rotation based on day-of-year and time slot, no storage needed."""
    idx = (day_index * 5 + slot_index) % len(TOPICS)
    return TOPICS[idx]
