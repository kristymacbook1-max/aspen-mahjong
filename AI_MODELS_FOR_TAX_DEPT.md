# AI Models for a National Tax Department

A practical reference for picking the right model for the right job. Based on
the model lineup as of April 2026.

> **Before you read on:** never paste taxpayer PII or classified material into
> a consumer chat product. Use the enterprise / API tier with a signed BAA / DPA,
> zero-data-retention enabled, and (ideally) a tenancy that keeps data in your
> jurisdiction. For the most sensitive workloads, prefer self-hosted open-weights
> models (Llama, Kimi, DeepSeek, Mistral) running inside your own VPC.

---

## 1. Key terms (cheat sheet)

| Term | Plain-English meaning | Why a tax dept should care |
|---|---|---|
| **Token** | Roughly ¾ of a word; the unit models read and bill in. | Drives cost and context-window math. |
| **Context window** | Max input + output the model can hold at once (e.g. 200K or 1M tokens). | Determines whether you can stuff a whole audit file or tax code chapter in one prompt. |
| **Reasoning / "thinking" mode** | The model spends extra compute thinking step-by-step before answering. | Use for calculation review, legal analysis, anything where a wrong answer is costly. Slower and pricier. |
| **Multimodal** | Model can read images, PDFs, audio, sometimes video. | Reading scanned receipts, handwritten forms, charts in filings. |
| **Hallucination** | Confident-sounding but fabricated output (fake case cite, fake §). | The single biggest legal risk. Mitigated with RAG + citations + human review. |
| **RAG (Retrieval-Augmented Generation)** | Model is given relevant source docs at query time. | The right way to ask about *current* statute, regulations, rulings, internal manuals. |
| **Fine-tuning** | Permanently teaching a model your domain/style. | Good for letter templates, classification; rarely needed for knowledge — use RAG. |
| **Tool use / function calling** | Model can call calculators, databases, code. | Always route arithmetic, date math, and DB lookups through tools, not the LLM. |
| **Prompt caching** | Re-using a long static prompt at a discount. | Huge cost savings when you re-query against the same tax code or ruleset. |
| **Grounding / citations** | Model returns a source for each claim. | Required for any taxpayer-facing or court-facing output. |
| **Latency** | Time to first / last token. | Matters for live agent assist, less for overnight batch review. |
| **Data residency** | Where your data physically sits and is processed. | Often a legal requirement (EU, UK, CA, AU all have rules). |
| **Zero data retention (ZDR)** | Provider does not store prompts/outputs. | Standard requirement for PII workloads. |
| **Open weights** | Model file you can download and self-host. | Lets you run fully air-gapped — Llama, Kimi K2, DeepSeek, Mistral. |
| **Agentic** | Model can plan and run multi-step tool calls on its own. | Useful for "go pull this taxpayer's last 5 returns and flag anomalies" workflows. |
| **Eval** | Structured test set used to measure model quality on *your* tasks. | Build one before you commit to a vendor. |

---

## 2. Model lineup at a glance

| Model | Strengths | Watch-outs |
|---|---|---|
| **Claude Opus 4.7** | Best-in-class long-form reasoning, legal analysis, careful drafting, code; ~200K context with extended thinking. | Most expensive; slower than Sonnet. |
| **Claude Sonnet 4.6** | The workhorse — drafting, document review, summarization, coding, daily Q&A. Great cost/quality balance. | Not as deep on multi-step reasoning as Opus. |
| **Claude Haiku 4.5** | Fast and cheap — classification, routing, simple extraction, helpdesk. | Skips nuance; don't use for legal calls. |
| **OpenAI GPT-5** | Strong general model, very good multimodal (vision + voice), wide tool ecosystem. | Verify legal cites; data residency depends on tier. |
| **OpenAI GPT-5 mini** | Cheap, fast variant for high-volume tasks. | Same as above, less depth. |
| **OpenAI o-series (reasoning, e.g. o4)** | Math, formal logic, calculation chains. | Slow; overkill for prose. |
| **Google Gemini 2.5 Pro** | ~1M-token context, strong multimodal (PDFs, images, video, audio), good with spreadsheets. | Reasoning depth slightly behind Opus on legal nuance. |
| **Google Gemini 2.5 Flash** | Cheap, fast, multimodal — great for OCR-style ingest at scale. | Light on judgment. |
| **Moonshot Kimi K2** | Open-weights, very long context, strong agentic + coding, excellent for Chinese / CJK. | Smaller English legal corpus than US frontier labs. |
| **DeepSeek V3 / R1** | Open-weights, very cheap, strong math/reasoning. | Hosted endpoints raise sovereignty concerns; self-host if used. |
| **Mistral Large 2 / Mixtral** | EU-based, sovereignty-friendly, open-weights options. | Behind frontier on hardest reasoning. |
| **Meta Llama 4** | Open-weights, fully self-hostable, broad ecosystem. | You own the ops burden (GPUs, evals, safety). |

