"""Unit test suite cho Domain Policy `video_edit_plan.py`."""

import pytest

from core.enums import VideoCaptionStyle
from domain.policies.video_edit_plan import (
    default_edit_plan_for_short_form,
    validate_edit_plan,
)
from domain.ports.video_renderer import InvalidEditPlanError


def test_validate_default_short_form_edit_plan():
    plan_dict = default_edit_plan_for_short_form(30.0, hook_text="Bí quyết dưỡng sinh 3s")
    plan = validate_edit_plan(plan_dict)

    assert plan.target_aspect_ratio == "9:16"
    assert plan.target_duration_seconds == 30.0
    assert len(plan.cuts) == 1
    assert plan.cuts[0].start_ms == 0
    assert plan.cuts[0].end_ms == 30000
    assert len(plan.captions) == 1
    assert plan.captions[0].text == "Bí quyết dưỡng sinh 3s"
    assert plan.captions[0].style == VideoCaptionStyle.BOLD_YELLOW


def test_validate_edit_plan_rejects_invalid_aspect_ratio():
    with pytest.raises(InvalidEditPlanError, match="không hỗ trợ"):
        validate_edit_plan({"target_aspect_ratio": "4:3", "target_duration_seconds": 15})


def test_validate_edit_plan_rejects_out_of_bounds_duration():
    with pytest.raises(InvalidEditPlanError, match="Thời lượng video phải từ"):
        validate_edit_plan({"target_aspect_ratio": "9:16", "target_duration_seconds": 1.0})


def test_validate_edit_plan_rejects_invalid_cuts():
    # start_ms >= end_ms
    with pytest.raises(InvalidEditPlanError, match="phải nhỏ hơn end_ms"):
        validate_edit_plan(
            {
                "target_aspect_ratio": "9:16",
                "target_duration_seconds": 15,
                "cuts": [{"start_ms": 5000, "end_ms": 2000}],
            }
        )


def test_validate_edit_plan_rejects_empty_caption_text():
    with pytest.raises(InvalidEditPlanError, match="không được để trống text"):
        validate_edit_plan(
            {
                "target_aspect_ratio": "9:16",
                "target_duration_seconds": 15,
                "captions": [{"text": "   ", "start_ms": 0, "end_ms": 2000}],
            }
        )
