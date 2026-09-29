from fastapi import APIRouter, HTTPException

from data.learning import LEARNING_CONTENTS


router = APIRouter(
    prefix="/api/learning",
    tags=["learning"],
)


@router.get("")
def get_learning_contents():
    return LEARNING_CONTENTS


@router.get("/{content_id}")
def get_learning_content(content_id: str):
    content = next(
        (
            item
            for item in LEARNING_CONTENTS
            if item["id"] == content_id
        ),
        None,
    )

    if content is None:
        raise HTTPException(
            status_code=404,
            detail="학습 콘텐츠를 찾을 수 없습니다.",
        )

    return content
