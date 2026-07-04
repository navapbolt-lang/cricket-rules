"""Condition graphs for key cricket laws. Each scenario type has an ordered checklist the agent must verify."""

from app.models.types import Format, ScenarioType, ConditionCheck


# ── LBW Conditions ──────────────────────────────────────────

LBW_CONDITIONS = [
    ConditionCheck(
        id=1,
        description="Ball pitches in line with the stumps or on the off side",
        law="36.1",
        terminal=True,
    ),
    ConditionCheck(
        id=2,
        description="Ball impacts in line with the stumps (or outside off if no shot offered)",
        law="36.2",
        terminal=False,
    ),
    ConditionCheck(
        id=3,
        description="Ball would have hit the stumps",
        law="36.3",
        terminal=True,
    ),
    ConditionCheck(
        id=4,
        description="Batter did not hit the ball before the pad",
        law="36.4",
        terminal=False,
    ),
    ConditionCheck(
        id=5,
        description="No-shot exception handled (if no shot offered, impact outside off can still be out)",
        law="36.5",
        terminal=True,
    ),
]

# ── DRS Review Conditions ────────────────────────────────────

DRS_CONDITIONS = [
    ConditionCheck(
        id=1,
        description="Original on-field decision (out or not out)",
        law="25.3",
        terminal=False,
    ),
    ConditionCheck(
        id=2,
        description="Ball-tracking shows clear error in on-field decision (outside umpire's call margin)",
        law="25.3.1",
        terminal=True,
    ),
    ConditionCheck(
        id=3,
        description="Reviewing team has reviews remaining",
        law="25.3.2",
        terminal=True,
    ),
]

# ── No-Ball Conditions (Front Foot) ─────────────────────────

NO_BALL_CONDITIONS = [
    ConditionCheck(
        id=1,
        description="Bowler's front foot lands behind the popping crease on the bowling side",
        law="24.1",
        terminal=True,
    ),
    ConditionCheck(
        id=2,
        description="Delivery is otherwise fair (not a beamer, not above waist height)",
        law="24.2",
        terminal=True,
    ),
]

# ── Wide Ball Conditions ─────────────────────────────────────

WIDE_CONDITIONS = [
    ConditionCheck(
        id=1,
        description="Ball passes out of the batter's reach on the off or leg side",
        law="25.1",
        terminal=True,
    ),
    ConditionCheck(
        id=2,
        description="Leg-side tramline marker considered (2025 trial rule)",
        law="25.1.1",
        terminal=False,
    ),
]

# ── Run-Out Conditions ──────────────────────────────────────

RUN_OUT_CONDITIONS = [
    ConditionCheck(
        id=1,
        description="Ball is in play (not dead)",
        law="38.1",
        terminal=True,
    ),
    ConditionCheck(
        id=2,
        description="Batter is out of their ground (no part of bat or body behind the popping crease)",
        law="38.2",
        terminal=True,
    ),
    ConditionCheck(
        id=3,
        description="Wicket is put down by the fielding side fairly",
        law="38.3",
        terminal=False,
    ),
]

# ── Boundary Catch Conditions (2025 Rule) ────────────────────

BOUNDARY_CATCH_CONDITIONS = [
    ConditionCheck(
        id=1,
        description="Fielder has full control over the ball and their own movement",
        law="33.1",
        terminal=False,
    ),
    ConditionCheck(
        id=2,
        description="Fielder lands AND stays wholly inside the boundary throughout the catch",
        law="33.2",
        terminal=True,
    ),
    ConditionCheck(
        id=3,
        description="Ball is caught cleanly (not grounded, not bounced)",
        law="33.3",
        terminal=True,
    ),
]

# ── Obstructing the Field ────────────────────────────────────

OBSTRUCTING_CONDITIONS = [
    ConditionCheck(
        id=1,
        description="Batter makes a significant change of direction or movement",
        law="37.1",
        terminal=False,
    ),
    ConditionCheck(
        id=2,
        description="The movement is wilful and without cricket cause",
        law="37.2",
        terminal=True,
    ),
    ConditionCheck(
        id=3,
        description="The obstruction prevents a run-out or catch",
        law="37.3",
        terminal=True,
    ),
]

