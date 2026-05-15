import sims4.commands


@sims4.commands.Command('rotwages.status', command_type=sims4.commands.CommandType.Live)
def cmd_rotwages_status(_connection=None):
    # type: (object) -> None
    """Print the rotational pay state for every played-household away Sim."""
    output = sims4.commands.CheatOutput(_connection)
    try:
        import services
        from rotational_wages.paycheck import is_eligible, ELIGIBLE_CATEGORIES

        sim_info_manager = services.sim_info_manager()
        if sim_info_manager is None:
            output('rotpay: sim_info_manager not available')
            return

        found = False
        for sim_info in sim_info_manager.get_all():
            if not sim_info.is_npc:
                continue
            household = sim_info.household
            if household is None or not household.is_played_household:
                continue
            career_tracker = sim_info.career_tracker
            if career_tracker is None:
                continue
            for career in career_tracker.careers.values():
                found = True
                eligible = is_eligible(sim_info, career)
                hours = career.get_current_work_duration_in_hours() if eligible else None
                output('[rotpay] {} | cat={} | eligible={} | hours={} | funds={}'.format(
                    sim_info.full_name,
                    int(career.career_category),
                    eligible,
                    hours,
                    household.funds.money,
                ))

        if not found:
            output('rotpay: no played-household away Sims found')
    except Exception as exc:
        output('rotpay error: {}'.format(exc))
