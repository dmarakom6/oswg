"""Mutate router - word mutation endpoint."""

from fastapi import APIRouter, HTTPException

from oswg.core.mutations import MutationEngine
from oswg.models import ErrorResponse, MutateRequest, MutateResponse

router = APIRouter()


@router.post(
    "/mutate",
    response_model=MutateResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def mutate_words(request: MutateRequest) -> MutateResponse:
    """Apply mutations to words."""
    try:
        engine = MutationEngine()

        config = {
            "enable_leet": request.enable_leet,
            "enable_numbers": request.enable_numbers,
            "enable_special": request.enable_special,
            "leet_level": request.leet_level,
        }

        mutations = engine.generate_all_mutations(request.words, config=config)
        mutations = list(dict.fromkeys(mutations))

        return MutateResponse(
            words=mutations,
            count=len(mutations),
            source_count=len(request.words),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
