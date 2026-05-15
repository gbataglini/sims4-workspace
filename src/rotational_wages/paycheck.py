# Pure eligibility logic — no game imports so this is testable outside the game.
from typing import Any

# Integer values of careers.career_enums.CareerCategory for rabbit-hole and part-time jobs.
# Work=1, TeenPartTime=3, AdultPartTime=5
# Excluded: School(2), Volunteer(4), UniversityCourse(6), TeenSideHustle(7), WorkFromHome(8)
ELIGIBLE_CATEGORIES = frozenset([1, 3, 5])


def is_eligible(sim_info, career):
    # type: (Any, Any) -> bool
    """True when this career should receive rotational pay while the household is away."""
    if not sim_info.is_npc:
        return False
    household = sim_info.household
    if household is None or not household.is_played_household:
        return False
    if int(career.career_category) not in ELIGIBLE_CATEGORIES:
        return False
    if career.on_assignment:
        return False
    return True