---

## 3. Recommended model by task

### Writing & correspondence
| Task | First choice | Cheaper alternative | Notes |
|---|---|---|---|
| Drafting taxpayer letters / notices | **Claude Sonnet 4.6** | Haiku 4.5 (templates) | Sonnet handles tone + accuracy. Use templates + RAG of approved phrasings. |
| Drafting policy memos / white papers | **Claude Opus 4.7** | Sonnet 4.6 | Opus for nuance and structure on long docs. |
| Public-facing guidance / web copy | **Claude Sonnet 4.6** | GPT-5 | Run plain-language readability checks. |
| Translating notices (EN ↔ FR/ES/DE/etc.) | **Gemini 2.5 Pro** or **GPT-5** | Sonnet 4.6 | Always have a human native speaker review legal translations. |
| Translating to/from Chinese | **Kimi K2** | Gemini 2.5 Pro | Kimi is unusually strong on CJK. |
| Internal email / meeting summaries | **Claude Haiku 4.5** | Gemini Flash | Cheap and fast; quality is sufficient. |

### Simple questions & helpdesk
| Task | First choice | Cheaper alternative | Notes |
|---|---|---|---|
| Internal staff Q&A ("what form for X?") | **Claude Sonnet 4.6 + RAG** | Haiku 4.5 + RAG | RAG against your internal knowledge base is what makes this safe. |
| Taxpayer chatbot (general info) | **Claude Sonnet 4.6 + RAG** | Gemini Flash + RAG | Always cite the source page; never let the bot promise a refund or assess liability. |
| Form / topic classification, routing | **Claude Haiku 4.5** | Gemini Flash | High volume, low-judgment — go cheap and fast. |
| Sentiment / complaint triage | **Haiku 4.5** | Gemini Flash | Same. |

### Reviewing documents
| Task | First choice | Cheaper alternative | Notes |
|---|---|---|---|
| Reviewing one tax return / filing | **Claude Sonnet 4.6** | Haiku 4.5 (first pass) | Sonnet for the substantive read. |
| Reviewing huge bundles (a whole audit file, hundreds of pages) | **Gemini 2.5 Pro** (1M context) | Claude Opus with chunking | Use Gemini's huge window to keep everything in one prompt; have Opus do the final judgment pass. |
| Contract / settlement agreement review | **Claude Opus 4.7** | Sonnet 4.6 | Opus catches more edge-case legal issues. |
| Comparing two versions of a regulation | **Claude Opus 4.7** | Gemini 2.5 Pro | Ask for a structured diff with citations to section numbers. |
| Reading scanned PDFs, handwritten forms, photos of receipts | **Gemini 2.5 Pro** or **GPT-5** | Gemini Flash | Native multimodal beats a separate OCR step. |
| Extracting structured data from filings (JSON output) | **Claude Sonnet 4.6** with tool use | Haiku 4.5 | Use a JSON schema / structured output mode. |

### Reviewing calculations & numerical work
> ⚠️ **Rule of thumb:** never trust an LLM's mental math on anything that
> matters. Have it *write code* (Python) and run it, or call a deterministic
> calculator tool. Then have a second model review the code and the result.

| Task | First choice | Cheaper alternative | Notes |
|---|---|---|---|
| Verifying a return's math | **Claude Sonnet 4.6 + Python tool use** | Haiku 4.5 + Python | Make the model emit and run code; check the code, not the prose. |
| Complex multi-step assessments (depreciation, FX, transfer pricing) | **OpenAI o-series** or **Claude Opus 4.7 (extended thinking)** | DeepSeek R1 | Reasoning models earn their cost here. Always cross-check with a second model. |
| Spreadsheet analysis | **Gemini 2.5 Pro** | GPT-5 | Strong native handling of CSV/XLSX. |
| Statistical / risk-scoring narratives | **Claude Opus 4.7** | Sonnet 4.6 | Use Opus to *explain* a model's output; don't use the LLM as the risk model. |
| Date / interest / penalty math | **Tool call to a deterministic library** | — | This should never be an LLM call at all. |

