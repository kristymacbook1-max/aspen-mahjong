"""§263A farming — preproductive-period costs of plants and animals
produced in a farming business (§263A(d)/(e); Reg. §1.263A-4).

DECISION ORDER:
1. Taxpayer-level gates, in order:
   a. profile.small_business_exempt (§263A(i)): EVERYTHING is deducted
      currently — "§263A(i) small-business exception — farming UNICAP
      off." Early return mirroring analysis.compute_unicap's exempt
      shape: an `exempt: True` dict with zeroed capitalization and the
      deductible total (plus the §448(c) threshold-estimate warning when
      the tax year has no published figure on file).
   b. required_447_accrual is None -> OPEN QUESTION (is the taxpayer a
      corporation or partnership required to use an accrual method under
      §447, or a tax shelter prohibited from using the cash method under
      §448(a)(3)? — the §263A(d)(1) exceptions are UNAVAILABLE to those
      taxpayers) and the engine proceeds CONSERVATIVELY treating the
      answer as True (exceptions unavailable); every group whose outcome
      rests on that assumption carries flag 447-STATUS-UNKNOWN. When
      profile.is_tax_shelter is True the §447 answer is MOOT — the same
      flush-language bar applies regardless — so no question and no flag
      are emitted.
2. Per group:
   a. Negative preproductive_costs -> flag NEGATIVE-AMOUNT, treatment
      "sme_review", nothing computed (house pattern: a cost cannot be
      negative).
   b. ANIMALS (§263A(d)(1)(A)(ii)): exempt — deducted currently
      ("animal_exempt_deduct") UNLESS the taxpayer is required to use
      accrual under §447 or is a tax shelter — those must capitalize
      ("animal_capitalize_447").
   c. PLANTS: preproductive_period_over_2yr is the nationwide weighted
      average preproductive-period determination (§263A(e)(3)(B) — the
      IRS publishes the >2-year crop list; the determination is an
      INPUT here, never guessed).
      False -> exempt, deducted currently ("plant_exempt_deduct",
      §263A(d)(1)(A)(i)) — with the SAME §447/tax-shelter carve-out as
      animals: the flush language of §263A(d)(1) denies the exception
      to §447-required taxpayers and tax shelters for BOTH prongs
      (animals AND ≤2-year plants). That conservative reading is
      implemented here; affected items capitalize as
      "plant_capitalize_447" with flag 263AD1-FLUSH-READING.
      None -> OPEN QUESTION (is the crop on the IRS >2-year
      nationwide-weighted-average list?) + conservative CAPITALIZE
      ("open_question_capitalize_pending") with flag
      PREPRODUCTIVE-PERIOD-UNKNOWN.
      True -> capitalize the preproductive costs
      ("preproductive_capitalize", §263A(d)/(e)(3)); the capitalized
      amount attaches to the plant's basis — recovery is out of scope.
   d. §263A(d)(3) ELECTION OUT (election_out_263Ad3 AND
      group.in_election_out_year), evaluated on groups that would
      otherwise capitalize under (b)/(c): available only if the taxpayer
      is NOT required to use accrual under §447 and is NOT a tax
      shelter — the election is unavailable to them (the
      §263A(d)(3)(B)-style limitation); if barred, warning
      ELECTION-OUT-UNAVAILABLE and the election is IGNORED for that
      group (the capitalize result stands). When it applies: deduct
      currently ("election_out_deduct"), BUT emit ONCE PER RUN the two
      statutory consequences as warnings: ELECTION-OUT-ADS-REQUIRED
      (§263A(e)(2): ADS depreciation on ALL farming property placed in
      service in any election year — not computed here) and
      ELECTION-OUT-1245-RECHARACTERIZATION (§263A(e)(1): gain on
      disposition recaptured as ordinary income to the extent of the
      deducted preproductive costs — not computed here). A
      period-unknown plant group under a valid election deducts under
      the election (deduct is the outcome under either answer) but
      KEEPS the PREPRODUCTIVE-PERIOD-UNKNOWN flag and open question —
      the answer still scopes the §263A(e) consequences.
3. Totals: capitalized_total and deductible_total are exact Decimal sums
   (no division occurs, so nothing is quantized); per-item rows carry
   treatment/authority/flags like tangible_263a.py. Tie:
   capitalized_total + deductible_total == sum of all non-sme_review
   preproductive_costs.

The OPEN QUESTIONS list is the point of this engine: every place a
determination needs a fact the schedule does not carry, a precise
question a non-specialist can answer is emitted (never duplicated).
Nothing is silently deducted on missing facts — an unknown §447 status
and an unknown preproductive period both CAPITALIZE conservatively
until answered.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from ..model import _dec


@dataclass
class FarmGroup:
    """One farming preproductive-cost group (a plant crop or animal class).

    preproductive_period_over_2yr is TRI-STATE: True/False when the
    nationwide weighted average preproductive-period determination is
    established (§263A(e)(3)(B) — the IRS publishes the >2-year crop
    list; the determination is an INPUT here, never guessed), None when
    the schedule does not carry it — None is never treated as False."""
    group_id: str = ""
    description: str = ""
    kind: str = "plant"                    # plant / animal
    # current-year preproductive-period costs for the group
    preproductive_costs: Decimal = Decimal("0")
    preproductive_period_over_2yr: Optional[bool] = None
    in_election_out_year: bool = False     # covered by a §263A(d)(3) election
    row_index: int = 0

    def __post_init__(self):
        self.preproductive_costs = _dec(self.preproductive_costs)


def compute_farming_unicap(
        groups: List[FarmGroup], profile, *,
        required_447_accrual: Optional[bool] = None,
        election_out_263Ad3: bool = False) -> dict:
    """Apply the module-docstring decision order to every group.

    Returns {exempt, items, open_questions, capitalized_total,
    deductible_total, warnings}. Tie: capitalized_total +
    deductible_total == sum of all non-sme_review preproductive_costs
    (exact Decimal sums, nothing quantized)."""
    # --- 1a. §263A(i) small-business exception ----------------------------
    if profile.small_business_exempt:
        w: List[str] = []
        if profile.sec448_threshold_is_estimate:
            w.append(
                f"§448(c) threshold for TY {profile.tax_year} is not on "
                f"file — the 2026 figure (${profile.sec448_threshold:,.0f}) "
                f"was used to determine the exemption. VERIFY: a higher "
                f"indexed threshold cannot change this result, but relying "
                f"on it should be documented.")
        return {"exempt": True,
                "note": "§263A(i) small-business exception — farming "
                        "UNICAP off.",
                "items": [],
                "open_questions": [],
                "capitalized_total": Decimal("0"),
                "deductible_total": sum(
                    (g.preproductive_costs for g in groups), Decimal("0")),
                "warnings": w}

    warnings: List[str] = []
    open_questions: List[dict] = []
    seen_questions: set = set()

    def ask(group_id: str, question: str, why: str) -> None:
        if question in seen_questions:
            return
        seen_questions.add(question)
        open_questions.append({"item_id": group_id,
                               "question": question, "why": why})

    # --- 1b. §447/§448(a)(3) status gate -----------------------------------
    unknown_447 = False
    if required_447_accrual is None:
        if profile.is_tax_shelter:
            # Moot: the flush-language bar applies to a tax shelter
            # regardless of the §447 answer — no question, no flag.
            effective_447 = False
        else:
            unknown_447 = True
            effective_447 = True   # conservative: exceptions unavailable
            ask("",
                "Is the taxpayer a corporation or partnership required to "
                "use an accrual method of accounting under §447, or a tax "
                "shelter prohibited from using the cash method under "
                "§448(a)(3)? Answer required_447_accrual True/False.",
                "The §263A(d)(1) exceptions (animals; plants with a "
                "preproductive period of 2 years or less) AND the "
                "§263A(d)(3) election out are UNAVAILABLE to those "
                "taxpayers. The engine proceeded CONSERVATIVELY treating "
                "the answer as True (exceptions unavailable); every group "
                "whose outcome rests on that assumption carries flag "
                "447-STATUS-UNKNOWN.")
    else:
        effective_447 = bool(required_447_accrual)
    exceptions_barred = effective_447 or profile.is_tax_shelter

    rows: List[dict] = []
    capitalized_total = Decimal("0")
    deductible_total = Decimal("0")
    consequences_warned = False

    for g in groups:
        row = {"group_id": g.group_id, "description": g.description,
               "kind": g.kind, "amount": g.preproductive_costs,
               "treatment": "", "authority": "", "flags": [],
               "deductible": Decimal("0"), "capitalized": Decimal("0")}
        label = g.group_id or g.description

        # --- 2a. negative amount ------------------------------------------
        if g.preproductive_costs < 0:
            row["treatment"] = "sme_review"
            row["flags"].append("NEGATIVE-AMOUNT")
            warnings.append(
                f"NEGATIVE-AMOUNT [farming {label}]: "
                f"${g.preproductive_costs:,.2f} — nothing computed; route "
                f"credits/refunds through the schedule, not a negative "
                f"preproductive cost.")
            rows.append(row)
            continue

        # --- 2b/2c. animals / plants (§263A(d)(1)) --------------------------
        capitalize = False
        if g.kind == "animal":
            if exceptions_barred:
                capitalize = True
                row["treatment"] = "animal_capitalize_447"
                row["authority"] = (
                    "§263A(d)(1) flush language — the animal exception "
                    "(§263A(d)(1)(A)(ii)) is unavailable to taxpayers "
                    "required to use an accrual method under §447 and to "
                    "tax shelters (§448(a)(3))")
                if unknown_447:
                    row["flags"].append("447-STATUS-UNKNOWN")
            else:
                row["treatment"] = "animal_exempt_deduct"
                row["authority"] = "§263A(d)(1)(A)(ii); Reg. §1.263A-4(a)(2)"
        else:  # plant
            if g.preproductive_period_over_2yr is False:
                if exceptions_barred:
                    # Conservative reading: the §263A(d)(1) flush language
                    # denies the exception to §447-required taxpayers and
                    # tax shelters for BOTH prongs — short-period plants
                    # of such a taxpayer still capitalize.
                    capitalize = True
                    row["treatment"] = "plant_capitalize_447"
                    row["authority"] = (
                        "§263A(d)(1) flush language — the ≤2-year-plant "
                        "exception (§263A(d)(1)(A)(i)) is unavailable to "
                        "taxpayers required to use an accrual method under "
                        "§447 and to tax shelters (§448(a)(3)); "
                        "conservative reading")
                    row["flags"].append("263AD1-FLUSH-READING")
                    if unknown_447:
                        row["flags"].append("447-STATUS-UNKNOWN")
                else:
                    row["treatment"] = "plant_exempt_deduct"
                    row["authority"] = ("§263A(d)(1)(A)(i); "
                                        "Reg. §1.263A-4(a)(2)")
            elif g.preproductive_period_over_2yr is None:
                capitalize = True
                row["treatment"] = "open_question_capitalize_pending"
                row["authority"] = (
                    "§263A(d)/(e)(3) — nationwide weighted average "
                    "preproductive period not established; capitalized "
                    "conservatively")
                row["flags"].append("PREPRODUCTIVE-PERIOD-UNKNOWN")
                ask(g.group_id,
                    f"Group {label} '{g.description}': is the crop on the "
                    f"IRS list of plants with a nationwide weighted average "
                    f"preproductive period of MORE than 2 years "
                    f"(§263A(e)(3)(B))? Answer preproductive_period_over_2yr "
                    f"True/False.",
                    "The >2-year determination comes from the published IRS "
                    "crop list — it is an input, never guessed. The group "
                    "is capitalized CONSERVATIVELY pending the answer; "
                    "under a §263A(d)(3) election the answer still scopes "
                    "the §263A(e) ADS/recapture consequences.")
            else:  # True
                capitalize = True
                row["treatment"] = "preproductive_capitalize"
                row["authority"] = (
                    "§263A(d); §263A(e)(3) preproductive-period costs; "
                    "Reg. §1.263A-4 — capitalized to the plant's basis "
                    "(recovery out of scope)")

        # --- 2d. §263A(d)(3) election out -----------------------------------
        if capitalize and election_out_263Ad3 and g.in_election_out_year:
            if exceptions_barred:
                row["flags"].append("ELECTION-OUT-UNAVAILABLE")
                if unknown_447 and "447-STATUS-UNKNOWN" not in row["flags"]:
                    row["flags"].append("447-STATUS-UNKNOWN")
                warnings.append(
                    f"ELECTION-OUT-UNAVAILABLE [farming {label}]: the "
                    f"§263A(d)(3) election out is unavailable to taxpayers "
                    f"required to use an accrual method under §447 and to "
                    f"tax shelters — the election was IGNORED for this "
                    f"group and the preproductive costs remain capitalized.")
            else:
                capitalize = False
                row["treatment"] = "election_out_deduct"
                row["authority"] = ("§263A(d)(3) election — §263A does not "
                                    "apply; deducted currently")
                if not consequences_warned:
                    consequences_warned = True
                    warnings.append(
                        "ELECTION-OUT-ADS-REQUIRED: §263A(e)(2) — with the "
                        "§263A(d)(3) election in effect, the alternative "
                        "depreciation system (ADS) is REQUIRED for ALL "
                        "property used predominantly in the farming "
                        "business and placed in service in any taxable "
                        "year for which the election is in effect — not "
                        "computed here; route the affected assets through "
                        "the depreciation workpaper.")
                    warnings.append(
                        "ELECTION-OUT-1245-RECHARACTERIZATION: §263A(e)(1) "
                        "— on disposition of a plant covered by the "
                        "election, gain is recaptured as ORDINARY income "
                        "(§1245 treatment) to the extent of the "
                        "preproductive-period costs deducted under the "
                        "election — not computed here; tracked at "
                        "disposition.")

        if capitalize:
            row["capitalized"] = g.preproductive_costs
            capitalized_total += g.preproductive_costs
        else:
            row["deductible"] = g.preproductive_costs
            deductible_total += g.preproductive_costs
        rows.append(row)

    return {"exempt": False,
            "items": rows,
            "open_questions": open_questions,
            "capitalized_total": capitalized_total,
            "deductible_total": deductible_total,
            "warnings": warnings}
