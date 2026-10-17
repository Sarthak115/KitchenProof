"""FSSAI Hygiene Rating-style check pool (§6.2). Only camera-verifiable checks.

Check IDs are mirrored in frontend/src/lib/checks.ts for labels.
"""

from dataclasses import dataclass

SEVERITY_PENALTY = {"critical": 30, "high": 15, "medium": 8, "low": 4}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@dataclass(frozen=True)
class Check:
    id: str
    prompt: str  # shown to the owner; may contain {orderId}
    verify: str  # what Gemini verifies
    severity: str
    fix: str  # offline fallback fix step for the Coach


CHECKS: dict[str, Check] = {
    c.id: c
    for c in [
        Check(
            "pests",
            "Show the floor under the stove and the corners of the room",
            "No droppings, cockroaches, larvae or rodent signs",
            "critical",
            "Book a pest control visit and seal gaps under the stove and in room corners.",
        ),
        Check(
            "fridge_segregation",
            "Open the fridge and show each shelf slowly",
            "Raw meat/fish is not stored above cooked or ready-to-eat food; veg and non-veg are "
            "separated; food is covered",
            "critical",
            "Move raw meat and fish to the bottom shelf in covered trays, below cooked food.",
        ),
        Check(
            "fridge_temp",
            "Bring the camera close to the fridge thermometer",
            "Thermometer reading is visible and at or below 5 °C",
            "high",
            "Keep a thermometer in the fridge and set it to 5 °C or colder.",
        ),
        Check(
            "handwash",
            "Show the handwash sink and turn on the tap",
            "Soap present, running water, basin clean",
            "high",
            "Keep soap at the handwash sink and clean the basin every shift.",
        ),
        Check(
            "handler_hygiene",
            "Show the person cooking from the shoulders down",
            "Head covering, gloves or clean hands, clean apron (do not identify the person)",
            "high",
            "Give every cook a head covering and a clean apron for each shift.",
        ),
        Check(
            "order_prep",
            "Show order #{orderId} being prepared right now",
            "Active cooking or plating is visible; handler hygiene during preparation",
            "high",
            "Make sure staff wear head coverings and use clean hands or gloves while plating.",
        ),
        Check(
            "dustbins",
            "Show your dustbins with their lids",
            "Lid present and closed, bin not overflowing",
            "medium",
            "Use dustbins with lids, keep them closed and empty them before they overflow.",
        ),
        Check(
            "surfaces",
            "Show the cutting boards and the main cooking counter",
            "No visible grime, stains or food residue build-up",
            "medium",
            "Scrub cutting boards and the counter with hot soapy water after each rush.",
        ),
        Check(
            "drains",
            "Show the floor drain",
            "Grating present, no standing waste",
            "medium",
            "Fit a grating on the floor drain and clear it at closing time.",
        ),
        Check(
            "dry_storage",
            "Show where you store flour, rice and vegetables",
            "Stored off the floor on racks; containers and sacks closed",
            "medium",
            "Store sacks and containers on racks off the floor and keep them closed.",
        ),
        Check(
            "labels_expiry",
            "Show the labels of two packaged ingredients",
            "Expiry date readable and not past today's date",
            "medium",
            "Check expiry dates weekly and use older stock first.",
        ),
        Check(
            "oil_condition",
            "Show the frying oil in the kadhai or fryer",
            "Oil is not visibly black or foaming (visual only: flag, do not certify)",
            "medium",
            "Change frying oil when it turns dark or starts foaming.",
        ),
        Check(
            "walls_ceiling",
            "Slowly show the walls and ceiling above the cooking area",
            "No heavy grease, mould or peeling paint over food areas",
            "low",
            "Degrease the walls above the stove and repair peeling paint over food areas.",
        ),
        Check(
            "fssai_board",
            "Show your FSSAI licence on the wall",
            "Licence or registration is visible and the number is readable",
            "low",
            "Display your FSSAI licence where it can be clearly seen.",
        ),
        Check(
            "pest_control_record",
            "Show your last pest control certificate",
            "A dated pest control document is visible",
            "low",
            "Keep the latest pest control certificate in a file in the kitchen.",
        ),
        Check(
            "water_source",
            "Show your drinking-water filter or source",
            "Filter or source present and clean",
            "low",
            "Service the drinking-water filter on schedule and keep it clean.",
        ),
    ]
}


def by_severity(severity: str, exclude: set[str] | None = None) -> list[str]:
    exclude = exclude or set()
    return [c.id for c in CHECKS.values() if c.severity == severity and c.id not in exclude]


def prompt_for(check_id: str, order_id: str | None = None) -> str:
    text = CHECKS[check_id].prompt
    return text.replace("{orderId}", order_id or "the current order")
