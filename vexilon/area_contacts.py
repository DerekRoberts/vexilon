"""
BCGEU Area Office Contact Information Module

Issue #232: Integration with BCGEU area offices and contact info
"""

import json
from pathlib import Path
from typing import Optional


def load_area_contacts() -> dict:
    """Load area office contact information from JSON."""
    contacts_path = Path(__file__).parent.parent / "data" / "bcgeu_area_contacts.json"
    with open(contacts_path) as f:
        return json.load(f)


def get_area_office_by_location(location_hint: str) -> Optional[dict]:
    """Find area office by location name or area number."""
    data = load_area_contacts()
    location_hint = location_hint.lower()
    
    for area in data["areas"]:
        # Match by location name
        if location_hint in area["location"].lower():
            return area
        # Match by region description
        if location_hint in area["regions"].lower():
            return area
        # Match by area number
        if location_hint == str(area["area_number"]):
            return area
    
    return None


def format_area_office_contact(area: dict) -> str:
    """Format area office contact info for display."""
    return f"""### 📞 BCGEU Area Office {area['area_number']} — {area['location']}

**Address:** {area['address']}  
**Phone:** {area['phone']}  
**Toll-Free:** {area['toll_free']}  
**Fax:** {area['fax']}  
**Email:** {area['email']}  

**Serves:** {area['regions']}
"""


def get_all_area_offices_summary() -> str:
    """Get summary of all area offices."""
    data = load_area_contacts()
    lines = ["### 📋 BCGEU Area Offices Summary\n"]
    
    for area in data["areas"]:
        lines.append(f"**Area {area['area_number']} — {area['location']}:** {area['phone']} | {area['email']}")
    
    lines.append(f"\n**Toll-Free (all areas):** {data['areas'][0]['toll_free']}")
    return "\n".join(lines)


def get_staff_rep_process() -> str:
    """Get the staff representative assignment process."""
    data = load_area_contacts()
    process = data["staff_rep_process"]
    
    lines = [f"### 🔄 {process['title']}\n"]
    
    for step in process["steps"]:
        lines.append(f"**Step {step['step']}: {step['title']}**  
{step['description']}\n")
    
    lines.append(f"*Note: {process['note']}*")
    return "\n".join(lines)


def get_grievance_handoff_message(location_hint: Optional[str] = None) -> str:
    """
    Generate a comprehensive handoff message for grievance filing.
    
    This should be called at the end of grievance-related interactions
    to provide members with next steps and contact information.
    """
    data = load_area_contacts()
    
    lines = [
        "---",
        "",
        "## 📤 Next Steps: Submit Your Grievance",
        "",
        "### 1. Contact Your Area Office",
        ""
    ]
    
    # If location provided, show specific office
    if location_hint:
        area = get_area_office_by_location(location_hint)
        if area:
            lines.append(format_area_office_contact(area))
            lines.append("")
        else:
            lines.append(f"*Could not find area office for '{location_hint}'. Showing all offices:*")
            lines.append(get_all_area_offices_summary())
            lines.append("")
    else:
        lines.append(get_all_area_offices_summary())
        lines.append("")
    
    # Add staff rep process
    lines.append(get_staff_rep_process())
    lines.append("")
    
    # Add form submission guidance
    lines.append("""### 📄 Submit Your Forms

Send your completed grievance forms and supporting documents to your area office:
- **Email:** Your area office email (above)
- **Fax:** Your area office fax (above)
- **Mail:** Your area office address (above)

**Required documents:**
- Completed grievance form (Grievance - A, B, or C as appropriate)
- Your notes and evidence
- Any relevant correspondence with management

### ⏰ Timeline Reminder

Remember: Grievances must be filed within the timelines specified in your collective agreement. Check Article 8 (Grievance Procedure) for specific deadlines.
""")
    
    return "\n".join(lines)


# Quick lookup table for common BC locations
LOCATION_TO_AREA = {
    # Metro Vancouver
    "vancouver": 5, "burnaby": 5, "new westminster": 5, "richmond": 5, "surrey": 5,
    "coquitlam": 5, "port coquitlam": 5, "port moody": 5, "delta": 5, "north vancouver": 5,
    "west vancouver": 5, "maple ridge": 5, "pitt meadows": 5, "new west": 5,
    
    # Vancouver Island
    "victoria": 6, "saanich": 6, "duncan": 6, "nanaimo": 6, "cowichan": 6,
    "ladysmith": 6, "parksville": 6, "qualicum": 6, "port alberni": 6, "tofino": 6,
    "ucluelet": 6, "comox": 6, "courtenay": 6, "campbell river": 6,
    
    # Fraser Valley / Southwest
    "abbotsford": 7, "chilliwack": 7, "hope": 7, "mission": 7, "agassiz": 7,
    "harrison": 7, "boston bar": 7,
    
    # Okanagan
    "kelowna": 8, "penticton": 8, "vernon": 8, "west kelowna": 8, "peachland": 8,
    "summerland": 8, " osoyoos": 8, "oliver": 8, "princeton": 8, "revelstoke": 8,
    
    # Thompson / Nicola
    "kamloops": 9, "clearwater": 9, "barriere": 9, "chase": 9, "cache creek": 9,
    "ashcroft": 9, "merritt": 9, "logan lake": 9,
    
    # Kootenay
    "nelson": 10, "castlegar": 10, "trail": 10, "rossland": 10, "fruitvale": 10,
    "salmo": 10, "creston": 10, "kaslo": 10, "nakusp": 10, "new denver": 10,
    "cranbrook": 11, "fernie": 11, "kimberley": 11, "sparwood": 11, "invermere": 11,
    "golden": 11, "radium": 11, "elkford": 11,
    
    # Cariboo
    "williams lake": 3, "quesnel": 3, "100 mile house": 3, "alexandria": 3,
    "cariboo": 3, "clinton": 3, "lac la hache": 3, "liard": 3,
    
    # North Central
    "prince george": 2, "vanderhoof": 2, "fort st. james": 2, "mackenzie": 2,
    "valemount": 2, "mcbride": 2, "quesnel": 2,
    
    # Northwest
    "terrace": 1, "kitimat": 1, "prince rupert": 1, "smithers": 1, "houston": 1,
    "masset": 1, "queen charlotte": 1, "haida gwaii": 1, "kitimat": 1,
    
    # Northeast
    "fort st. john": 12, "dawson creek": 12, "fort nelson": 12, "tumbler ridge": 12,
    "chetwynd": 12, "hudson's hope": 12, "pink mountain": 12,
    
    # Sunshine Coast
    "powell river": 4, "sechelt": 4, "gibsons": 4, "sunshine coast": 4,
    "squit": 4, "roberts creek": 4, "madeira park": 4, "langdale": 4,
}


def get_area_by_workplace_location(location: str) -> Optional[dict]:
    """Get area office based on workplace location."""
    location = location.lower().strip()
    
    # Direct lookup
    if location in LOCATION_TO_AREA:
        area_number = LOCATION_TO_AREA[location]
        data = load_area_contacts()
        for area in data["areas"]:
            if area["area_number"] == area_number:
                return area
    
    # Partial match
    for loc_key, area_number in LOCATION_TO_AREA.items():
        if loc_key in location or location in loc_key:
            data = load_area_contacts()
            for area in data["areas"]:
                if area["area_number"] == area_number:
                    return area
    
    return None
