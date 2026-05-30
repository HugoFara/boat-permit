"""Registry of approved sources for Phase 1.

Every source here was explicitly approved (see project memory / handoff). The
legal boundary is hard: only public-domain law + clearly-reusable references.
Each entry records enough to (a) fetch it deterministically and (b) carry full
provenance + a licence note into the knowledge base.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    id: str                 # stable short id, also the raw-cache subdir
    name: str               # human label (carried into provenance)
    kind: str               # "fedlex" | "wikipedia" | "html"
    url: str                # canonical reference URL (for provenance)
    default_theme: str | None = None   # tagging fallback hint
    licence: str = ""       # licence / reuse note recorded per unit
    pin_theme: str | None = None  # mono-thematic source: pin instead of keyword-tag
    # Content language. fedlex acts are language-agnostic (fetched per requested
    # language via SPARQL); wikipedia/html sources are language-specific — their
    # `lang` is the language of the page and they're only built for that language.
    lang: str = "fr"
    # kind-specific knobs:
    eli: str = ""           # fedlex: ELI fragment used to resolve files via SPARQL
    want_pdf: bool = False  # fedlex: also fetch PDF/A for annex figures
    titles: tuple[str, ...] = field(default_factory=tuple)  # wikipedia page titles


SOURCES: list[Source] = [
    # --- Legal spine: public domain, cleanest licensing -------------------
    Source(
        id="oni",
        name="Ordonnance sur la navigation intérieure (ONI), RS 747.201.1",
        kind="fedlex",
        url="https://www.fedlex.admin.ch/eli/cc/1979/337_337_337/fr",
        eli="cc/1979/337_337_337",
        want_pdf=True,
        default_theme="lois",
        licence="Public domain — Swiss federal law (freely reusable).",
    ),
    Source(
        id="rnl",
        name="Règlement de la navigation sur le Léman (RNL), RS 747.221.1",
        kind="fedlex",
        url="https://www.fedlex.admin.ch/eli/cc/1978/1994_1993_1993/fr",
        eli="cc/1978/1994_1993_1993",
        want_pdf=False,
        default_theme="eaux_frontalieres",
        licence="Public domain — Franco-Swiss convention / Swiss federal law.",
    ),
    # --- Matelotage: CC BY-SA 4.0 (one Wikipedia source per language) -----
    Source(
        id="matelotage_wp",
        name="Wikipédia (FR) — nœuds marins (matelotage)",
        kind="wikipedia", lang="fr",
        url="https://fr.wikipedia.org/wiki/Nœud_(lien)",
        titles=("Nœud (lien)", "Nœud de chaise", "Demi-clé",
                "Nœud de taquet", "Tour mort et deux demi-clés"),
        default_theme="matelotage",
        licence="CC BY-SA 4.0 — Wikipédia (FR), attribution required.",
    ),
    Source(
        id="matelotage_wp_de",
        name="Wikipedia (DE) — Knoten (Seemannschaft)",
        kind="wikipedia", lang="de",
        url="https://de.wikipedia.org/wiki/Palstek",
        titles=("Palstek", "Kreuzknoten", "Webeleinenstek", "Roringstek",
                "Achtknoten"),
        default_theme="matelotage", pin_theme="matelotage",
        licence="CC BY-SA 4.0 — Wikipedia (DE), attribution required.",
    ),
    Source(
        id="matelotage_wp_it",
        name="Wikipedia (IT) — nodi marinareschi",
        kind="wikipedia", lang="it",
        url="https://it.wikipedia.org/wiki/Gassa_d'amante",
        titles=("Gassa d'amante", "Nodo barcaiolo", "Nodo Savoia", "Nodo piano"),
        default_theme="matelotage", pin_theme="matelotage",
        licence="CC BY-SA 4.0 — Wikipedia (IT), attribution required.",
    ),
    # --- Météo: official Swiss public-sector, reuse with attribution ------
    Source(
        id="meteo_vents",
        name="MétéoSuisse — Les vents du Léman",
        kind="html",
        url="https://www.meteosuisse.admin.ch/portrait/meteosuisse-blog/fr/2023/05/les-vents-du-leman.html",
        default_theme="meteorologie",
        pin_theme="meteorologie",   # whole page is about Léman winds
        licence="Official Swiss public-sector content — reuse with attribution.",
    ),
    Source(
        id="meteo_signaux",
        name="SISL — Signaux d'avis de tempête sur le Léman",
        kind="html",
        url="https://sisl.ch/blog-dynamic/52-signaux-d-avis-de-tempete-sur-le-leman-changements-2016",
        default_theme="meteorologie",
        pin_theme="meteorologie",   # storm-warning signals are a météo topic
        licence="SISL — licence not formally open; explanatory cross-check only, "
                "canonical rule is the RNL legal text.",
    ),
    # Météo (DE/IT): the MétéoSuisse "vents du Léman" blog is FR-only, but the
    # Léman winds and föhn are documented on German/Italian Wikipedia (CC BY-SA)
    # — incl. Joran and Vaudaire in German. These give DE/IT météo grounding.
    Source(
        id="meteo_wp_de",
        name="Wikipedia (DE) — Winde (Bise, Joran, Vaudaire, Föhn)",
        kind="wikipedia", lang="de",
        url="https://de.wikipedia.org/wiki/Bise",
        titles=("Bise", "Joran", "Vaudaire", "Föhn"),
        default_theme="meteorologie", pin_theme="meteorologie",
        licence="CC BY-SA 4.0 — Wikipedia (DE), attribution required.",
    ),
    Source(
        id="meteo_wp_it",
        name="Wikipedia (IT) — venti (Favonio, Bisa)",
        kind="wikipedia", lang="it",
        url="https://it.wikipedia.org/wiki/Favonio",
        titles=("Favonio", "Bisa", "Vento di caduta"),
        default_theme="meteorologie", pin_theme="meteorologie",
        licence="CC BY-SA 4.0 — Wikipedia (IT), attribution required.",
    ),
    # --- Cantonal completeness layer --------------------------------------
    Source(
        id="geneve",
        name="République et canton de Genève — Consignes générales de navigation",
        kind="html",
        url="https://www.ge.ch/naviguer-geneve/consignes-generales-navigation",
        default_theme="lois",
        licence="Official cantonal content — reuse with attribution.",
    ),
]

BY_ID: dict[str, Source] = {s.id: s for s in SOURCES}
