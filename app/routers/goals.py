from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import Goal
from app.schemas import Contribution, GoalCreate, GoalOut, GoalUpdate
from app.services.goals import goal_to_out

router = APIRouter()


def _get_owned_goal(db, goal_id: int, user_id: int) -> Goal:
    goal = db.get(Goal, goal_id)
    if goal is None or goal.owner_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Goal not found")
    return goal


@router.get("", response_model=list[GoalOut])
def list_goals(db: DbSession, current_user: CurrentUser):
    goals = db.scalars(
        select(Goal).where(Goal.owner_id == current_user.id).order_by(Goal.created_at, Goal.id)
    ).all()
    return [goal_to_out(goal) for goal in goals]


@router.post("", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(payload: GoalCreate, db: DbSession, current_user: CurrentUser):
    goal = Goal(**payload.model_dump(), owner_id=current_user.id)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal_to_out(goal)


@router.put("/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: int, payload: GoalUpdate, db: DbSession, current_user: CurrentUser):
    goal = _get_owned_goal(db, goal_id, current_user.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is None and field in ("name", "target_amount"):
            continue  # required columns: ignore explicit nulls (deadline may be cleared)
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return goal_to_out(goal)


@router.post("/{goal_id}/contribute", response_model=GoalOut)
def contribute(goal_id: int, payload: Contribution, db: DbSession, current_user: CurrentUser):
    """Add money to a goal (positive amount) or withdraw some (negative amount)."""
    goal = _get_owned_goal(db, goal_id, current_user.id)
    new_total = round(goal.saved_amount + payload.amount, 2)
    if new_total < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't withdraw more than is saved")
    goal.saved_amount = new_total
    db.commit()
    db.refresh(goal)
    return goal_to_out(goal)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: int, db: DbSession, current_user: CurrentUser):
    goal = _get_owned_goal(db, goal_id, current_user.id)
    db.delete(goal)
    db.commit()
