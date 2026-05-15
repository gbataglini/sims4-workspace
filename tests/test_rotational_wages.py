"""Tests for rotational_wages.paycheck — no game runtime required."""
import sys
import types
import pytest


# ---------------------------------------------------------------------------
# Minimal stubs so src/ can be imported without the game runtime
# ---------------------------------------------------------------------------

def _stub_module(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


def _ensure_stubs():
    """Create the minimum game-module stubs needed to import paycheck.py."""
    # Only stub what paycheck.py actually imports at module level — nothing.
    # paycheck.py has no game imports, so this is a no-op, but keep it here
    # in case future helpers are added.
    pass


_ensure_stubs()

# Now safe to import
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from rotational_wages.paycheck import is_eligible, ELIGIBLE_CATEGORIES


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

class MockHousehold:
    def __init__(self, is_played=True):
        self.is_played_household = is_played


class MockSimInfo:
    def __init__(self, is_npc=True, is_played_household=True):
        self.is_npc = is_npc
        self.household = MockHousehold(is_played=is_played_household)


class MockCareer:
    def __init__(self, category=1, on_assignment=False):
        self.career_category = category  # int matching CareerCategory enum
        self.on_assignment = on_assignment


# ---------------------------------------------------------------------------
# Tests: is_eligible
# ---------------------------------------------------------------------------

class TestIsEligible:
    def test_active_household_sim_not_eligible(self):
        sim = MockSimInfo(is_npc=False, is_played_household=True)
        career = MockCareer(category=1)
        assert not is_eligible(sim, career)

    def test_townie_npc_not_eligible(self):
        sim = MockSimInfo(is_npc=True, is_played_household=False)
        career = MockCareer(category=1)
        assert not is_eligible(sim, career)

    def test_no_household_not_eligible(self):
        sim = MockSimInfo(is_npc=True)
        sim.household = None
        career = MockCareer(category=1)
        assert not is_eligible(sim, career)

    def test_work_career_eligible(self):
        sim = MockSimInfo(is_npc=True, is_played_household=True)
        career = MockCareer(category=1)  # Work
        assert is_eligible(sim, career)

    def test_teen_part_time_eligible(self):
        sim = MockSimInfo(is_npc=True, is_played_household=True)
        career = MockCareer(category=3)  # TeenPartTime
        assert is_eligible(sim, career)

    def test_adult_part_time_eligible(self):
        sim = MockSimInfo(is_npc=True, is_played_household=True)
        career = MockCareer(category=5)  # AdultPartTime
        assert is_eligible(sim, career)

    def test_school_career_not_eligible(self):
        sim = MockSimInfo(is_npc=True, is_played_household=True)
        career = MockCareer(category=2)  # School
        assert not is_eligible(sim, career)

    def test_work_from_home_not_eligible(self):
        sim = MockSimInfo(is_npc=True, is_played_household=True)
        career = MockCareer(category=8)  # WorkFromHome
        assert not is_eligible(sim, career)

    def test_on_assignment_not_eligible(self):
        sim = MockSimInfo(is_npc=True, is_played_household=True)
        career = MockCareer(category=1, on_assignment=True)
        assert not is_eligible(sim, career)

    def test_all_eligible_categories_covered(self):
        sim = MockSimInfo(is_npc=True, is_played_household=True)
        for cat in ELIGIBLE_CATEGORIES:
            career = MockCareer(category=cat)
            assert is_eligible(sim, career), 'category {} should be eligible'.format(cat)


# ---------------------------------------------------------------------------
# Tests: hook logic (tested via thin wrappers, no game imports)
# ---------------------------------------------------------------------------

class MockFunds:
    def __init__(self):
        self.money = 0
        self.calls = []

    def add(self, amount, reason, sim=None):
        self.money += amount
        self.calls.append(amount)


class MockHouseholdWithFunds:
    def __init__(self):
        self.is_played_household = True
        self.funds = MockFunds()


class MockSimInfoWithHousehold:
    def __init__(self):
        self.is_npc = True
        self.household = MockHouseholdWithFunds()


def _make_hook_logic():
    """Returns a callable that mimics the _end_work_callback hook body."""
    from rotational_wages.paycheck import is_eligible

    MISSING_WORK = 3  # CareerTimeOffReason.MISSING_WORK

    def hook_logic(sim_info, career, currently_at_work, taking_day_off_reason,
                   work_duration_hours, handle_career_loot_fn):
        # type: (object, object, bool, int, float, object) -> bool
        """Returns True if handle_career_loot was called."""
        if currently_at_work:
            return False
        if not is_eligible(sim_info, career):
            return False
        if taking_day_off_reason == MISSING_WORK:
            return False
        if work_duration_hours:
            handle_career_loot_fn(work_duration_hours)
            return True
        return False

    return hook_logic


class TestEndWorkCallbackHookLogic:
    def setup_method(self):
        self.hook = _make_hook_logic()
        self.sim = MockSimInfoWithHousehold()
        self.career = MockCareer(category=1)
        self.paid = []

    def _pay(self, hours):
        self.paid.append(hours)

    def test_eligible_sim_gets_paid(self):
        called = self.hook(self.sim, self.career,
                           currently_at_work=False,
                           taking_day_off_reason=0,  # NO_TIME_OFF
                           work_duration_hours=8.0,
                           handle_career_loot_fn=self._pay)
        assert called
        assert self.paid == [8.0]

    def test_currently_at_work_skips(self):
        called = self.hook(self.sim, self.career,
                           currently_at_work=True,
                           taking_day_off_reason=0,
                           work_duration_hours=8.0,
                           handle_career_loot_fn=self._pay)
        assert not called
        assert self.paid == []

    def test_missing_work_skips(self):
        called = self.hook(self.sim, self.career,
                           currently_at_work=False,
                           taking_day_off_reason=3,  # MISSING_WORK
                           work_duration_hours=8.0,
                           handle_career_loot_fn=self._pay)
        assert not called
        assert self.paid == []

    def test_zero_duration_skips(self):
        called = self.hook(self.sim, self.career,
                           currently_at_work=False,
                           taking_day_off_reason=0,
                           work_duration_hours=0,
                           handle_career_loot_fn=self._pay)
        assert not called
        assert self.paid == []

    def test_townie_npc_skips(self):
        townie = MockSimInfo(is_npc=True, is_played_household=False)
        called = self.hook(townie, self.career,
                           currently_at_work=False,
                           taking_day_off_reason=0,
                           work_duration_hours=8.0,
                           handle_career_loot_fn=self._pay)
        assert not called
        assert self.paid == []

    def test_active_household_sim_skips(self):
        active_sim = MockSimInfo(is_npc=False, is_played_household=True)
        called = self.hook(active_sim, self.career,
                           currently_at_work=False,
                           taking_day_off_reason=0,
                           work_duration_hours=8.0,
                           handle_career_loot_fn=self._pay)
        assert not called
        assert self.paid == []

    def test_pto_day_gets_paid(self):
        called = self.hook(self.sim, self.career,
                           currently_at_work=False,
                           taking_day_off_reason=1,  # PTO
                           work_duration_hours=8.0,
                           handle_career_loot_fn=self._pay)
        assert called
        assert self.paid == [8.0]
