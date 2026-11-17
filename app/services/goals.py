from datetime import date

from app.models import Goal
from app.schemas import GoalOut


def goal_to_out(goal: Goal, today: date | None = None) -> GoalOut:
    """Build the API response for a goal, including progress and pacing hints."""
    today = today or date.today()
    target = goal.target_amount
    saved = goal.saved_amount
    remaining = round(max(target - saved, 0.0), 2)
    progress = round(min(saved / target * 100, 100.0), 1) if target > 0 else 0.0
    complete = saved >= target

    days_left: int | None = None
    monthly_needed: float | None = None
    if goal.deadline is not None:
        days_left = (goal.deadline - today).days
        if not complete and days_left > 0:
            months_left = max(days_left / 30.44, 1.0)
            monthly_needed = round(remaining / months_left, 2)
        elif not complete:
            monthly_needed = remaining  # deadline passed (or today): everything is still due

    return GoalOut(
        id=goal.id,
        name=goal.name,
        target_amount=target,
        saved_amount=saved,
        deadline=goal.deadline,
        remaining=remaining,
        progress_percent=progress,
        is_complete=complete,
        days_left=days_left,
        monthly_needed=monthly_needed,
    )
