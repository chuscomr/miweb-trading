# core/universos.py
# ══════════════════════════════════════════════════════════════
# FUENTE ÚNICA DE UNIVERSOS DE TICKERS
# Todo el sistema importa desde aquí. No duplicar en otros módulos.
# ══════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────
# IBEX 35
# ─────────────────────────────────────────────────────────────

IBEX35 = [
    "ACX.MC", "ACS.MC", "AENA.MC", "AMS.MC", "ANA.MC",
    "ANE.MC", "BBVA.MC", "BKT.MC", "CABK.MC", "CLNX.MC",
    "COL.MC", "ELE.MC", "ENG.MC", "FCC.MC", "FER.MC",
    "GRF.MC", "IAG.MC", "IBE.MC", "IDR.MC", "ITX.MC",
    "LOG.MC", "MAP.MC", "MRL.MC", "MTS.MC", "NTGY.MC",
    "PUIG.MC", "RED.MC", "REP.MC", "ROVI.MC", "SAB.MC",
    "SAN.MC", "SCYR.MC", "SLR.MC", "TEF.MC", "UNI.MC",
]

NOMBRES_IBEX = {
    "ACS.MC":  "ACS",
    "AENA.MC": "AENA",
    "AMS.MC":  "Amadeus",
    "ANA.MC":  "Acciona",
    "BBVA.MC": "BBVA",
    "CABK.MC": "CaixaBank",
    "ELE.MC":  "Endesa",
    "FER.MC":  "Ferrovial",
    "GRF.MC":  "Grifols",
    "IBE.MC":  "Iberdrola",
    "IAG.MC":  "IAG",
    "IDR.MC":  "Indra",
    "ITX.MC":  "Inditex",
    "MAP.MC":  "Mapfre",
    "MRL.MC":  "Merlin",
    "NTGY.MC": "Naturgy",
    "RED.MC":  "Redeia",
    "REP.MC":  "Repsol",
    "ROVI.MC": "Rovi",
    "SAB.MC":  "Sabadell",
    "SAN.MC":  "Santander",
    "SCYR.MC": "Sacyr",
    "SLR.MC":  "Solaria",
    "TEF.MC":  "Telefónica",
    "UNI.MC":  "Unicaja",
    "CLNX.MC": "Cellnex",
    "LOG.MC":  "Logista",
    "ACX.MC":  "Acerinox",
    "BKT.MC":  "Bankinter",
    "COL.MC":  "Colonial",
    "ANE.MC":  "Acciona Energía",
    "ENG.MC":  "Enagás",
    "FCC.MC":  "FCC",
    "PUIG.MC": "PUIG",
    "MTS.MC":  "ArcelorMittal",
    "ADX.MC":  "Audax Renovables",  # aparece en listas continuo también
}

# ─────────────────────────────────────────────────────────────
# MERCADO CONTINUO
# ─────────────────────────────────────────────────────────────

CONTINUO = [
    "CIE.MC", "VID.MC", "TUB.MC", "TRE.MC", "CAF.MC",
    "GEST.MC", "APAM.MC", "PHM.MC", "OHLA.MC", "DOM.MC",
    "ENC.MC", "GRE.MC", "ANE.MC", "HOME.MC", "CIRSA.MC",
    "FAE.MC", "NEA.MC", "PSG.MC", "LDA.MC", "MEL.MC",
    "VIS.MC", "ECR.MC", "ENO.MC", "DIA.MC", "IMC.MC",
    "LIB.MC", "A3M.MC", "ATRY.MC", "R4.MC", "RLIA.MC",
    "MVC.MC", "EBROM.MC", "AMP.MC", "HBX.MC", "CASH.MC",
    "ADX.MC", "IZER.MC", "AEDAS.MC",
]

NOMBRES_CONTINUO = {
    "CIE.MC":   "CIE Automotive",
    "VID.MC":   "Vidrala",
    "TUB.MC":   "Tubacex",
    "TRE.MC":   "Técnicas Reunidas",
    "CAF.MC":   "CAF",
    "GEST.MC":  "Gestamp",
    "APAM.MC":  "Applus",
    "PHM.MC":   "PharmaMar",
    "OHLA.MC":  "OHLA",
    "DOM.MC":   "Global Dominion",
    "ENC.MC":   "ENCE",
    "GRE.MC":   "Grenergy",
    "ANE.MC":   "Acciona Energía",
    "HOME.MC":  "Neinor Homes",
    "CIRSA.MC": "CIRSA",
    "FAE.MC":   "Faes Farma",
    "NEA.MC":   "Naturhouse",
    "PSG.MC":   "Prosegur",
    "LDA.MC":   "Línea Directa",
    "MEL.MC":   "Meliá",
    "VIS.MC":   "Viscofan",
    "ECR.MC":   "Ercros",
    "ENO.MC":   "Elecnor",
    "DIA.MC":   "DIA",
    "IMC.MC":   "Inmocentro",
    "LIB.MC":   "Libertas 7",
    "A3M.MC":   "Atresmedia",
    "ATRY.MC":  "Atrys Health",
    "R4.MC":    "Renta 4",
    "RLIA.MC":  "Realia Business",
    "MVC.MC":   "Metrovacesa",
    "EBROM.MC": "Ebro Foods",
    "AMP.MC":   "Amper",
    "HBX.MC":   "HBX Group",
    "CASH.MC":  "Cash Converters",
    "ADX.MC":   "Audax Renovables",
    "IZER.MC":  "Izertis",
    "AEDAS.MC": "AEDAS Homes",
}

# ─────────────────────────────────────────────────────────────
# UNIVERSO COMPLETO
# ─────────────────────────────────────────────────────────────

TODOS = list(dict.fromkeys(IBEX35 + CONTINUO))  # sin duplicados, orden preservado

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def get_nombre(ticker: str) -> str:
    """Devuelve el nombre legible de un ticker. Fallback al propio ticker."""
    return NOMBRES_IBEX.get(ticker) or NOMBRES_CONTINUO.get(ticker) or ticker


def es_ibex(ticker: str) -> bool:
    return ticker in IBEX35


def es_continuo(ticker: str) -> bool:
    return ticker in CONTINUO


def normalizar_ticker(ticker: str) -> str:
    """Añade .MC si no lleva sufijo de mercado."""
    ticker = ticker.strip().upper()
    if "." not in ticker:
        ticker += ".MC"
    return ticker
