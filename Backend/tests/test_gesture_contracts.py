from services.gesture.contracts import default_gesture_contracts
from services.gesture.detection import default_gesture_specs


def test_gesture_contracts_define_recording_profiles_for_core_gestures():
    contracts = default_gesture_contracts()

    assert contracts["push_click_short"].tempo_hint == "schneller als der lange klick"
    assert (
        contracts["push_click_long"].tempo_hint
        == "langsamer commit plus sichtbare haltephase"
    )
    assert (
        contracts["swipe_up"].start_pose
        == "offene handflaeche in der mittleren kamerazone"
    )
    assert (
        contracts["circle"].start_pose
        == "kompakte hand oder faust in der mittleren kamerazone"
    )
    assert contracts["zoom_in_hands"].required_primitives == ("two_hand_expand",)
    assert contracts["zoom_out_hands"].required_primitives == ("two_hand_contract",)


def test_default_gesture_specs_are_derived_from_contracts():
    contracts = default_gesture_contracts()
    specs = default_gesture_specs()

    assert specs["push_click_short"].spec_id == contracts["push_click_short"].spec_id
    assert (
        specs["push_click_long"].required_primitives
        == contracts["push_click_long"].required_primitives
    )
    assert specs["swipe_left"].allowed_phases == contracts["swipe_left"].allowed_phases
    assert specs["zoom_out_hands"].min_hand_count == 2
