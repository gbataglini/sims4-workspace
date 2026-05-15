from typing import Any

_installed = False  # type: bool


def install():
    # type: () -> None
    global _installed
    if _installed:
        return
    _apply_hooks()
    _installed = True


def _apply_hooks():
    # type: () -> None
    # All game imports are deferred inside this function so the module can be
    # imported in the test environment without the game runtime present.
    from careers.career_base import CareerBase
    from helpers.injector import inject
    from rotational_wages.paycheck import is_eligible
    import sims4.log

    logger = sims4.log.Logger('RotationalWages', default_owner='rotwages')

    @inject(CareerBase, '_end_work_callback')
    def _on_end_work_callback(original, self, handle):
        # type: (Any, Any, Any) -> None
        # Fires at shift end for every employed Sim.  The vanilla code skips
        # handle_career_loot for is_npc Sims, so played-household away Sims
        # get §0.  We call it first with the full shift duration.
        if not self.currently_at_work and is_eligible(self._sim_info, self):
            from careers.career_ops import CareerTimeOffReason
            if self.taking_day_off_reason != CareerTimeOffReason.MISSING_WORK:
                hours = self.get_current_work_duration_in_hours()
                if hours:
                    try:
                        self.handle_career_loot(hours)
                        logger.info('Rotational pay: {} earned §{} for shift',
                                    self._sim_info, self._sim_info.household.funds)
                    except Exception as exc:
                        logger.exception('Rotational pay (_end_work_callback) failed '
                                         'for {}: {}', self._sim_info, exc)
        return original(self, handle)

    @inject(CareerBase, 'leave_work')
    def _on_leave_work(original, self, left_early=False):
        # type: (Any, Any, bool) -> None
        # Fires when a Sim who was _at_work=True finishes the shift (e.g. saved
        # mid-shift then loaded a different household).  Same guard: call
        # handle_career_loot before vanilla skips it.
        if not left_early and is_eligible(self._sim_info, self):
            hours = self.get_current_work_duration_in_hours()
            if hours:
                try:
                    self.handle_career_loot(hours, left_early=False)
                    logger.info('Rotational pay (leave_work): {} earned shift pay',
                                self._sim_info)
                except Exception as exc:
                    logger.exception('Rotational pay (leave_work) failed '
                                     'for {}: {}', self._sim_info, exc)
        return original(self, left_early)

    logger.info('RotationalWages hooks applied')
