"""Treatment advice lookup for CropWatch diagnoses."""

from __future__ import annotations

from typing import Any

EXPERT_REFERRAL = "Contact your local agricultural extension office."

_ADVICE: dict[str, dict[str, Any]] = {
    "Early blight": {
        "message": (
            "Early blight often starts on older leaves. Reduce leaf wetness "
            "and remove infected tissue before it spreads."
        ),
        "steps": [
            "Pick off and destroy badly spotted leaves; do not compost them.",
            "Space plants and prune lower foliage to improve airflow.",
            "Water at the soil line and avoid wetting leaves.",
            "Mulch soil to limit splash of spores onto foliage.",
            "Check locally approved fungicides with your extension officer.",
        ],
    },
    "Late blight": {
        "message": (
            "Late blight can move quickly in cool, wet weather. Act early "
            "and keep foliage as dry as you can."
        ),
        "steps": [
            "Remove and destroy plants with spreading brown lesions.",
            "Increase spacing and airflow around remaining plants.",
            "Avoid overhead watering, especially in the evening.",
            "Do not save seed or tubers from infected plants.",
            "Check locally approved fungicides with your extension officer.",
        ],
    },
    "Leaf mold": {
        "message": (
            "Leaf mold thrives in humid, still air. Drying the canopy is "
            "the first line of control."
        ),
        "steps": [
            "Remove the most affected leaves and dispose of them off-field.",
            "Open the canopy so air can move through the plants.",
            "Reduce humidity by watering in the morning at soil level.",
            "Avoid crowding new plantings in the same humid spot.",
            "Check locally approved fungicides with your extension officer.",
        ],
    },
    "Septoria leaf spot": {
        "message": (
            "Septoria spreads by splash. Keep lower leaves dry and remove "
            "infected debris."
        ),
        "steps": [
            "Strip lower leaves that show small dark spots with pale centers.",
            "Mulch to stop rain from splashing soil onto stems.",
            "Water the soil, not the leaves, and improve airflow.",
            "Rotate away from tomatoes and related crops next season.",
            "Check locally approved fungicides with your extension officer.",
        ],
    },
    "Gray leaf spot": {
        "message": (
            "Gray leaf spot builds when maize stays wet. Residue and dense "
            "stands make it worse."
        ),
        "steps": [
            "Remove heavily diseased leaves from small plots where practical.",
            "Avoid overhead irrigation and water earlier in the day.",
            "Rotate with non-host crops and bury or remove old maize residue.",
            "Do not overcrowd plants so the canopy can dry after rain.",
            "Check locally approved fungicides with your extension officer.",
        ],
    },
    "Northern leaf blight": {
        "message": (
            "Northern leaf blight favors long dew periods. Cultural cleanup "
            "slows the next cycle."
        ),
        "steps": [
            "Remove the worst-affected leaves on young plants if you can.",
            "Improve airflow with sensible spacing on the next planting.",
            "Plow under or remove old maize trash after harvest.",
            "Rotate out of maize for at least one season if blight was severe.",
            "Check locally approved fungicides with your extension officer.",
        ],
    },
    "Common rust": {
        "message": (
            "Common rust needs moisture on leaves. Keep plants drier and "
            "watch new pustules."
        ),
        "steps": [
            "Avoid working plants while leaves are wet.",
            "Water at the base and keep irrigation off the foliage.",
            "Remove volunteer maize that can carry rust nearby.",
            "Rotate crops and avoid dense, humid plantings.",
            "Check locally approved fungicides with your extension officer.",
        ],
    },
    "Bacterial leaf blight": {
        "message": (
            "Bacterial leaf blight spreads with rain splash and wounds. "
            "Sanitation matters more than extra watering."
        ),
        "steps": [
            "Remove badly streaked leaves and keep them out of irrigation water.",
            "Avoid walking fields when plants are wet.",
            "Do not use overhead watering if you can irrigate at soil level.",
            "Rotate rice with a non-host crop and use clean seed next season.",
            "Check locally approved products with your extension officer.",
        ],
    },
    "Brown spot": {
        "message": (
            "Brown spot is worse on stressed rice. Strengthen the crop and "
            "reduce long leaf wetness."
        ),
        "steps": [
            "Remove severely spotted leaves from small plots.",
            "Improve drainage so plants are not left in standing water too long.",
            "Avoid overhead watering late in the day.",
            "Rotate crops and use healthy seed in the next planting.",
            "Check locally approved fungicides with your extension officer.",
        ],
    },
    "Leaf blast": {
        "message": (
            "Leaf blast can expand fast in humid weather. Reduce dense, "
            "wet canopies first."
        ),
        "steps": [
            "Roguing badly blasted plants from small patches.",
            "Avoid late, heavy nitrogen that makes lush, susceptible growth.",
            "Water in a way that lets leaves dry during the day.",
            "Destroy infected residues after harvest where possible.",
            "Check locally approved fungicides with your extension officer.",
        ],
    },
    "Healthy": {
        "message": (
            "No disease was identified with high confidence. Keep scouting "
            "and maintain good growing conditions."
        ),
        "steps": [
            "Continue weekly checks of older and inner leaves.",
            "Keep airflow and avoid unnecessary wetting of foliage.",
            "Remove only leaves that later show clear disease signs.",
            "Record weather and any new symptoms for the next visit.",
            "Ask your extension officer if the crop changes quickly.",
        ],
    },
}

_LOW_CONFIDENCE = {
    "message": (
        "The photo could not be judged with enough confidence. Please "
        "confirm the problem with a local expert before treating."
    ),
    "steps": [
        "Take a sharper photo of several leaves in natural light.",
        "Note which parts of the plant are affected and how fast it spread.",
        "Collect a sample in a clean bag if an extension officer requests it.",
        "Avoid spraying until the cause is confirmed.",
    ],
}


def get_advice(disease: str, low_confidence: bool) -> dict[str, Any]:
    """Return the advice object for a disease or the expert-referral path."""
    if low_confidence:
        return {
            "message": _LOW_CONFIDENCE["message"],
            "steps": list(_LOW_CONFIDENCE["steps"]),
            "low_confidence": True,
            "expert_referral": EXPERT_REFERRAL,
        }
    entry = _ADVICE.get(
        disease,
        {
            "message": (
                "Follow general sanitation and ask an extension officer "
                "before applying any product."
            ),
            "steps": [
                "Remove the worst-affected leaves and destroy them.",
                "Improve airflow and avoid overhead watering.",
                "Rotate crops when you replant this plot.",
                "Check locally approved fungicides with your extension officer.",
            ],
        },
    )
    return {
        "message": entry["message"],
        "steps": list(entry["steps"]),
        "low_confidence": False,
        "expert_referral": EXPERT_REFERRAL,
    }