### Legal & regulatory research
| Task | First choice | Cheaper alternative | Notes |
|---|---|---|---|
| Statute / regulation interpretation | **Claude Opus 4.7 + RAG over your authoritative corpus** | Sonnet 4.6 + RAG | Require a citation to section + sub-paragraph for every claim. |
| Case-law summary | **Claude Opus 4.7 + RAG** | GPT-5 + RAG | Never accept an uncited case name — it might be fabricated. |
| Drafting an audit position memo | **Claude Opus 4.7** | Sonnet 4.6 | Have a second model (e.g. GPT-5) red-team the argument. |
| Cross-border / treaty analysis | **Claude Opus 4.7** | Gemini 2.5 Pro | Ground in OECD model + the specific treaty PDF. |
| Bill / amendment impact analysis | **Claude Opus 4.7** | Gemini 2.5 Pro (long doc) | Use Gemini for ingest, Opus for judgment. |

### Audit & investigations
| Task | First choice | Cheaper alternative | Notes |
|---|---|---|---|
| Anomaly narrative ("explain why this filing is unusual") | **Claude Sonnet 4.6** | Haiku 4.5 | LLM summarizes the *signals*; the rules engine picks them. |
| Interview prep questions | **Claude Sonnet 4.6** | GPT-5 | Generate, then have a senior auditor edit. |
| Timeline reconstruction from emails / docs | **Gemini 2.5 Pro** (long context) | Opus 4.7 | Ingest everything, output a dated timeline with cite-back to source. |
| Linking entities across filings | **Code + database**; LLM only to explain | — | Don't ask an LLM to do graph joins. |

### Internal coding & data work
| Task | First choice | Cheaper alternative | Notes |
|---|---|---|---|
| Writing SQL / Python for analysts | **Claude Sonnet 4.6** | GPT-5 | Sonnet is currently the strongest day-to-day coder. |
| Refactoring legacy COBOL / mainframe code | **Claude Opus 4.7** | GPT-5 | Older languages reward depth. |
| Building internal agents / pipelines | **Claude Sonnet 4.6** or **Kimi K2** (open) | DeepSeek V3 | Kimi K2 is a strong open-weights agentic option. |
| Quick scripts, regex, one-liners | **Claude Haiku 4.5** | Gemini Flash | Cheap, fast, good enough. |

### Voice, video, OCR, and other multimodal
| Task | First choice | Cheaper alternative | Notes |
|---|---|---|---|
| Transcribing taxpayer phone calls | **GPT-5 (audio)** or dedicated ASR | Gemini Flash | Use a speech model; fall back to LLM only for summarization. |
| Reading a chart / diagram in a filing | **Gemini 2.5 Pro** | GPT-5 | Both are strong; Gemini edges ahead on dense charts. |
| Reviewing video evidence (asset tracing, etc.) | **Gemini 2.5 Pro** | GPT-5 | Gemini natively ingests video. |

### Highly sensitive / classified workloads
| Task | First choice | Notes |
|---|---|---|
| Anything involving live taxpayer PII at scale | **Self-hosted Llama 4 or Kimi K2 in your VPC** | Trade some quality for full control. |
| Sovereign / EU-only deployments | **Mistral Large 2** (EU-hosted) or self-hosted Llama | Check the contract for sub-processors. |
| Air-gapped classified analysis | **Self-hosted Llama 4 / DeepSeek / Mistral** | No external API calls, period. |

---

## 4. Quick decision rules

1. **Picking by task type:**
   - *Judgment / legal nuance* → **Opus 4.7**
   - *Daily drafting & review* → **Sonnet 4.6**
   - *High-volume / classification / routing* → **Haiku 4.5** or **Gemini Flash**
   - *Huge documents in one shot* → **Gemini 2.5 Pro**
   - *Hard math / formal reasoning* → **OpenAI o-series** or **Opus extended thinking**
   - *Multimodal (images/audio/video)* → **Gemini 2.5 Pro** or **GPT-5**
   - *Sovereignty / on-prem* → **Llama 4**, **Kimi K2**, **Mistral Large 2**

2. **Always pair an LLM with:**
   - **RAG** for any current-law question
   - **Tool use / code execution** for any number
   - **Citations** for any claim that will leave the building
   - **A human reviewer** for anything that affects a taxpayer

3. **Use two models, not one, on high-stakes outputs.** Have one draft, the
   other red-team. Cheap insurance against hallucination.

4. **Build an internal eval set** of ~100 real tax-department tasks and
   re-score every model release. Vendor benchmarks won't tell you what works
   for *your* statute, *your* forms, *your* style guide.

5. **Log everything.** Prompt, response, model, version, who ran it, what
   citation it gave. You will need this for audit and for FOIA-equivalent
   requests.
