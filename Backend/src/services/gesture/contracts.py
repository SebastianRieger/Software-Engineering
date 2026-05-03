from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from schemas.gestures import GestureType

GesturePhase = Literal["idle", "preparing", "holding", "committing", "releasing", "cooldown"]


@dataclass(frozen=True, slots=True)
class GestureContract:
    contract_id: str
    spec_id: str
    gesture: GestureType
    display_name: str
    start_pose: str
    motion_profile: str
    end_pose: str
    tempo_hint: str
    recording_notes: tuple[str, ...]
    detector_bias: tuple[str, ...]
    required_primitives: tuple[str, ...]
    forbidden_primitives: tuple[str, ...] = ()
    allowed_phases: tuple[GesturePhase, ...] = ()
    min_hand_count: int = 1
    max_hand_count: int = 1
    score_threshold: float = 0.45
    priority: int = 0


def default_gesture_contracts() -> dict[GestureType, GestureContract]:
    contracts = [
        GestureContract(
            contract_id="gesture_contract.swipe_left.v2",
            spec_id="gesture.swipe_left.v1",
            gesture="swipe_left",
            display_name="Swipe links",
            start_pose="offene handflaeche in der mittleren kamerazone",
            motion_profile="aus der mitte stabil nach links ziehen",
            end_pose="handflaeche zeigt am ende nach links",
            tempo_hint="klarer commit statt rueckfuehrbewegung",
            recording_notes=(
                "vor jedem swipe zuerst die mittlere startposition mit offener handflaeche einnehmen",
                "die endpose soll die wischrichtung klar anzeigen und nicht sofort in die mitte zurueckfedern",
            ),
            detector_bias=("open_palm_preferred", "mid_zone_start_preferred", "directional_finish_preferred"),
            required_primitives=("swipe_vector_left",),
            allowed_phases=("preparing", "committing", "releasing"),
            score_threshold=0.4,
            priority=40,
        ),
        GestureContract(
            contract_id="gesture_contract.swipe_right.v2",
            spec_id="gesture.swipe_right.v1",
            gesture="swipe_right",
            display_name="Swipe rechts",
            start_pose="offene handflaeche in der mittleren kamerazone",
            motion_profile="aus der mitte stabil nach rechts ziehen",
            end_pose="handflaeche zeigt am ende nach rechts",
            tempo_hint="klarer commit statt rueckfuehrbewegung",
            recording_notes=(
                "vor jedem swipe zuerst die mittlere startposition mit offener handflaeche einnehmen",
                "die endpose soll die wischrichtung klar anzeigen und nicht sofort in die mitte zurueckfedern",
            ),
            detector_bias=("open_palm_preferred", "mid_zone_start_preferred", "directional_finish_preferred"),
            required_primitives=("swipe_vector_right",),
            allowed_phases=("preparing", "committing", "releasing"),
            score_threshold=0.4,
            priority=40,
        ),
        GestureContract(
            contract_id="gesture_contract.swipe_up.v2",
            spec_id="gesture.swipe_up.v1",
            gesture="swipe_up",
            display_name="Swipe hoch",
            start_pose="offene handflaeche in der mittleren kamerazone",
            motion_profile="aus der mitte stabil nach oben ziehen",
            end_pose="handflaeche zeigt am ende nach oben",
            tempo_hint="klarer commit statt reinem anheben in die mitte",
            recording_notes=(
                "vor jedem swipe zuerst die mittlere startposition mit offener handflaeche einnehmen",
                "das ende der geste soll eine echte richtungsentscheidung nach oben zeigen",
            ),
            detector_bias=("open_palm_preferred", "mid_zone_start_preferred", "directional_finish_preferred"),
            required_primitives=("swipe_vector_up",),
            allowed_phases=("preparing", "committing", "releasing"),
            score_threshold=0.4,
            priority=38,
        ),
        GestureContract(
            contract_id="gesture_contract.swipe_down.v2",
            spec_id="gesture.swipe_down.v1",
            gesture="swipe_down",
            display_name="Swipe runter",
            start_pose="offene handflaeche in der mittleren kamerazone",
            motion_profile="aus der mitte stabil nach unten ziehen",
            end_pose="handflaeche zeigt am ende nach unten",
            tempo_hint="klarer commit statt schmaler rueckfuehrbewegung",
            recording_notes=(
                "vor jedem swipe zuerst die mittlere startposition mit offener handflaeche einnehmen",
                "das ende der geste soll eine echte richtungsentscheidung nach unten zeigen",
            ),
            detector_bias=("open_palm_preferred", "mid_zone_start_preferred", "directional_finish_preferred"),
            required_primitives=("swipe_vector_down",),
            allowed_phases=("preparing", "committing", "releasing"),
            score_threshold=0.4,
            priority=38,
        ),
        GestureContract(
            contract_id="gesture_contract.circle.v2",
            spec_id="gesture.circle.v1",
            gesture="circle",
            display_name="Kreis",
            start_pose="faust in der mittleren kamerazone",
            motion_profile="von der mitte einen geschlossenen kreis bis zur ursprungsposition ziehen",
            end_pose="nach kreisabschluss hand oeffnen und nach unten absenken",
            tempo_hint="gleichmaessige kreisbewegung statt punktweiser richtungswechsel",
            recording_notes=(
                "die faust soll vor oder spaetestens in der mittleren startposition geschlossen sein",
                "der kreis soll geschlossen zurueck zur ursprungsposition laufen, bevor die hand geoeffnet wird",
            ),
            detector_bias=("fist_preferred", "center_anchor_preferred", "closed_loop_required"),
            required_primitives=("circular_motion",),
            allowed_phases=("preparing", "committing", "releasing"),
            score_threshold=0.52,
            priority=45,
        ),
        GestureContract(
            contract_id="gesture_contract.push_click_short.v2",
            spec_id="gesture.push_click_short.v1",
            gesture="push_click_short",
            display_name="Kurzer Klick",
            start_pose="zentrierter index-push mit eingeklappten restfingern",
            motion_profile="schneller vorwaerts-commit mit frueher release-phase",
            end_pose="release zur neutralen tiefe ohne lange haltephase",
            tempo_hint="schneller als der lange klick",
            recording_notes=(
                "die unterscheidung zum langen klick soll ueber vorwaertstempo und kurze haltedauer sichtbar sein",
                "nach dem commit frueh loesen statt die pose stabil zu halten",
            ),
            detector_bias=("fast_commit_preferred", "brief_hold_preferred", "release_confirmed"),
            required_primitives=("index_primary", "push_forward", "hand_centered"),
            forbidden_primitives=("all_fingers_open",),
            allowed_phases=("idle", "preparing", "releasing", "committing", "holding"),
            score_threshold=0.56,
            priority=55,
        ),
        GestureContract(
            contract_id="gesture_contract.push_click_long.v2",
            spec_id="gesture.push_click_long.v1",
            gesture="push_click_long",
            display_name="Langer Klick",
            start_pose="zentrierter index-push mit eingeklappten restfingern",
            motion_profile="bewusster vorwaerts-commit mit stabiler haltephase",
            end_pose="release erst nach erkennbarer haltezeit",
            tempo_hint="langsamer commit plus sichtbare haltephase",
            recording_notes=(
                "die unterscheidung zum kurzen klick soll ueber ruhigere einleitung und stabile haltephase sichtbar sein",
                "release erst nach klarer haltedauer statt sofortigem loesen",
            ),
            detector_bias=("stable_hold_required", "slower_commit_preferred", "release_confirmed"),
            required_primitives=("index_primary", "push_forward", "stable_hold", "hand_centered"),
            forbidden_primitives=("all_fingers_open",),
            allowed_phases=("idle", "preparing", "holding", "releasing", "committing"),
            score_threshold=0.58,
            priority=60,
        ),
        GestureContract(
            contract_id="gesture_contract.zoom_out_hands.v1",
            spec_id="gesture.zoom_out_hands.v1",
            gesture="zoom_out_hands",
            display_name="Zwei-Hand-Zoom zusammen",
            start_pose="zwei haende deutlich getrennt vor der kamera",
            motion_profile="symmetrisch zueinander fuehren",
            end_pose="haende nah beieinander",
            tempo_hint="gleichmaessige symmetrische kontraktion",
            recording_notes=(
                "beide haende sollen gleichzeitig und moeglichst symmetrisch laufen",
            ),
            detector_bias=("two_hand_symmetry_preferred",),
            required_primitives=("two_hand_contract",),
            allowed_phases=("preparing", "committing", "releasing"),
            min_hand_count=2,
            max_hand_count=2,
            score_threshold=0.54,
            priority=50,
        ),
        GestureContract(
            contract_id="gesture_contract.zoom_in_hands.v1",
            spec_id="gesture.zoom_in_hands.v1",
            gesture="zoom_in_hands",
            display_name="Zwei-Hand-Zoom auseinander",
            start_pose="zwei haende nah beieinander vor der kamera",
            motion_profile="symmetrisch auseinanderziehen",
            end_pose="haende deutlich weiter auseinander",
            tempo_hint="gleichmaessige symmetrische expansion",
            recording_notes=(
                "beide haende sollen gleichzeitig und moeglichst symmetrisch laufen",
            ),
            detector_bias=("two_hand_symmetry_preferred",),
            required_primitives=("two_hand_expand",),
            allowed_phases=("preparing", "committing", "releasing"),
            min_hand_count=2,
            max_hand_count=2,
            score_threshold=0.54,
            priority=50,
        ),
    ]
    return {contract.gesture: contract for contract in contracts}


def get_gesture_contract(gesture: GestureType) -> GestureContract:
    return default_gesture_contracts()[gesture]