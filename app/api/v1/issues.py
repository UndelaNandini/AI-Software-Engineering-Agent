from typing import List
from fastapi import APIRouter, HTTPException, status

from app.agents.planner import issue_planner
from app.models.schemas import (
    ImplementationPlan,
    IssuePlanRequest,
    PlanUpdateRequest,
)

router = APIRouter()


@router.post(
    "/plan",
    response_model=ImplementationPlan,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Implementation Plan",
    description="Analyzes an issue description against the repository and produces a structured, human-approvable implementation plan.",
)
async def create_implementation_plan(request: IssuePlanRequest) -> ImplementationPlan:
    try:
        plan = issue_planner.generate_plan(request)
        return plan
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Plan generation failed: {str(e)}",
        )


@router.get(
    "/plans/{plan_id}",
    response_model=ImplementationPlan,
    status_code=status.HTTP_200_OK,
    summary="Get Implementation Plan",
    description="Retrieve a previously generated implementation plan by its unique ID.",
)
async def get_plan(plan_id: str) -> ImplementationPlan:
    plan = issue_planner.get_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan not found with ID: {plan_id}",
        )
    return plan


@router.patch(
    "/plans/{plan_id}",
    response_model=ImplementationPlan,
    status_code=status.HTTP_200_OK,
    summary="Update or Approve Plan",
    description="Approve, reject, or modify steps in an implementation plan prior to code execution.",
)
async def update_plan(plan_id: str, update: PlanUpdateRequest) -> ImplementationPlan:
    updated = issue_planner.update_plan(plan_id, update)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan not found with ID: {plan_id}",
        )
    return updated


@router.get(
    "/plans",
    response_model=List[ImplementationPlan],
    status_code=status.HTTP_200_OK,
    summary="List Implementation Plans",
    description="List all generated implementation plans.",
)
async def list_plans() -> List[ImplementationPlan]:
    return issue_planner.list_plans()
