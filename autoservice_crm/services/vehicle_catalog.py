from __future__ import annotations

POPULAR_MAKES_MODELS = {
    "Audi": ["A3", "A4", "A6", "Q3", "Q5", "Q7"],
    "BMW": ["1 Series", "3 Series", "5 Series", "X3", "X5", "X6"],
    "Chevrolet": ["Cruze", "Malibu", "Tahoe", "Tracker"],
    "Ford": ["Focus", "Fusion", "Kuga", "Mondeo", "Mustang", "Explorer"],
    "Honda": ["Accord", "Civic", "CR-V", "Pilot"],
    "Hyundai": ["Accent", "Elantra", "Santa Fe", "Solaris", "Sonata", "Tucson"],
    "Kia": ["Ceed", "K5", "Optima", "Rio", "Sorento", "Sportage"],
    "Lada": ["Granta", "Largus", "Niva Legend", "Vesta", "XRAY"],
    "Lexus": ["ES", "GX", "LX", "NX", "RX"],
    "Mazda": ["CX-5", "CX-9", "Mazda 3", "Mazda 6"],
    "Mercedes-Benz": ["A-Class", "C-Class", "E-Class", "GLE", "GLS", "S-Class"],
    "Mitsubishi": ["ASX", "L200", "Outlander", "Pajero Sport"],
    "Nissan": ["Almera", "Juke", "Qashqai", "Teana", "X-Trail"],
    "Renault": ["Arkana", "Duster", "Kaptur", "Logan", "Sandero"],
    "Skoda": ["Karoq", "Kodiaq", "Octavia", "Rapid", "Superb"],
    "Subaru": ["Forester", "Impreza", "Outback", "XV"],
    "Tesla": ["Model 3", "Model S", "Model X", "Model Y"],
    "Toyota": ["Camry", "Corolla", "Land Cruiser", "RAV4", "Yaris"],
    "Volkswagen": ["Golf", "Passat", "Polo", "Tiguan", "Touareg"],
    "Volvo": ["S60", "S90", "XC40", "XC60", "XC90"],
}

_MODELS_BY_MAKE_LOWER = {
    make.lower(): models for make, models in POPULAR_MAKES_MODELS.items()
}


def get_popular_makes() -> list[str]:
    return sorted(POPULAR_MAKES_MODELS.keys())


def get_models_for_make(make: str) -> list[str]:
    return _MODELS_BY_MAKE_LOWER.get((make or "").strip().lower(), [])