# ── Stumping Conditions ─────────────────────────────────────

STUMPING_CONDITIONS = [
    ConditionCheck(
        id=1,
        description="Batter is out of their ground (advancing to the bowler)",
        law="39.1",
        terminal=False,
    ),
    ConditionCheck(
        id=2,
        description="Wicket-keeper puts down the wicket fairly (no gloves in front of stumps)",
        law="39.2",
        terminal=True,
    ),
    ConditionCheck(
        id=3,
        description="Bowler did not bowl a no-ball",
        law="39.3",
        terminal=True,
    ),
]

# ── Hit Wicket Conditions ───────────────────────────────────

HIT_WICKET_CONDITIONS = [
    ConditionCheck(
        id=1,
        description="Batter dislodges the bails with their body or bat",
        law="35.1",
        terminal=True,
    ),
    ConditionCheck(
        id=2,
        description="Occurs while attempting to play the ball or taking off for a run",
        law="35.2",
        terminal=True,
    ),
]

# ── Concussion Replacement Conditions ────────────────────────

CONCUSSION_CONDITIONS = [
    ConditionCheck(
        id=1,
        description="Player is diagnosed with concussion during the match",
        law="1.7",
        terminal=True,
    ),
    ConditionCheck(
        id=2,
        description="Replacement is a like-for-like player approved by match referee",
        law="1.7.1",
        terminal=True,
    ),
]

# ── DLS Method Conditions ───────────────────────────────────

DLS_CONDITIONS = [
    ConditionCheck(
        id=1,
        description="Match is interrupted by rain or other external factors",
        law="16.1",
        terminal=True,
    ),
    ConditionCheck(
        id=2,
        description="Minimum overs have been bowled in the first innings",
        law="16.2",
        terminal=True,
    ),
    ConditionCheck(
        id=3,
        description="Both teams have batted equal number of overs (or target is computed by DLS)",
        law="16.3",
        terminal=False,
    ),
]

# ── Aggregated Map ──────────────────────────────────────────

# ── Timed Out / New Batter Conditions ────────────────────────

TIMED_OUT_CONDITIONS = [
    ConditionCheck(
        id=1,
        description="The new batter must be ready to receive the ball within 3 minutes of the dismissal/retirement",
        law="40.1",
        terminal=True,
    ),
    ConditionCheck(
        id=2,
        description="If the incoming batter is not ready within 3 minutes, they are given out Timed out",
        law="40.2",
        terminal=True,
    ),
    ConditionCheck(
        id=3,
        description="Time was not called before the 3-minute period expired",
        law="40.1",
        terminal=False,
    ),
]

SCENARIO_GRAPH_MAP: dict[str, dict[str, list[ConditionCheck]]] = {
    "lbw": {"all": LBW_CONDITIONS},
    "drs_review": {"all": DRS_CONDITIONS},
    "no_ball": {"all": NO_BALL_CONDITIONS},
    "wide": {"all": WIDE_CONDITIONS},
    "run_out": {"all": RUN_OUT_CONDITIONS},
    "boundary_catch": {"all": BOUNDARY_CATCH_CONDITIONS},
    "obstructing": {"all": OBSTRUCTING_CONDITIONS},
    "stumping": {"all": STUMPING_CONDITIONS},
    "hit_wicket": {"all": HIT_WICKET_CONDITIONS},
    "concussion": {"all": CONCUSSION_CONDITIONS},
    "dls": {"all": DLS_CONDITIONS},
    "timed_out": {"all": TIMED_OUT_CONDITIONS},
}


def get_scenario_graph(scenario_type: str, format: str = "all") -> list[ConditionCheck]:
    """Get the condition checklist for a scenario type and format."""
    type_map = SCENARIO_GRAPH_MAP.get(scenario_type, {})

    if format in type_map:
        return type_map[format]
    if "all" in type_map:
        return type_map["all"]

    return [
        ConditionCheck(
            id=1,
            description=f"No pre-defined conditions for '{scenario_type}'",
            law="",
            terminal=True,
        )
    ]
